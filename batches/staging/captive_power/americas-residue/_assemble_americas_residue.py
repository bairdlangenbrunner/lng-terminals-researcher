"""Assemble the Americas-residue captive-power canonical staging JSONs from shard results.

Run from this directory:  python _assemble_americas_residue.py

Reads  shard_results/shard_*.json    (2 primary shards, 11 terminals)
       shard_results/recovery_*.json (recovery passes; supersede primaries by terminal_id)
       neighbors_raw.json            (nearest-2 GOGPT plants per terminal, 30 km cap,
                                      every row carrying gogpt_plant_id — _compute_neighbors.py)
       ../../../../scripts/gem_export.csv (unit rows + current CaptiveGasPower cells)
Writes staged_updates.json, staged_qa_review.json, captive_terminal_first.json,
       captive_neighboring_plants.json, captive_gogpt_candidates.json
(same canonical layout as ../asia, ../europe, ../americas-complete).
"""
import csv
import glob
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
CSV = HERE / "../../../../scripts/gem_export.csv"
EXPECTED_TERMINALS = 11

# ---------------------------------------------------------------- load shards
records = {}
for fp in sorted(glob.glob(str(HERE / "shard_results/shard_*.json"))):
    data = json.loads(Path(fp).read_text(encoding="utf-8"))
    for r in (data if isinstance(data, list) else data.get("results", [])):
        records[r["terminal_id"]] = r
n_primary = len(records)
superseded = []
for fp in sorted(glob.glob(str(HERE / "shard_results/recovery_*.json"))):
    data = json.loads(Path(fp).read_text(encoding="utf-8"))
    for r in (data if isinstance(data, list) else data.get("results", [])):
        if r["terminal_id"] in records:
            superseded.append(r["terminal_id"])
        records[r["terminal_id"]] = r
assert len(records) == n_primary == EXPECTED_TERMINALS, \
    f"expected {EXPECTED_TERMINALS} terminals, got {len(records)} (primary {n_primary})"

tally = {}
for r in records.values():
    tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
print(f"{len(records)} terminals; {len(superseded)} superseded by recovery; verdicts: {tally}")

# --------------------------------------------------------------- gem CSV rows
unit_rows = {}   # terminal_id -> list of unit dicts
with open(CSV, encoding="utf-8-sig", newline="") as fh:
    for row in csv.DictReader(fh):
        unit_rows.setdefault(row["TerminalID"], []).append(row)

# ------------------------------------------------------ neighbors + relations
neighbors = json.loads((HERE / "neighbors_raw.json").read_text(encoding="utf-8"))
URL_RE = re.compile(r"https?://[^\s)\]'\"<>]+")
for nb in neighbors:
    assert nb.get("gogpt_plant_id"), f"neighbor row missing gogpt_plant_id (run _compute_neighbors.py): {nb['neighboring_plant']}"
    r = records.get(nb["terminal_id"])
    if not r:
        continue
    prior = (r.get("gogpt_prior_assessment") or "").strip()
    if nb["rank"] == 1:
        nb["relation"] = prior
        for u in URL_RE.findall(prior):
            if "gem.wiki" not in u and "globalenergymonitor.org" not in u:
                nb["info_url"] = u.rstrip(".,;")
                break
    else:
        nb["relation"] = "Second-nearest plant, shown for colocation context; analyzed only where named in the rank-1 assessment."

# nearest plant per terminal (for the staged_updates gogpt_* columns) — copied
# BEFORE the tab-write pops so gogpt_plant_id survives for the staged rows
nearest = {}
for nb in neighbors:
    if nb["rank"] == 1:
        nearest[nb["terminal_id"]] = dict(nb)

for nb in neighbors:
    nb.pop("country", None)         # not in the build's known-key set for this tab
    nb.pop("gogpt_plant_id", None)  # staged-row column only; tab carries the wiki nav link
(HERE / "captive_neighboring_plants.json").write_text(
    json.dumps(neighbors, ensure_ascii=False, indent=1), encoding="utf-8")

# -------------------------------------------------------- terminal_first tab
terminal_first = []
for tid, r in sorted(records.items(), key=lambda kv: (kv[1].get("country", ""), kv[1].get("terminal", ""))):
    how = f"VERDICT: {r['verdict']}. {(r.get('captive_summary') or '').strip()}"
    ch = (r.get("confirmed_how") or "").strip()
    if ch:
        how += f" EVIDENCE: {ch}"
    terminal_first.append({
        "terminal": r.get("terminal", ""),
        "terminal_id": tid,
        "mechanical": r.get("mechanical", "") or "False" if r["verdict"] == "YES" else r.get("mechanical", ""),
        "confidence": r.get("confidence", ""),
        "gogpt_captive_prior": (r.get("gogpt_prior_assessment") or "").strip(),
        "confirmed_how": how,
        "confirmed_how [ref]": r.get("refs", []),
    })
(HERE / "captive_terminal_first.json").write_text(
    json.dumps(terminal_first, ensure_ascii=False, indent=1), encoding="utf-8")

