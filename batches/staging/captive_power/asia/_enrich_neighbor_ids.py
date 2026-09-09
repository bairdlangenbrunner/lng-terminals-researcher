"""Add gogpt_plant_id to every row of neighbors_raw.json.

The original neighbors computation kept plant name/wiki/MW but dropped the GOGPT
plant_id, which left the staged-row gogpt_plant_id column blank while gogpt_plant
was named — wrong per the standing convention (europe/americas fill the id for
every named plant, regardless of GOGPT's own captive flag).

Run from this directory with GEM_READONLY_DB_URL set:
    python _enrich_neighbor_ids.py
Rewrites neighbors_raw.json in place; fails loud on any unmatched or ambiguous
plant name so a silent blank can't ship again.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE / "../../../../scripts"))
from captive_power_colocation import _get_engine, load_gogpt_plants  # noqa: E402

neighbors = json.loads((HERE / "neighbors_raw.json").read_text(encoding="utf-8"))
countries = sorted({nb["country"] for nb in neighbors})

engine = _get_engine()
by_name = defaultdict(list)   # (country, name) -> [GogptPlant]
for c in countries:
    for p in load_gogpt_plants(engine, c, by_country=True):
        by_name[(c, p.name)].append(p)
    print(f"{c}: GOGPT plants loaded")

unmatched, ambiguous = [], []
for nb in neighbors:
    cands = by_name.get((nb["country"], nb["neighboring_plant"]), [])
    if len(cands) > 1:  # same name twice in one country: disambiguate by subnational
        sub = [p for p in cands if p.subnational == nb.get("subnational")]
        cands = sub or cands
    if not cands:
        unmatched.append(nb["neighboring_plant"])
    elif len(cands) > 1:
        ambiguous.append(nb["neighboring_plant"])
    else:
        nb["gogpt_plant_id"] = cands[0].plant_id

if unmatched or ambiguous:
    sys.exit(f"FAIL — unmatched: {sorted(set(unmatched))}; ambiguous: {sorted(set(ambiguous))}")

(HERE / "neighbors_raw.json").write_text(
    json.dumps(neighbors, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"OK — gogpt_plant_id set on all {len(neighbors)} neighbor rows")
