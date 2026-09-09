"""Assemble this region's captive-power canonical staging JSONs from shard results.

Run from this directory:  python _assemble_<region>.py
Region = this directory's name; expected terminal count = len(worklist.json).

Reads  worklist.json                  (the coordinate-first audit's scope for this region)
       shard_results/shard_*.json     (primary shards)
       shard_results/recovery_*.json  (recovery passes; supersede primaries by terminal_id)
       neighbors_raw.json             (nearest-2 GOGPT plants, 30 km cap, gogpt_plant_id on
                                       every row — _compute_neighbors.py)
       ../../../../scripts/gem_export.csv (unit rows + current CaptiveGasPower cells)
Writes staged_updates.json, staged_qa_review.json, captive_terminal_first.json,
       captive_neighboring_plants.json, captive_gogpt_candidates.json
(same canonical layout as ../asia, ../europe, ../americas-gap).

Overturn handling (differs from americas-gap, whose scope had no pre-existing values):
some in-scope terminals already carry CaptiveGasPower=True in the live DB. A shard verdict
that AGREES (YES) stages normally with ref merge. A shard verdict that CONFLICTS (NO or
INSUFFICIENT against an existing value) is NOT auto-staged — the script fails listing the
conflicts until each terminal_id is adjudicated in ADJUDICATED_OVERTURNS below (QC-gate
output): map tid -> "False" (stage the overturn) or "keep" (existing value stands; the
research lands in qa_review only).
"""
import csv
import glob
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
REGION = HERE.name
CSV = HERE / "../../../../scripts/gem_export.csv"

worklist = json.loads((HERE / "worklist.json").read_text(encoding="utf-8"))
EXPECTED_TERMINALS = len(worklist)
scope_tids = {w["terminal_id"] for w in worklist}

# ---- QC-gate adjudications (2026-08-02) -------------------------------------
# Live-DB conflicts: tid -> "False" (stage the overturn) or "keep".
ADJUDICATED_OVERTURNS = {
    # PAWA PNG FSRU: integrated FSRP power barges — regas AND gas-turbine
    # generation on the SAME vessels (PowerMag ref, already the live [ref]) —
    # read as on-site generation (hybrid grid_export), not a separate-external-
    # plant direction-test NO. Project cancelled; existing True + ref stand.
    "T100000131072": "keep",
    # Pasca FLNG: recovery confirmed INSUFFICIENT — Baker Hughes release body
    # unreachable by any method, no independent design source. Existing live-DB
    # True KEPT (Tango pattern: off-grid FLSO physics prior, no contrary
    # evidence, two passes exhausted the leads); uncorroborated YouTube ref
    # flagged in qa_review, not repairable without a replacement source.
    "T100000131159": "keep",
}

# Verdict/record patches ruled at the gate; "gate_note" is prepended to notes.
VERDICT_OVERRIDES = {
    "T100000131072": {  # PAWA PNG FSRU — document the keep adjudication
        "gate_note": ("QC-GATE 2026-08-02: existing CaptiveGasPower=True KEPT. The "
                      "documented design puts gas-turbine generation and regas on "
                      "the SAME FSRP barges (PowerMag, already the live [ref]) — "
                      "on-site generation with hybrid_basis=grid_export, not a "
                      "separate external plant; the shard's direction-test NO is "
                      "scoped to separate-vessel/external-plant cases. Cancelled "
                      "project; no edit staged."),
    },
}

# Ref adjudications. drop_own: URLs stripped from the shard record's refs (not
# citable in any lane). drop_existing: live-DB [ref] URLs proven wrong/contentless
# -> excluded from the ref merge and DECLARED on the staged record via
# dropped_urls_dead (the build's REF-DROP guard reads the declaration).
REF_DROPS = {
    "T100000130331": {"drop_existing": {  # Darwin LNG
        "https://turbolab.tamu.edu/wp-content/uploads/2018/08/Lecture-08.pdf":
            "generic gas-turbine lecture PDF; does not mention Darwin LNG",
    }},
    "T100000130340": {"drop_existing": {  # QCLNG
        "https://www.youtube.com/watch?v=mFB3arwpSKY&t=8s":
            "Bechtel construction video; no captive-power content",
    }},
    "T100000130344": {"drop_existing": {  # Wheatstone
        "https://www.reuters.com/business/energy/chevron-australia-starts-repair-work-wheatstone-platform-says-spokesperson-2024-06-13/":
            "platform-repair news story; Wayback 20240613101004 full text contains "
            "no turbine/generator/power content",
    }},
    "T100000131159": {"drop_existing": {  # Pasca FLNG (applies only if a row stages)
        "https://www.youtube.com/watch?v=wnpzWwNIXRE&t=121s":
            "YouTube video; not a verifiable citation for the claim",
    }},
    "T100000130860": {"drop_own": [  # Equus FLNG — bare homepage, banned in all lanes
        "http://equusenergy.com.au/",
    ]},
}

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
assert set(records) == scope_tids, (
    f"shard coverage != worklist: missing {scope_tids - set(records)}, "
    f"extra {set(records) - scope_tids}")
assert len(records) == EXPECTED_TERMINALS

