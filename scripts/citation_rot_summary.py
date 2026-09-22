#!/usr/bin/env python3
"""Re-adjudicate a citation_qc.py scan into the QC memo's §3.2 numbers.

citation_qc.py grades every [ref] URL instance; its raw `dead` bucket is too
broad for the SOP's rot definition (QC SOP §3.2 / §6). This script applies the
repo's own rules on top of the raw verdicts and emits the numbers the memo
quotes, so §2 of a QC memo is reproducible instead of hand-tallied:

  rot        = dead (HTTP 4xx other than 401/403/429, HTTP 410, connection
               failure `000`, soft-404 pages) + content_gone
  live       = ok, plus dead-verdicts that are really live: 301/302 (keep the
               citation at its redirect target), 202, bot-challenge
               interstitials (Incapsula/Cloudflare)
  blocked    = 401/403/429 and ANY 5xx (a human can read it) -> never rot
  unverifiable = image-only PDFs -> never rot

Optionally intersects with a FRESH export so citations already repaired since
the scan drop out (the scan is a snapshot; the export is the present).

    python scripts/citation_rot_summary.py \
        --scan batches/staging/qc-<stamp>/citation_qc_full.json \
        --csv scripts/gem_export.csv \
        [--retest batches/staging/qc-<stamp>/citation_retest.json] \
        --out batches/staging/qc-<stamp>/citation_rot_summary.json

`--retest` takes a later url_verifier pass over a subset of the scanned URLs (the SOP's
"re-test a sample of the dead verdicts with a browser UA" step, §3.2): a URL that now
loads is live, one that now answers 401/403/429/5xx is blocked. HTTP 000 (connection
failure) is the bucket worth re-testing: on 2026-09-10 a third of it turned out live or
blocked, while 404s re-tested 95% still-404.
"""
import argparse, csv, json, re, sys
from pathlib import Path
from collections import Counter, defaultdict

BLOCKED_CODES = {"401", "403", "429"}
LIVE_DEAD_CODES = {"301", "302", "307", "308", "202"}
LIVE_STATUSES = {"operating", "construction", "proposed", "idle", "idled"}
MIRRORABLE_HOSTS = ("giignl.org", "igu.org")  # official-mirror swap, data/README.md


def load_retest(path):
    """url -> forced adjudication from a later url_verifier re-test (verify_url(url, [])
    per URL, dumped as [{url, ok, reason}]). ok -> live; 401/403/429/5xx -> blocked;
    anything else leaves the scan's verdict in place (a re-test that fails the same
    way adds nothing)."""
    out = {}
    for r in json.load(open(path)):
        if r.get("ok"):
            out[r["url"]] = "live"; continue
        m = re.search(r"HTTP (\d{3})", r.get("reason", ""))
        if m and (m.group(1) in BLOCKED_CODES or m.group(1).startswith("5")):
            out[r["url"]] = "blocked"
    return out


def adjudicate(rec, retest=None):
    v, reason = rec["verdict"], rec["reason"]
    if retest and rec["url"] in retest and v in ("dead", "content_gone"):
        return retest[rec["url"]]
    if v in ("ok",):
        return "live"
    if v == "unverifiable":
        return "unverifiable"
    if v == "content_gone":
        return "rot"
    if v == "blocked":
        return "blocked"
    # v == dead
    if "interstitial" in reason:
        return "live"
    m = re.search(r"HTTP (\d{3})", reason)
    if not m:
        return "rot"  # soft-error page
    code = m.group(1)
    if code in LIVE_DEAD_CODES:
        return "live"
    if code in BLOCKED_CODES or code.startswith("5"):
        return "blocked"
    return "rot"


