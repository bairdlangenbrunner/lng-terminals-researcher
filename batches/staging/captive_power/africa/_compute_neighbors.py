"""Compute neighbors_raw.json — nearest-2 GOGPT plants per worklist LNG terminal, 30 km cap.

Run from this directory with GEM_READONLY_DB_URL set:  python _compute_neighbors.py

Unlike the country-scoped increments, this dir's scope is the terminal_id list in
./worklist.json (the coordinate-first audit's uncrawled set) — countries in meta.json
are annotation only. GOGPT is pulled whole-country (by_country=True — never
subnational-filtered, per the blank-area rule). Every row carries gogpt_plant_id
from the start (SOP §3: the three gogpt_* staged columns travel together).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "../../../../scripts"))
from captive_power_colocation import (  # noqa: E402
    _get_engine, haversine_km, load_gogpt_plants, load_lng_terminals)

CSV = str(HERE / "../../../../scripts/gem_export.csv")
CAP_KM = 30.0

worklist = json.loads((HERE / "worklist.json").read_text(encoding="utf-8"))
tids = {w["terminal_id"] for w in worklist}
countries = sorted({w["country"] for w in worklist})
engine = _get_engine()

rows = []
seen = set()
for country in countries:
    terminals = [t for t in load_lng_terminals(CSV, country, area_col="Country/Area")
                 if t.terminal_id in tids]
    plants = [p for p in load_gogpt_plants(engine, country, by_country=True)
              if p.lat is not None and p.lon is not None]
    print(f"{country}: {len(terminals)} worklist terminals, {len(plants)} GOGPT plants")
    for t in terminals:
        seen.add(t.terminal_id)
        if t.lat is None or t.lon is None:
            print(f"  !! no coordinates: {t.name} ({t.terminal_id}) — no neighbor rows")
            continue
        near = sorted(((haversine_km(t.lat, t.lon, p.lat, p.lon), p) for p in plants),
                      key=lambda dp: dp[0])
        for rank, (d, p) in enumerate([dp for dp in near if dp[0] <= CAP_KM][:2], start=1):
            assert p.plant_id, f"GOGPT plant without plant_id: {p.name}"
            rows.append({
                "terminal": t.name,
                "terminal_id": t.terminal_id,
                "country": country,
                "rank": rank,
                "neighboring_plant": p.name,
                "dist_km": round(d, 3),
                "gogpt_mw": p.total_mw,
                "gogpt_units": p.n_units,
                "gogpt_captive": p.captive,
                "gogpt_status": "/".join(sorted(p.statuses)) if p.statuses else "",
                "subnational": p.subnational,
                "relation": "",
                "info_url": "",
                "gogpt_record (nav only)": p.wiki_url,
                "gogpt_plant_id": p.plant_id,
            })

missing = tids - seen
if missing:
    print(f"!! {len(missing)} worklist tids not found in the export: {sorted(missing)}")

(HERE / "neighbors_raw.json").write_text(
    json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"wrote {len(rows)} neighbor rows -> neighbors_raw.json (all with gogpt_plant_id)")
