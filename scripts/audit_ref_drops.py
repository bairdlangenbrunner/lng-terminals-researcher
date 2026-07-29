"""
Audit (and repair) staged [ref] edits that DROPPED existing citation URLs.

The miss class (Al Zour / gulf-turkiye, 2026-07-17): a sweep subagent re-verifying
a `[ref]` cell replaced the whole cell with its own newly-verified URLs, silently
dropping existing citations that were live (often bot-blocked 403s misread as
dead). The standing rule is MERGE semantics: a [ref] edit's new_value must carry
forward every still-valid existing URL — never drop a URL not proven dead
(Update SOP §7.2a).

This script walks a staging dir's `*.updates.json` files, finds every record
whose citation set drops URLs already in GEM's ref cell, and classifies each
dropped URL. Both record shapes are audited (matching the build's REF-DROP
guard since 2026-07-27): a `<field> [ref]` record (existing cell in its
old_value) and a VALUE record carrying `ref_urls`, whose target ref cell is
read from the fresh export (pass --gem-csv; defaults to scripts/gem_export.csv).
Classifications:

  rehosted_same_doc   the same document appears in new_value at a new host
                      (e.g. dead giignl.org PDF -> GIIGNL CDN mirror of the SAME
                      edition; or a domain migration with the same path). A host
                      fix, not a lost source — drop is legitimate.
  restore             the URL is live (HTTP 200, name-token check passes) or
                      bot-blocked with the value verified via Wayback snapshot
                      (url_verifier's wayback fallback). Must be merged back.
  drop_ok_dead        genuinely dead (404/410/5xx/DNS) — replacement already
                      staged; drop stands.
  drop_ok_content_gone  live page but the terminal is no longer mentioned —
                      a failed citation per the verification rule; drop stands.
  dropped_unverifiable  bot-blocked AND no usable Wayback snapshot — cannot be
                      machine-verified; left dropped, listed for manual review.

URLs already declared in the record's `dropped_urls_dead` are skipped — they
carry an explicit disposition and the build GUARD already accepts them.

Redirects are followed; a restored URL is recorded in its FINAL live form (e.g.
hydrocarbons-technology.com -> offshore-technology.com).

Report-only by default (writes work/ref_drop_audit_<slug>.json + prints a
summary). With --apply it patches the per-country updates JSONs in place:
  - new_value / ref_urls  := restored URLs (existing-first) + agent's URLs
  - source_notes          += a dated ref-restore note
  - dropped_urls_dead     := the legitimately-dropped URLs (satisfies the
                             build_review_package ref-drop GUARD)
Re-run _assemble.py + build_review_package.py afterwards to rebuild the xlsx.

Usage (from scripts/):
    python audit_ref_drops.py ../batches/staging/gulf-turkiye            # report
    python audit_ref_drops.py ../batches/staging/gulf-turkiye --apply    # patch
    python audit_ref_drops.py ../batches/staging/<slug> --delay 0.5
"""
import argparse
import json
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

from url_verifier import verify_url

URL_RE = re.compile(r"https?://\S+")
YEAR_RE = re.compile(r"(20\d\d)")

RESTORE_CLASSES = {"restore_live", "restore_botblocked_wayback"}

# Words stripped from TerminalName when deriving name tokens for the content check
_NAME_SUFFIX_WORDS = {"lng", "terminal", "fsru", "flng", "import", "export",
                      "regasification", "liquefaction", "project"}


def extract_urls(value):
    """All http(s) URLs in a cell value / staged string, in order."""
    if not value:
        return []
    return [u.rstrip(",;") for u in URL_RE.findall(str(value))]


def norm_url(u):
    """Normalization for same-URL comparison (scheme + trailing-slash tolerant)."""
    u = u.strip().rstrip(",;").rstrip("/").lower()
    return re.sub(r"^https?://(www\.)?", "", u)


def name_tokens(terminal_name):
    """Distinctive substrings for the require_all=False content check.
    'Al Zour LNG Terminal' -> ['Al Zour', 'Al-Zour', 'Zour']."""
    words = [w for w in re.split(r"[\s]+", terminal_name or "")
             if w and w.lower().strip("()") not in _NAME_SUFFIX_WORDS]
    base = " ".join(words) or (terminal_name or "").strip()
    variants = [base]
    if " " in base:
        variants.append(base.replace(" ", "-"))
    if "-" in base:
        variants.append(base.replace("-", " "))
    longest = max(words, key=len, default="")
    if len(longest) >= 4 and longest not in variants:
        variants.append(longest)
    # ASCII-fold diacritics (Dörtyol -> Dortyol) — pages often drop accents
    folded = [unicodedata.normalize("NFKD", v).encode("ascii", "ignore").decode()
              for v in variants]
    variants += [f for f in folded if f]
    return [v for v in dict.fromkeys(variants) if v]


_HTTP_CACHE = {}