# apply QC-gate patches
for tid, patch in VERDICT_OVERRIDES.items():
    r = records.get(tid)
    assert r, f"VERDICT_OVERRIDES tid missing from shard results: {tid}"
    for k, v in patch.items():
        if k == "gate_note":
            r["notes"] = (v + " | " + (r.get("notes") or "")).strip(" |")
        else:
            r[k] = v
for tid, drops in REF_DROPS.items():
    r = records.get(tid)
    assert r, f"REF_DROPS tid missing from shard results: {tid}"
    own = set(drops.get("drop_own", []))
    if own:
        r["refs"] = [u for u in r.get("refs", []) if u not in own]

tally = {}
for r in records.values():
    tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
print(f"{REGION}: {len(records)} terminals; {len(superseded)} superseded by recovery; "
      f"verdicts: {tally}")

# --------------------------------------------------------------- gem CSV rows
unit_rows = {}   # terminal_id -> list of unit dicts
with open(CSV, encoding="utf-8-sig", newline="") as fh:
    for row in csv.DictReader(fh):
        unit_rows.setdefault(row["TerminalID"], []).append(row)

# live-DB conflict detection: existing CaptiveGasPower vs shard verdict
preexisting = {}
for tid in scope_tids:
    v = (unit_rows.get(tid) or [{}])[0].get("CaptiveGasPower", "").strip()
    if v:
        preexisting[tid] = v
conflicts = {}
for tid, old in preexisting.items():
    verdict = records[tid]["verdict"]
    agrees = (old == "True" and verdict == "YES") or (old == "False" and verdict == "NO")
    if not agrees and tid not in ADJUDICATED_OVERTURNS:
        conflicts[tid] = (old, verdict, records[tid].get("terminal"))
assert not conflicts, (
    "live-DB value vs shard verdict conflicts need QC-gate adjudication in "
    f"ADJUDICATED_OVERTURNS: {conflicts}")

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
updates = []
for tid, r in sorted(records.items(), key=lambda kv: (kv[1].get("country", ""), kv[1].get("terminal", ""))):
    is_yes = r["verdict"] == "YES"
    staged_overturn = ADJUDICATED_OVERTURNS.get(tid) == "False"
    if not (is_yes or staged_overturn):
        continue
    rows = unit_rows.get(tid)
    assert rows, f"no gem_export rows for {tid} {r.get('terminal')}"
    nb = nearest.get(tid, {})
    drop_existing = REF_DROPS.get(tid, {}).get("drop_existing", {})
    for row in rows:
        existing_urls = URL_RE.findall(row.get("CaptiveGasPower [ref]", "") or "")
        shard_urls = list(r.get("refs", []))
        # ref MERGE: still-valid existing URLs first, then additions (dedup,
        # order-stable); gate-declared wrong/contentless URLs drop with declaration
        ref_urls, seen, dropped = [], set(), []
        for u in existing_urls + shard_urls:
            u = u.rstrip(".,;")
            if u in seen:
                continue
            seen.add(u)
            if u in drop_existing:
                dropped.append(u)
            else:
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
        if dropped:
            rec["dropped_urls_dead"] = dropped
            reasons = "; ".join(f"{u} — {drop_existing[u]}" for u in dropped)
            rec["source_notes"] = (rec["source_notes"]
                                   + f" [REF DROP declared (QC gate): {reasons}]").strip()
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
        kept = preexisting.get(tid) and ADJUDICATED_OVERTURNS.get(tid) == "keep"
        qa.append({
            "category": "captive_power_insufficient",
            "terminal_id": tid,
            "unit_id": "",
            "terminal_name": r.get("terminal", ""),
            "issue": (r.get("captive_summary") or "").strip(),
            "severity": "low",
            "suggested_action": (
                ("Existing CaptiveGasPower value KEPT (QC-gate adjudication); this batch adds no edit. "
                 if kept else
                 "CaptiveGasPower left blank — fuel/equipment for on-site generation undocumented after research (fuel gate: unstated = INSUFFICIENT). ")
                + "Revisit if an equipment spec, EIA chapter, or class record surfaces. "
                + ((r.get("notes") or "").strip()[:400])),
            "gem_field": "CaptiveGasPower",
            "paste_value": "",
        })
    elif preexisting.get(tid) and ADJUDICATED_OVERTURNS.get(tid) == "keep":
        qa.append({
            "category": "captive_power_adjudication",
            "terminal_id": tid,
            "unit_id": "",
            "terminal_name": r.get("terminal", ""),
            "issue": (f"Shard verdict {r['verdict']} conflicts with live-DB "
                      f"CaptiveGasPower={preexisting[tid]}; QC gate adjudicated KEEP "
                      f"(no edit staged). " + (r.get("captive_summary") or "").strip()),
            "severity": "low",
            "suggested_action": ("Existing value stands per the gate adjudication "
                                 "recorded in the record's notes. "
                                 + ((r.get("notes") or "").strip()[:400])),
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
if preexisting:
    print(f"pre-existing live-DB values in scope: { {t: preexisting[t] for t in sorted(preexisting)} }")
print("YES terminals:")
for n in yes_names:
    print("  " + n)
