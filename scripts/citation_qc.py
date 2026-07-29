"""
Citation link-rot sweep — batch re-verification of EXISTING [ref] URLs in the
GEM export. The QC workflow's read-side complement to Update SOP §7.2 (which
re-verifies only rows a batch touches): this walks every [ref] column for the
scoped rows and re-checks each cited URL via url_verifier.py.

Used by QC SOP §3.2. Findings route to a follow-on Update batch ("QC detects,
Update fixes") — this script never edits anything.

Each URL gets a verdict, graded so the QC memo can weigh severity honestly:
  - ok:        HTTP 200, not a soft-error page (+ PDFs must have a text layer)
  - blocked:   HTTP 401/403/429 or a paywall/bot-wall soft-error (Reuters,
               Cloudflare interstitials, members-only pages…). The URL is
               probably fine for a human — verify manually, do NOT count as rot.
  - dead:      hard link-rot (404/410/5xx, DNS/timeout, soft-404 titles,
               scanned-PDF-no-text). The >25%-per-country escalation in
               QC SOP §6 counts ONLY these.
Plus, for ok URLs, an advisory name_found signal: page/PDF text contains the
terminal name (trailing parenthetical stripped; for 3+-word names a
first-two-words fallback is also tried). Names are often suffixed
("… LNG Terminal") or translated, so live-but-name-absent means
"verify manually", not "dead citation".

Politeness: url_verifier._fetch has NO built-in delay, so this script sleeps
--delay seconds after each first-time fetch (url_verifier's per-process cache
makes repeat citations of the same URL free — no extra sleep).

Usage:
    python citation_qc.py --country "Croatia"
    # Reads ./gem_export.csv + .colmap.json; writes work/citation_qc.json

    python citation_qc.py --status operating --max-urls 200
    # Scope by lifecycle status; cap unique URL checks (summary marks truncation)
"""
import argparse
import csv
import json
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from url_verifier import verify_url, clear_cache  # noqa: E402
from colmap import load_colmap as _load_colmap  # noqa: E402

# Read-only / computed ref columns the build never writes — skip them here too.
_EXCLUDED_REF_KEYS = {"tot_terminal_cost_ref"}

_URL_RE = re.compile(r"https?://[^\s,;\"'<>]+")
_TRAILING_PUNCT = ".,;:)]}>\"'"


def _extract_urls(cell):
    """A [ref] cell may carry several URLs (the build comma-joins them).
    Findall + trailing-punctuation strip is robust to comma/semicolon/space
    separators without truncating URLs that legitimately contain commas."""
    return [u.rstrip(_TRAILING_PUNCT) for u in _URL_RE.findall(cell or "")]


