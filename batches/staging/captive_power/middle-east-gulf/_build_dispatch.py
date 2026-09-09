"""Build dispatch/shard_*.json worklists for the researcher subagents.

Run from this directory:  python _build_dispatch.py
Reads ../../../../scripts/gem_export.csv + the per-country deterministic-prior
worklist CSVs in ../../../deliverables/ (captive_worklist_<STAMP>_<slug>.csv),
merges them terminal-level, and writes one shard JSON per SHARDS entry
(same shape as ../asia/dispatch/). Max 8 terminals per shard.
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
CSV = HERE / "../../../../scripts/gem_export.csv"
DELIV = HERE / "../../../deliverables"
STAMP = "20260801_1201_ET"

SHARDS = [
    ("01_iran", ["Iran"]),
    ("02_uae-bahrain", ["United Arab Emirates", "Bahrain"]),
    ("03_qatar-kuwait-oman-yemen", ["Qatar", "Kuwait", "Oman", "Yemen"]),
    ("04_israel-lebanon", ["Israel", "Lebanon"]),
    ("05_iraq-jordan", ["Iraq", "Jordan"]),
]

SLUG = {c: c.lower().replace(" ", "-") for shard in SHARDS for c in shard[1]}

# terminal-level rollup from the fresh export
rows_by_tid = defaultdict(list)
countries = set(SLUG)
with open(CSV, encoding="utf-8-sig", newline="") as fh:
    for r in csv.DictReader(fh):
        if r["Country/Area"] in countries:
            rows_by_tid[r["TerminalID"]].append(r)

# deterministic priors, keyed by terminal_id
prior = {}
for c, slug in SLUG.items():
    wl = DELIV / f"captive_worklist_{STAMP}_{slug}.csv"
    with open(wl, encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            prior[r["lng_terminal_id"]] = r

(HERE / "dispatch").mkdir(exist_ok=True)
total = 0
for shard_slug, shard_countries in SHARDS:
    terminals = []
    for tid, rows in sorted(rows_by_tid.items(), key=lambda kv: (kv[1][0]["Country/Area"], kv[1][0]["TerminalName"])):
        r0 = rows[0]
        if r0["Country/Area"] not in shard_countries:
            continue
        p = prior.get(tid, {})
        ftypes = sorted({r["FacilityType"] for r in rows if r.get("FacilityType")})
        terminals.append({
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
        })
    assert 0 < len(terminals) <= 8, f"shard {shard_slug}: {len(terminals)} terminals"
    out = HERE / "dispatch" / f"shard_{shard_slug}.json"
    out.write_text(json.dumps({"shard": shard_slug, "terminals": terminals},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    total += len(terminals)
    print(f"shard_{shard_slug}: {len(terminals)} terminals")
print(f"total {total} terminals across {len(SHARDS)} shards")
