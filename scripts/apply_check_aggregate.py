#!/usr/bin/env python3
"""Roll a directory of apply_check.py outputs into one divergence summary.

apply_check.py is per-workbook. The QC memo (§3.4 of the QC SOP) needs the
tracker-wide view: how many staged edits are still not in the live DB, how many
landed changed, and what the divergences look like. This produces the same shape
as `batches/staging/qc-<stamp>/apply_check_divergence.json`:

    python scripts/apply_check_aggregate.py work/apply_check_<date>/ \
        --out batches/staging/qc-<stamp>/apply_check_divergence.json

Divergence classes are heuristics over (old, staged, live) for review triage:
  ref_no_overlap          [ref] cell: live shares no URL with the staged value
  ref_partial_merge       [ref] cell: live has some staged URLs but not all
  ref_landed_plus_additions  [ref] cell: live has every staged URL plus more
  entity_name_rendering   Owner/Parent/Operator differing only by entity rendering
                          ([TO BE DELETED] markers, whitespace, list delimiters)
  clean_name_replaced_by_marked_entity  live shows a [TO BE DELETED] entity
  list_delimiter_or_addition  same members, different delimiter / a member added
  year_superseded_later   year field, live year > staged year
  coordinate_precision    lat/lon differing by < 0.01 degrees
  note_rewritten_by_later_researcher  ResearcherNotes*/Wiki free text
  REVIEW_<field>          everything else: a real value conflict a human must look at
"""
import argparse, glob, json, os, re
from collections import Counter, defaultdict

TBD = "[TO BE DELETED]"


def _urls(v):
    return set(re.findall(r"https?://[^\s,;\"'<>]+", v or ""))


def _members(v):
    return {re.sub(r"\s+", " ", m.replace(TBD, "")).strip().lower()
            for m in re.split(r"[;,]", v or "") if m.strip()}


def _num(v):
    try:
        return float(str(v).replace(",", ""))
    except (TypeError, ValueError):
        return None


def classify(rec):
    f, staged, live, old = rec["field_name"], rec.get("new_value") or "", rec.get("fresh_value") or "", rec.get("old_value") or ""
    if f.endswith("[ref]"):
        s, l = _urls(staged), _urls(live)
        if not (s & l):
            return "ref_no_overlap", "medium"
        if s <= l:
            return "ref_landed_plus_additions", "low"
        return "ref_partial_merge", "medium"
    if f in ("Owner", "Parent", "Operator", "VesselOwner", "VesselOperator"):
        if _members(staged) == _members(live):
            return ("clean_name_replaced_by_marked_entity" if TBD in live and TBD not in staged
                    else "entity_name_rendering"), "low"
        return f"REVIEW_ownership_conflict", "medium"
    if f.startswith("ResearcherNotes") or f == "Wiki":
        return "note_rewritten_by_later_researcher", "low"
    if f in ("Latitude", "Longitude"):
        a, b = _num(staged), _num(live)
        if a is not None and b is not None and abs(a - b) < 0.01:
            return "coordinate_precision", "low"
        return "REVIEW_coordinates", "high"
    if re.search(r"Year|Date", f) and not f.endswith("[ref]"):
        a, b = _num(staged), _num(live)
        if a is not None and b is not None and b > a:
            return "year_superseded_later", "low"
        return "REVIEW_year_conflict", "medium"
    if _members(staged) == _members(live):
        return "list_delimiter_or_addition", "low"
    if f == "Status":
        return "REVIEW_status_conflict", "high"
    if f.startswith("Capacity"):
        return "REVIEW_capacity_conflict", "high"
    if rec.get("delete") or staged == "" and live:
        return "REVIEW_deletion_not_applied", "medium"
    return f"REVIEW_{f}", "medium"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir", help="directory of apply_check.py JSON outputs (one per workbook)")
    ap.add_argument("--out")
    a = ap.parse_args()

    per_batch, classes, queue = [], Counter(), []
    totals = Counter()
    for fp in sorted(glob.glob(os.path.join(a.dir, "*.json"))):
        d = json.load(open(fp))
        batch = os.path.basename(d.get("batch", fp))
        batch = re.sub(r"^lng_terminals_batch_", "", batch).replace(".xlsx", "")
        m = re.match(r"(\d{8}_\d{4}_ET)(?:_(.+?))?_(exhaustive_update|update|discovery|reconciliation)$", batch)
        scope, mode = (m.group(2) or "", m.group(3)) if m else ("", "")
        s = d["summary"]
        for k in ("landable_edits", "applied", "not_applied", "diverged", "not_found", "reverify_only"):
            totals[k] += s.get(k, 0)
        breakdown = Counter()
        for rec in d.get("by_classification", {}).get("diverged", []):
            cls, sev = classify(rec)
            breakdown[cls] += 1; classes[cls] += 1
            queue.append({"scope": scope, "batch": batch, "class": cls, "severity": sev,
                          "terminal": rec.get("terminal_name"), "unit_id": rec.get("unit_id"),
                          "terminal_id": rec.get("terminal_id"), "field": rec["field_name"],
                          "staged": (rec.get("new_value") or "")[:300], "live": (rec.get("fresh_value") or "")[:300],
                          "was": (rec.get("old_value") or "")[:300]})
        per_batch.append({"scope": scope, "mode": mode, "batch": batch,
                          **{k: s.get(k, 0) for k in ("landable_edits", "applied", "not_applied", "diverged", "not_found", "reverify_only")},
                          "divergence_pct": round(100 * s.get("diverged", 0) / s["landable_edits"], 1) if s.get("landable_edits") else 0.0,
                          "breakdown": dict(breakdown)})
    sev_rank = {"high": 0, "medium": 1, "low": 2}
    queue.sort(key=lambda q: (sev_rank[q["severity"]], q["scope"], q["terminal"] or ""))
    out = {
        "generated": json.load(open(sorted(glob.glob(os.path.join(a.dir, "*.json")))[0])).get("today"),
        "source_dir": a.dir, "n_batches": len(per_batch),
        "note": "one entry per (scope, mode); superseded rebuilds of the same scope excluded",
        "totals": dict(totals),
        "divergence_pct": round(100 * totals["diverged"] / totals["landable_edits"], 1) if totals["landable_edits"] else None,
        "divergence_classes": dict(classes.most_common()),
        "severity": dict(Counter(q["severity"] for q in queue)),
        "per_batch": per_batch, "review_queue": queue,
    }
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1, ensure_ascii=False)
    print(json.dumps({k: v for k, v in out.items() if k not in ("per_batch", "review_queue")}, indent=1))
    for b in per_batch:
        print(f'{b["batch"]:55s} landable {b["landable_edits"]:4d} applied {b["applied"]:4d} not_applied {b["not_applied"]:4d} diverged {b["diverged"]:3d} not_found {b["not_found"]}')


if __name__ == "__main__":
    main()