def load_export_refs(csv_path):
    """(terminal_id, unit_id) -> {ref_key: set(urls)} from the fresh export, using the
    same colmap keys and URL parser citation_qc.py used to grade the scan."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from colmap import load_colmap
    from citation_qc import _extract_urls, _EXCLUDED_REF_KEYS
    colmap = load_colmap(csv_path)
    ref_cols = [(k, v) for k, v in colmap.items()
                if k.endswith("_ref") and k not in _EXCLUDED_REF_KEYS and isinstance(v, int)]
    ci_tid, ci_uid = colmap["terminal_id"], colmap["unit_id"]
    out = {}
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f); next(reader)
        for row in reader:
            if len(row) < colmap["_total_columns"]:
                continue
            d = {}
            for k, idx in ref_cols:
                urls = set(_extract_urls(row[idx]))
                if urls:
                    d[k] = urls
            out[(row[ci_tid], row[ci_uid])] = d
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scan", required=True)
    ap.add_argument("--csv", help="fresh export; drop citations no longer present")
    ap.add_argument("--out")
    ap.add_argument("--retest", help="url_verifier re-test JSON [{url, ok, reason}]; live/blocked results override dead verdicts")
    ap.add_argument("--threshold", type=float, default=25.0, help="SOP §6 per-country rot %% escalation")
    a = ap.parse_args()

    scan = json.load(open(a.scan))
    recs = scan["results"]
    export = load_export_refs(a.csv) if a.csv else None
    retest = load_retest(a.retest) if a.retest else None

    kept, dropped_repaired = [], 0
    for r in recs:
        if export is not None:
            live_urls = export.get((r["terminal_id"], r["unit_id"]), {}).get(r["ref_column"], set())
            if r["url"] not in live_urls:
                dropped_repaired += 1
                continue
        r = dict(r); r["adjudicated"] = adjudicate(r, retest); kept.append(r)

    tot = Counter(r["adjudicated"] for r in kept)
    raw = Counter(r["verdict"] for r in kept)
    n = len(kept)
    rot = [r for r in kept if r["adjudicated"] == "rot"]

    # per-cell view: a cell is (terminal, unit, ref_column); fully_dead = every citation in it is rot
    cells = defaultdict(list)
    for r in kept:
        cells[(r["terminal_id"], r["unit_id"], r["ref_column"])].append(r)
    cell_any_rot = {k for k, v in cells.items() if any(x["adjudicated"] == "rot" for x in v)}
    cell_all_rot = {k for k, v in cells.items() if all(x["adjudicated"] == "rot" for x in v)}
    tcell_all_rot = {(k[0], k[2]) for k in cell_all_rot}
    live_all_rot = {k for k in cell_all_rot if cells[k][0]["status"] in LIVE_STATUSES}
    mirrorable_cells = {k for k in cell_all_rot if all(any(h in x["url"] for h in MIRRORABLE_HOSTS) for x in cells[k])}

    by_country = {}
    for c in sorted({r["country"] for r in kept}):
        rs = [r for r in kept if r["country"] == c]
        nr = sum(1 for r in rs if r["adjudicated"] == "rot")
        by_country[c] = {
            "checked": len(rs), "rot": nr, "rot_pct": round(100 * nr / len(rs), 1),
            "blocked": sum(1 for r in rs if r["adjudicated"] == "blocked"),
            "terminals_with_fully_dead_cell": len({k[0] for k in cell_all_rot if cells[k][0]["country"] == c}),
        }
    over = {c: v for c, v in by_country.items() if v["rot_pct"] > a.threshold and v["checked"] >= 10}
    by_col = Counter(r["ref_column"] for r in rot)
    by_host = Counter(re.sub(r"^https?://(www\.)?([^/]+).*$", r"\2", r["url"]) for r in rot)
    rot_codes = Counter(re.search(r"HTTP (\d{3})", r["reason"]).group(1) if re.search(r"HTTP (\d{3})", r["reason"]) else r["verdict"] for r in rot)

    out = {
        "scan": a.scan, "scan_date": scan.get("today"), "export": a.csv, "retest": a.retest,
        "retest_overrides": dict(Counter(v for v in (retest or {}).values())),
        "instances_overridden_by_retest": sum(1 for r in kept if retest and r["url"] in retest and r["verdict"] in ("dead", "content_gone")),
        "rules": "rot = dead(4xx not 401/403/429, 410, 000, soft-404) + content_gone; 301/302/307/308/202/interstitial -> live; 401/403/429/5xx -> blocked; image PDFs -> unverifiable",
        "citation_instances_in_scan": len(recs),
        "dropped_since_scan_repaired_or_removed": dropped_repaired,
        "citation_instances_assessed": n,
        "raw_verdicts": dict(raw),
        "adjudicated": dict(tot),
        "rot_pct": round(100 * tot["rot"] / n, 1) if n else None,
        "rot_by_http_code": dict(rot_codes.most_common()),
        "cells_with_any_rot": len(cell_any_rot),
        "cells_fully_dead": len(cell_all_rot),
        "terminal_cells_fully_dead": len(tcell_all_rot),
        "terminals_with_fully_dead_cell": len({k[0] for k in cell_all_rot}),
        "fully_dead_cells_on_live_status": len(live_all_rot),
        "fully_dead_cells_mirror_swappable_giignl_igu": len(mirrorable_cells),
        "fully_dead_cells_needing_resourcing": len(cell_all_rot) - len(mirrorable_cells),
        "countries_over_threshold": dict(sorted(over.items(), key=lambda kv: -kv[1]["rot_pct"])),
        "rot_by_ref_column": dict(by_col.most_common()),
        "rot_by_host_top": dict(by_host.most_common(25)),
        "by_country": by_country,
        "fully_dead_cells": sorted(
            [{"terminal_id": k[0], "unit_id": k[1], "terminal": cells[k][0]["terminal_name"], "country": cells[k][0]["country"],
              "status": cells[k][0]["status"], "ref_column": k[2], "urls": [x["url"] for x in cells[k]],
              "mirror_swappable": k in mirrorable_cells} for k in cell_all_rot],
            key=lambda x: (x["country"], x["terminal"], x["ref_column"])),
    }
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1, ensure_ascii=False)
    hdr = {k: v for k, v in out.items() if k not in ("by_country", "fully_dead_cells", "rot_by_host_top", "rot_by_ref_column")}
    print(json.dumps(hdr, indent=1, ensure_ascii=False))
    print("rot_by_ref_column (top 12):", dict(by_col.most_common(12)))
    print("rot_by_host (top 12):", dict(by_host.most_common(12)))


if __name__ == "__main__":
    main()
