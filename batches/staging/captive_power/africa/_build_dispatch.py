"""Build dispatch/shard_*.json worklists for the researcher subagents.

Run from this directory:  python _build_dispatch.py
Scope = ./worklist.json (the coordinate-first audit's uncrawled set for this region),
NOT a country list. Unlike americas-gap there are no per-country deterministic-prior
worklist CSVs in deliverables/ for this region, so the GOGPT prior comes straight from
./neighbors_raw.json (rank-1 nearest plant within 30 km, with its captive flag/MW/status).
Max 8 terminals per shard, grouped by country. Same shard shape as ../americas-gap/dispatch/.
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
CSV = HERE / "../../../../scripts/gem_export.csv"
MAX_PER_SHARD = 8

worklist = json.loads((HERE / "worklist.json").read_text(encoding="utf-8"))
tids = {w["terminal_id"] for w in worklist}
countries = sorted({w["country"] for w in worklist})
SLUG = {c: c.lower().replace(" ", "-").replace("'", "") for c in countries}

rows_by_tid = defaultdict(list)
with open(CSV, encoding="utf-8-sig", newline="") as fh:
    for r in csv.DictReader(fh):
        if r["TerminalID"] in tids:
            rows_by_tid[r["TerminalID"]].append(r)
assert set(rows_by_tid) == tids, f"missing from export: {tids - set(rows_by_tid)}"

nb1 = {}
for nb in json.loads((HERE / "neighbors_raw.json").read_text(encoding="utf-8")):
    if nb["rank"] == 1:
        nb1[nb["terminal_id"]] = nb

def terminal_obj(tid, rows):
    r0 = rows[0]
    nb = nb1.get(tid)
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
        "gogpt_prior": "yes" if nb else "no",
        "gogpt_plant": nb["neighboring_plant"] if nb else "",
        "gogpt_captive": str(nb["gogpt_captive"]) if nb else "",
        "gogpt_total_mw": str(nb["gogpt_mw"]) if nb else "",
        "gogpt_dist_km": str(nb["dist_km"]) if nb else "",
        "suggested_bucket": "deep",
    }
    return obj

by_country = defaultdict(list)
for tid, rows in rows_by_tid.items():
    by_country[rows[0]["Country/Area"]].append(terminal_obj(tid, rows))
for c in by_country:
    by_country[c].sort(key=lambda t: t["terminal"])

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
