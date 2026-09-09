"""Compute neighbors_raw.json — nearest-2 GOGPT plants per LNG terminal, 30 km cap.

Run from this directory with GEM_READONLY_DB_URL set:  python _compute_neighbors.py

Reads the country list from ./meta.json and the LNG side from
../../../../scripts/gem_export.csv; pulls GOGPT whole-country (by_country=True —
never subnational-filtered, per the blank-area rule). Every row carries
gogpt_plant_id from the start (SOP §3: the three gogpt_* staged columns travel
together; asia dropped the id and needed a backfill script).
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

countries = json.loads((HERE / "meta.json").read_text(encoding="utf-8"))["countries"]
engine = _get_engine()

rows = []
for country in countries:
    terminals = load_lng_terminals(CSV, country, area_col="Country/Area")
    plants = [p for p in load_gogpt_plants(engine, country, by_country=True)
              if p.lat is not None and p.lon is not None]
    print(f"{country}: {len(terminals)} terminals, {len(plants)} GOGPT plants")
    for t in terminals:
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

(HERE / "neighbors_raw.json").write_text(
    json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"wrote {len(rows)} neighbor rows -> neighbors_raw.json (all with gogpt_plant_id)")