def http_probe(url, timeout=30):
    """(final_status, final_url) following redirects, GET, browser UA. Cached."""
    if url in _HTTP_CACHE:
        return _HTTP_CACHE[url]
    r = subprocess.run(
        ["curl", "-sL", "-o", "/dev/null",
         "-A", ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"),
         "-w", "%{http_code} %{url_effective}", "--max-time", str(timeout), url],
        capture_output=True, text=True, timeout=timeout + 5,
    )
    parts = r.stdout.strip().split(None, 1)
    status = parts[0] if parts else "000"
    final_url = parts[1] if len(parts) > 1 else url
    _HTTP_CACHE[url] = (status, final_url)
    return status, final_url


def is_same_doc_rehosted(dropped_url, kept_urls):
    """True if a kept URL is plausibly the SAME document at a different host."""
    d_norm = norm_url(dropped_url)
    d_path = d_norm.split("/", 1)[1] if "/" in d_norm else ""
    d_is_giignl_report = ("giignl" in d_norm and
                          ("annual" in d_norm and "report" in d_norm))
    d_years = set(YEAR_RE.findall(dropped_url.rsplit("/", 1)[-1]))
    for k in kept_urls:
        k_norm = norm_url(k)
        # exact same path on a different host (domain migration)
        k_path = k_norm.split("/", 1)[1] if "/" in k_norm else ""
        if d_path and d_path == k_path:
            return True
        # same GIIGNL annual-report edition re-hosted (giignl.org -> CDN mirror)
        if d_is_giignl_report and "giignl" in k_norm.replace("-", ""):
            k_years = set(YEAR_RE.findall(k.rsplit("/", 1)[-1]))
            if d_years and d_years == k_years:
                return True
    return False


def classify_dropped_url(url, kept_urls, terminal_name):
    """-> dict(url, classification, detail, restore_url|None). Network-active."""
    if is_same_doc_rehosted(url, kept_urls):
        return {"url": url, "classification": "rehosted_same_doc",
                "detail": "same document present in new_value at a new host",
                "restore_url": None}

    status, final_url = http_probe(url)
    tokens = name_tokens(terminal_name)

    if status == "200":
        ok, reason = verify_url(final_url, tokens, require_all=False)
        if ok:
            return {"url": url, "classification": "restore_live",
                    "detail": reason, "restore_url": final_url}
        # 200 but soft-error/bot-wall reasons already went through the wayback
        # fallback inside verify_url; a residual failure here means the page is
        # live but no longer supports the citation.
        if "wayback" in reason.lower() or "bot-block" in reason.lower():
            return {"url": url, "classification": "dropped_unverifiable",
                    "detail": reason, "restore_url": None}
        return {"url": url, "classification": "drop_ok_content_gone",
                "detail": reason, "restore_url": None}

    if status in ("401", "403", "429"):
        ok, reason = verify_url(final_url, tokens, require_all=False)
        if ok:
            return {"url": url, "classification": "restore_botblocked_wayback",
                    "detail": reason, "restore_url": final_url}
        return {"url": url, "classification": "dropped_unverifiable",
                "detail": reason, "restore_url": None}

    return {"url": url, "classification": "drop_ok_dead",
            "detail": f"HTTP {status}", "restore_url": None}


def audit_file(fp, delay=0.5, csv_refs=None):
    """Audit one <slug>.updates.json; returns list of per-record findings."""
    recs = json.loads(Path(fp).read_text(encoding="utf-8"))
    if not isinstance(recs, list):
        return []
    findings = []
    for i, rec in enumerate(recs):
        if rec.get("delete"):
            continue
        fname = str(rec.get("field_name", ""))
        value_record = False
        if fname.endswith("[ref]"):
            old_urls = extract_urls(rec.get("old_value"))
            kept = extract_urls(rec.get("new_value")) + list(rec.get("ref_urls") or [])
        elif csv_refs and (rec.get("ref_urls") or rec.get("ref_url")):
            # VALUE record carrying its citations in ref_urls: the target ref
            # cell never appears in old_value — read it from the fresh export
            # (same shape the build's REF-DROP guard checks since 2026-07-27).
            value_record = True
            refcol = str(rec.get("ref_field") or f"{fname} [ref]")
            old_cell = csv_refs.get(str(rec.get("unit_id")), {}).get(refcol, "")
            old_urls = extract_urls(old_cell)
            kept = list(rec.get("ref_urls") or [])
            if rec.get("ref_url"):
                kept.append(str(rec.get("ref_url")))
        else:
            continue
        kept_norm = {norm_url(u) for u in kept}
        declared_norm = {norm_url(str(u))
                         for u in (rec.get("dropped_urls_dead") or [])}
        dropped = [u for u in old_urls
                   if norm_url(u) not in kept_norm
                   and norm_url(u) not in declared_norm]
        if not dropped:
            continue
        results = []
        for u in dropped:
            results.append(classify_dropped_url(u, kept, rec.get("terminal_name", "")))
            time.sleep(delay)
        findings.append({
            "file": str(fp), "record_index": i,
            "terminal_id": rec.get("terminal_id"),
            "unit_id": rec.get("unit_id"),
            "terminal_name": rec.get("terminal_name"),
            "field_name": fname,
            "value_record": value_record,
            "dropped": results,
        })
    return findings