# ------------------------------------------------------ gogpt_candidates tab
candidates = []
for tid, r in sorted(records.items(), key=lambda kv: (kv[1].get("country", ""), kv[1].get("terminal", ""))):
    candidates.append({
        "terminal": r.get("terminal", ""),
        "terminal_id": tid,
        "gogpt_candidate": r.get("gogpt_candidate", ""),
        "electric_mw": r.get("electric_mw", ""),
        "confidence": r.get("confidence", ""),
        "basis": (r.get("gogpt_candidate_basis") or "").strip(),
        "basis [ref]": r.get("refs", []),
        "mechanical_drive_note": r.get("mechanical_drive_note", ""),
    })
(HERE / "captive_gogpt_candidates.json").write_text(
    json.dumps(candidates, ensure_ascii=False, indent=1), encoding="utf-8")

# --------------------------------------------------------- staged_updates
OVERTURNS = set()  # no terminal in scope carries a pre-existing True (2026-08-01 pull)
updates = []
for tid, r in sorted(records.items(), key=lambda kv: (kv[1].get("country", ""), kv[1].get("terminal", ""))):
    is_yes = r["verdict"] == "YES"
    is_overturn = tid in OVERTURNS
    if not (is_yes or is_overturn):
        continue
    rows = unit_rows.get(tid)
    assert rows, f"no gem_export rows for {tid} {r.get('terminal')}"
    nb = nearest.get(tid, {})
    for row in rows:
        existing_urls = URL_RE.findall(row.get("CaptiveGasPower [ref]", "") or "")
        shard_urls = list(r.get("refs", []))
        # ref MERGE: still-valid existing URLs first, then additions (dedup, order-stable)
        ref_urls, seen = [], set()
        for u in existing_urls + shard_urls:
            u = u.rstrip(".,;")
            if u not in seen:
                seen.add(u)
                ref_urls.append(u)
        rec = {
            "captive_category": r.get("captive_category", ""),
            "hardware_summary": r.get("hardware_summary", ""),
            "mechanical": r.get("mechanical", "") or "False",
            "gogpt_plant_id": nb.get("gogpt_plant_id", ""),
            "gogpt_plant": nb.get("neighboring_plant", ""),
            "gogpt_wiki_url": nb.get("gogpt_record (nav only)", ""),
            "terminal_id": tid,
            "unit_id": row.get("UnitID", ""),
            "terminal_name": row.get("TerminalName", r.get("terminal", "")),
            "unit_name": row.get("UnitName", ""),
            "country": r.get("country", ""),
            "field_name": "CaptiveGasPower",
            "old_value": row.get("CaptiveGasPower", ""),
            "new_value": "True" if is_yes else "False",
            "confidence": r.get("confidence", ""),
            "source_tier": "",
            "ref_field": "CaptiveGasPower [ref]",
            "ref_urls": ref_urls,
            "source_notes": (r.get("captive_summary") or "").strip(),
        }
        if r.get("hybrid_basis"):
            rec["hybrid_basis"] = r["hybrid_basis"]
        updates.append(rec)
for u in updates:
    assert not u["gogpt_plant"] or u["gogpt_plant_id"], \
        f"staged row names gogpt_plant without gogpt_plant_id: {u['terminal_name']}"
(HERE / "staged_updates.json").write_text(
    json.dumps(updates, ensure_ascii=False, indent=1), encoding="utf-8")

# --------------------------------------------------------- staged_qa_review
# Authored rows for findings that live only in shard `notes` fields go here.
qa = []
for tid, r in sorted(records.items(), key=lambda kv: (kv[1].get("country", ""), kv[1].get("terminal", ""))):
    if r["verdict"] == "INSUFFICIENT":
        qa.append({
            "category": "captive_power_insufficient",
            "terminal_id": tid,
            "unit_id": "",
            "terminal_name": r.get("terminal", ""),
            "issue": (r.get("captive_summary") or "").strip(),
            "severity": "low",
            "suggested_action": "CaptiveGasPower left blank — fuel/equipment for on-site generation undocumented after research (fuel gate: unstated = INSUFFICIENT). Revisit if an equipment spec, EIA chapter, or class record surfaces. "
                                + ((r.get("notes") or "").strip()[:400]),
            "gem_field": "CaptiveGasPower",
            "paste_value": "",
        })
    other = (r.get("status_or_other_findings") or "").strip()
    if other and not re.match(r"(?i)^none\b", other):
        qa.append({
            "category": "update_batch_flag",
            "terminal_id": tid,
            "unit_id": "",
            "terminal_name": r.get("terminal", ""),
            "issue": other,
            "severity": "medium",
            "suggested_action": "FOLLOW-ON UPDATE BATCH, not this one: this captive batch's edit lane is CaptiveGasPower only. Flagged here with the researcher's sources so it is not lost.",
            "gem_field": "",
            "paste_value": "",
        })
(HERE / "staged_qa_review.json").write_text(
    json.dumps(qa, ensure_ascii=False, indent=1), encoding="utf-8")

yes_names = sorted(f"{r.get('country')}: {r.get('terminal')}" for r in records.values() if r["verdict"] == "YES")
print(f"staged_updates: {len(updates)} unit-rows "
      f"({len({u['terminal_id'] for u in updates})} terminals)")
print(f"qa_review: {len(qa)} rows; terminal_first: {len(terminal_first)}; "
      f"gogpt_candidates: {len(candidates)}; neighbors: {len(neighbors)}")
print("YES terminals:")
for n in yes_names:
    print("  " + n)
