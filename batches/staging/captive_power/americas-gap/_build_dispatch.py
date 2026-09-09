"""Build dispatch/shard_*.json worklists for the researcher subagents.

Run from this directory:  python _build_dispatch.py
Scope = ./worklist.json (the coordinate-first audit's uncrawled americas set),
NOT a country list. Reads ../../../../scripts/gem_export.csv + the per-country
deterministic-prior worklist CSVs in ../../../deliverables/
(captive_worklist_20260801_1330_ET_<slug>.csv), merges them terminal-level, and
writes one shard JSON per chunk (same shape as ../middle-east-gulf/dispatch/).
Max 8 terminals per shard, grouped by country.

Freeport + Texas LNG carry a research_hint: their documented-NO verdicts from the
2026-07-10 texas run were memo-only, the memo was pruned uncommitted, so they are
re-researched here rather than memo-ported (kickoff backfill note, amended).
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
CSV = HERE / "../../../../scripts/gem_export.csv"
DELIV = HERE / "../../../deliverables"
STAMP = "20260801_1330_ET"
MAX_PER_SHARD = 8

HINTS = {
    "Freeport LNG Terminal": ("2026-07-10 texas run returned a documented NO (electric-drive "
                              "trains on ERCOT grid) but the citations were memo-only and lost; "
                              "re-verify that NO from primary sources."),
    "Texas LNG Terminal": ("2026-07-10 texas run returned a documented NO (Baker Hughes electric "
                           "motor drives / renewable power) but the citations were memo-only and "
                           "lost; re-verify that NO from primary sources."),
}

worklist = json.loads((HERE / "worklist.json").read_text(encoding="utf-8"))
tids = {w["terminal_id"] for w in worklist}
countries = sorted({w["country"] for w in worklist})
SLUG = {c: c.lower().replace(" ", "-") for c in countries}

rows_by_tid = defaultdict(list)
with open(CSV, encoding="utf-8-sig", newline="") as fh:
    for r in csv.DictReader(fh):
        if r["TerminalID"] in tids:
            rows_by_tid[r["TerminalID"]].append(r)
assert set(rows_by_tid) == tids, f"missing from export: {tids - set(rows_by_tid)}"

prior = {}
for c, slug in SLUG.items():
    wl = DELIV / f"captive_worklist_{STAMP}_{slug}.csv"
    with open(wl, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            prior[r["lng_terminal_id"]] = r

def terminal_obj(tid, rows):
    r0 = rows[0]
    p = prior.get(tid, {})
    ftypes = sorted({r["FacilityType"] for r in rows if r.get("FacilityType")})
    obj = {
        "terminal_id": tid,
        "terminal": r0["TerminalName"],
        "country": r0["Country/Area"],
        "facility_type": ftypes,
        "status_by_unit": [{"unit": r.get("UnitName", "") or "--",
                            "unit_id": r.get("UnitID", ""),
                            "status": r.get("Status", ""),
                            "substatus": r.get("Substatus", "")} for r in rows],
        "n_unit_rows": len(rows),
        "state_province": r0.get("State/Province", ""),
        "lat": r0.get("Latitude", ""),
        "lon": r0.get("Longitude", ""),
        "floating": r0.get("Floating", ""),
        "offshore": r0.get("Offshore", ""),
        "vessel": r0.get("FloatingVesselName", ""),
        "owner": r0.get("Owner", ""),
        "operator": r0.get("Operator", ""),
        "captive_gas_power_current": r0.get("CaptiveGasPower", ""),
        "captive_gas_power_ref_current": r0.get("CaptiveGasPower [ref]", ""),
        "power_plants_supplied": r0.get("PowerPlantsSupplied", ""),
        "gogpt_prior": p.get("gogpt_prior", "no"),
        "gogpt_prior_tier": p.get("gogpt_prior_tier", ""),
        "gogpt_plant": p.get("gogpt_plant", ""),
        "gogpt_captive": p.get("gogpt_captive", ""),
        "gogpt_total_mw": p.get("gogpt_total_mw", ""),
        "gogpt_dist_km": p.get("dist_km", ""),
        "suggested_bucket": p.get("suggested_bucket", "deep"),
    }
    if r0["TerminalName"] in HINTS:
        obj["research_hint"] = HINTS[r0["TerminalName"]]
    return obj

by_country = defaultdict(list)
for tid, rows in rows_by_tid.items():
    by_country[rows[0]["Country/Area"]].append(terminal_obj(tid, rows))
for c in by_country:
    by_country[c].sort(key=lambda t: t["terminal"])

# pack: big countries chunked alone; small countries greedily combined
(HERE / "dispatch").mkdir(exist_ok=True)
shards = []
small_bin, small_names = [], []
for c in sorted(by_country, key=lambda c: -len(by_country[c])):
    ts = by_country[c]
    if len(ts) >= 5:
        for i in range(0, len(ts), MAX_PER_SHARD):
            chunk = ts[i:i + MAX_PER_SHARD]
            shards.append((f"{SLUG[c]}-{i // MAX_PER_SHARD + 1:02d}", chunk))
    else:
        if len(small_bin) + len(ts) > MAX_PER_SHARD:
            shards.append(("+".join(small_names), small_bin))
            small_bin, small_names = [], []
        small_bin += ts
        small_names.append(SLUG[c])
if small_bin:
    shards.append(("+".join(small_names), small_bin))

total = 0
for i, (slug, terminals) in enumerate(shards, start=1):
    assert 0 < len(terminals) <= MAX_PER_SHARD, f"{slug}: {len(terminals)}"
    name = f"shard_{i:02d}_{slug}"
    (HERE / "dispatch" / f"{name}.json").write_text(
        json.dumps({"shard": name, "terminals": terminals}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    total += len(terminals)
    print(f"{name}: {len(terminals)} terminals")
print(f"total {total} terminals across {len(shards)} shards")
assert total == len(tids)