def apply_restores(findings, stamp):
    """Patch the per-country updates JSONs in place from audit findings."""
    by_file = {}
    for f in findings:
        by_file.setdefault(f["file"], []).append(f)
    n_restored = n_records = 0
    for fp, items in sorted(by_file.items()):
        recs = json.loads(Path(fp).read_text(encoding="utf-8"))
        touched = False
        for it in items:
            rec = recs[it["record_index"]]
            # guard against index drift between report and apply runs
            if (str(rec.get("field_name")) != it["field_name"]
                    or rec.get("terminal_id") != it["terminal_id"]):
                print(f"  WARN: {fp}#{it['record_index']} no longer matches the "
                      "audit finding — re-run the audit; record skipped")
                continue
            restores = [d["restore_url"] for d in it["dropped"]
                        if d["classification"] in RESTORE_CLASSES]
            dead = [d["url"] for d in it["dropped"]
                    if d["classification"] not in RESTORE_CLASSES]
            if dead:
                # explicit disposition for the build GUARD: these old URLs were
                # verified dead/superseded, their drop is deliberate
                existing_dead = list(rec.get("dropped_urls_dead") or [])
                rec["dropped_urls_dead"] = existing_dead + [
                    u for u in dead if u not in existing_dead]
                touched = True
            if not restores:
                continue
            if it.get("value_record"):
                # VALUE record: new_value is the data value, not a URL list —
                # only the ref_urls citation set is merged.
                ref_urls = list(rec.get("ref_urls") or [])
                rec["ref_urls"] = list(dict.fromkeys(restores + ref_urls))
            else:
                agent_urls = extract_urls(rec.get("new_value"))
                merged = list(dict.fromkeys(restores + agent_urls))  # existing-first
                rec["new_value"] = ", ".join(merged)
                ref_urls = list(rec.get("ref_urls") or [])
                rec["ref_urls"] = list(dict.fromkeys(restores + ref_urls))
            note = (f"[ref-restore {stamp}: restored existing live URL(s) "
                    f"{', '.join(restores)} per merge-semantics rule "
                    "(bot-block != dead; never drop a URL not proven dead)]")
            rec["source_notes"] = (str(rec.get("source_notes") or "").rstrip()
                                   + " " + note).strip()
            n_restored += len(restores)
            n_records += 1
            touched = True
        if touched:
            Path(fp).write_text(
                json.dumps(recs, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8")
            print(f"  patched {fp}")
    print(f"  restored {n_restored} URL(s) across {n_records} record(s)")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("staging_dir", nargs="+",
                    help="batches/staging/<slug> dir(s) to audit")
    ap.add_argument("--apply", action="store_true",
                    help="patch the updates JSONs (default: report only)")
    ap.add_argument("--delay", type=float, default=0.5,
                    help="politeness delay between URL checks (s)")
    ap.add_argument("--report", default=None,
                    help="report path (default work/ref_drop_audit_<slug>.json)")
    ap.add_argument("--gem-csv", default=str(Path(__file__).parent / "gem_export.csv"),
                    help="fresh export CSV: supplies the existing ref cell for VALUE "
                         "records carrying ref_urls (default scripts/gem_export.csv; "
                         "if missing, only <field> [ref] records are audited)")
    args = ap.parse_args()

    from build_review_package import _csv_ref_cells
    csv_refs = _csv_ref_cells(args.gem_csv)
    if not csv_refs:
        print(f"  WARN: no ref cells read from {args.gem_csv} — "
              "VALUE-record drops will not be audited")

    stamp = time.strftime("%Y-%m-%d")
    for d in args.staging_dir:
        d = Path(d)
        slug = d.name
        findings = []
        for fp in sorted(d.glob("*.updates.json")):
            findings.extend(audit_file(fp, delay=args.delay, csv_refs=csv_refs))

        counts = {}
        for f in findings:
            for res in f["dropped"]:
                counts[res["classification"]] = counts.get(res["classification"], 0) + 1
        print(f"\n== {slug}: {len(findings)} record(s) with dropped URLs ==")
        for k, v in sorted(counts.items()):
            print(f"  {k}: {v}")
        for f in findings:
            for res in f["dropped"]:
                if res["classification"] in RESTORE_CLASSES or \
                        res["classification"] == "dropped_unverifiable":
                    print(f"  {res['classification']:28s} {f['terminal_name']} | "
                          f"{f['field_name']} | {res['url']}"
                          + (f" -> {res['restore_url']}"
                             if res["restore_url"] and res["restore_url"] != res["url"]
                             else ""))

        report_path = Path(args.report) if args.report else \
            Path(__file__).parent / "work" / f"ref_drop_audit_{slug}.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps({"slug": slug, "stamp": stamp, "counts": counts,
                        "findings": findings}, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")
        print(f"  report -> {report_path}")

        if args.apply:
            apply_restores(findings, stamp)


if __name__ == "__main__":
    main()