def _match_name(terminal_name):
    """Name used for the containment check: trailing parenthetical stripped
    (FSRU vessel tags etc. — display convention, not what articles print)."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", terminal_name or "").strip()


# Soft-error titles that mean "a human could still read this" — paywalls,
# bot-walls, rate limits — as opposed to genuine not-found pages.
_BLOCKED_TITLE_HINTS = (
    "429", "too many requests", "access denied", "forbidden", "just a moment",
    "attention required", "sign in", "log in to continue", "subscribe to continue",
    "members only", "login required", "this page is restricted",
)


def _verdict(reason):
    """Grade a url_verifier failure: 'blocked' (bot-wall/paywall — verify
    manually, not rot) vs 'dead' (hard link-rot)."""
    if reason.startswith(("HTTP 401", "HTTP 403", "HTTP 429")):
        return "blocked"
    if reason.startswith("soft-error"):
        low = reason.lower()
        if any(h in low for h in _BLOCKED_TITLE_HINTS):
            return "blocked"
    return "dead"


def _classify_reason(reason):
    """Bucket url_verifier failure reasons for the summary."""
    if reason.startswith(("HTTP 401", "HTTP 403", "HTTP 429")):
        return "http_blocked"
    if reason.startswith("HTTP 4"):
        return "http_4xx"
    if reason.startswith("HTTP 5"):
        return "http_5xx"
    if reason.startswith("HTTP"):
        return "http_other"
    if reason.startswith("soft-error"):
        return "soft_error"
    if reason.startswith("PDF has no extractable text"):
        return "pdf_no_text"
    return "other"


def compute_citation_qc(csv_path, country_filter=None, status_filter=None,
                        max_urls=0, delay=1.0, log=print):
    """Walk the scoped rows' [ref] columns and verify each cited URL.
    Returns (results, summary). Caps at max_urls unique URLs when > 0 —
    the summary then carries truncated=True (no silent caps)."""
    colmap = _load_colmap(csv_path)
    ci_tid = colmap.get("terminal_id")
    ci_uid = colmap.get("unit_id")
    ci_tname = colmap.get("terminal_name")
    ci_uname = colmap.get("unit_name")
    ci_country = colmap.get("country")
    ci_status = colmap.get("status")
    ci_fuel = colmap.get("fuel")

    # Derive the [ref] column list from the colmap so schema drift is absorbed.
    ref_cols = sorted(
        (k, v) for k, v in colmap.items()
        if k.endswith("_ref") and k not in _EXCLUDED_REF_KEYS and isinstance(v, int)
    )

    results = []
    seen_urls = set()
    truncated = False

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # header
        for row in reader:
            if truncated:
                break
            if len(row) < colmap["_total_columns"]:
                continue

            fuel = row[ci_fuel] if ci_fuel is not None else "LNG"
            if fuel != "LNG":
                continue  # out of scope per methodology

            country = row[ci_country]
            if country_filter and country != country_filter:
                continue
            status = row[ci_status] if ci_status is not None else ""
            if status_filter and status != status_filter:
                continue

            terminal_name = row[ci_tname]
            name_expected = _match_name(terminal_name)
            name_words = name_expected.split()

            for ref_key, ref_idx in ref_cols:
                for url in _extract_urls(row[ref_idx]):
                    if max_urls and len(seen_urls) >= max_urls and url not in seen_urls:
                        truncated = True
                        break

                    first_fetch = url not in seen_urls
                    seen_urls.add(url)

                    # Signal 1: liveness (HTTP + soft-error + PDF text layer).
                    # wayback_fallback OFF: this sweep's taxonomy wants bot-walls
                    # graded 'blocked' (verify manually), and with an empty token
                    # list the fallback would grade any 403-with-a-snapshot 'ok'
                    # on snapshot existence alone. Value-level Wayback checks
                    # belong to the staging path (url_verifier default), not QC.
                    live, reason = verify_url(url, [], strict=False,
                                              wayback_fallback=False)
                    verdict = "ok" if live else _verdict(reason)
                    # Signal 2: terminal-name containment (cached fetch — free).
                    name_found = None
                    if live and name_expected:
                        ok, _ = verify_url(url, [name_expected], strict=False,
                                           require_all=False)
                        if not ok and len(name_words) >= 3:
                            ok, _ = verify_url(url, [" ".join(name_words[:2])],
                                               strict=False, require_all=False)
                        name_found = ok

                    results.append({
                        "terminal_id": row[ci_tid],
                        "unit_id": row[ci_uid],
                        "terminal_name": terminal_name,
                        "unit_name": row[ci_uname],
                        "country": country,
                        "status": status,
                        "ref_column": ref_key,
                        "url": url,
                        "verdict": verdict,
                        "reason": "OK" if live else reason,
                        "name_found": name_found,
                    })

                    if first_fetch and delay > 0:
                        time.sleep(delay)
                if truncated:
                    break

    # ---- summary ----
    by_country = defaultdict(lambda: {"checked": 0, "dead": 0, "blocked": 0, "name_miss": 0})
    by_reason = Counter()
    by_ref_column = defaultdict(lambda: {"checked": 0, "dead": 0, "blocked": 0})
    for r in results:
        c = by_country[r["country"]]
        c["checked"] += 1
        col = by_ref_column[r["ref_column"]]
        col["checked"] += 1
        if r["verdict"] != "ok":
            c[r["verdict"]] += 1
            col[r["verdict"]] += 1
            by_reason[_classify_reason(r["reason"])] += 1
        elif r["name_found"] is False:
            c["name_miss"] += 1
    for c in by_country.values():
        # dead_pct counts hard rot only — blocked URLs are probably fine for a human
        c["dead_pct"] = round(100.0 * c["dead"] / c["checked"], 1) if c["checked"] else 0.0

    total_dead = sum(c["dead"] for c in by_country.values())
    total_blocked = sum(c["blocked"] for c in by_country.values())
    summary = {
        "total_url_citations_checked": len(results),
        "unique_urls_fetched": len(seen_urls),
        "total_dead": total_dead,
        "total_blocked": total_blocked,
        "total_name_miss": sum(c["name_miss"] for c in by_country.values()),
        "truncated": truncated,
        "by_country": dict(by_country),
        "by_reason": dict(by_reason),
        "by_ref_column": dict(by_ref_column),
    }

    log(f"\n  Citations checked: {len(results)} ({len(seen_urls)} unique URLs)"
        + ("  [TRUNCATED at --max-urls — coverage is partial]" if truncated else ""))
    log(f"  Dead (hard link-rot): {total_dead}   Blocked (bot-wall/paywall — verify "
        f"manually): {total_blocked}   Live-but-name-absent (advisory): "
        f"{summary['total_name_miss']}")
    worst = sorted(by_country.items(), key=lambda kv: -kv[1]["dead_pct"])[:10]
    if worst:
        log("  Worst countries by dead %:")
        for country, c in worst:
            flag = "  ← >25%: recommend EXHAUSTIVE update (QC SOP §6)" if c["dead_pct"] > 25 else ""
            log(f"    {country:30} {c['dead']:3}/{c['checked']:<4} ({c['dead_pct']}%){flag}")

    return results, summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", default="./gem_export.csv")
    p.add_argument("--output", "--out", dest="out", default="work/citation_qc.json")
    p.add_argument("--country", help="Filter to a specific country")
    p.add_argument("--status", help="Filter to a lifecycle status (e.g. operating)")
    p.add_argument("--max-urls", type=int, default=0,
                   help="Cap unique URL checks (0 = uncapped). The summary marks "
                        "truncation — partial coverage is never silent.")
    p.add_argument("--delay", type=float, default=1.0,
                   help="Seconds to sleep after each first-time fetch (politeness; "
                        "url_verifier has no built-in delay)")
    args = p.parse_args()

    clear_cache()
    results, summary = compute_citation_qc(
        args.csv, country_filter=args.country, status_filter=args.status,
        max_urls=args.max_urls, delay=args.delay,
    )

    out = {
        "today": str(date.today()),
        "country_filter": args.country,
        "status_filter": args.status,
        "max_urls": args.max_urls,
        "summary": summary,
        "results": results,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\n  Saved to {args.out}")


if __name__ == "__main__":
    main()
