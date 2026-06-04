"""sweep_worklist_split.py — split the central worklists per country for a regional sweep.

Standard-tier worklist (Update SOP §2.1) = stale_sweep flagged_units ∪ dev_pipeline.units
∪ completeness blank_ref gaps, restricted to Fuel == LNG units (the export carries some
US oil/NGL/NH3 rows that are out of LNG-update scope).

Reads   gem_export.csv, work/stale_sweep.json, work/completeness_sweep.json,
        ../batches/staging/_region_map.json     (country -> {region, slug})
Writes  work/sweep/<region>/<slug>.worklist.json   one per country with a non-empty worklist;
        work/sweep/_index.json                     all countries + counts (dispatch planning:
                                                   zero-worklist countries get no update agent;
                                                   by_state included for >40-unit countries to
                                                   guide sharding).

Run from scripts/ after the fresh pull + stale_sweep.py + completeness_sweep.py.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", default=str(HERE / "gem_export.csv"))
    p.add_argument("--stale", default=str(HERE / "work" / "stale_sweep.json"))
    p.add_argument("--completeness", default=str(HERE / "work" / "completeness_sweep.json"))
    p.add_argument("--region-map", default=str(HERE.parent / "batches" / "staging" / "_region_map.json"))
    p.add_argument("--out", default=str(HERE / "work" / "sweep"))
    p.add_argument("--shard-state-threshold", type=int, default=40,
                   help="include a by_state breakdown in the index for countries with more LNG units than this")
    args = p.parse_args()

    region_map = json.loads(Path(args.region_map).read_text(encoding="utf-8"))["map"]
    stale = json.loads(Path(args.stale).read_text(encoding="utf-8"))
    comp = json.loads(Path(args.completeness).read_text(encoding="utf-8"))

    # LNG-fuel universe from the fresh export.
    lng_units: set[str] = set()
    per_country_units: Counter = Counter()
    per_country_terminals: dict[str, set] = defaultdict(set)
    per_country_state: dict[str, Counter] = defaultdict(Counter)
    with open(args.csv, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if (row.get("Fuel") or "").strip() != "LNG":
                continue
            c = row["Country/Area"]
            lng_units.add(row["UnitID"])
            per_country_units[c] += 1
            per_country_terminals[c].add(row["TerminalID"])
            per_country_state[c][row.get("State/Province") or "?"] += 1

    def keep(entry: dict) -> bool:
        return entry.get("unit_id") in lng_units

    by_country: dict[str, dict] = defaultdict(lambda: {"stale_flags": [], "dev_pipeline": [], "blank_refs": []})
    for e in stale.get("flagged_units", []):
        if keep(e):
            by_country[e["country"]]["stale_flags"].append(e)
    for e in stale.get("dev_pipeline", {}).get("units", []):
        if keep(e):
            by_country[e["country"]]["dev_pipeline"].append(e)
    for e in comp.get("gaps", []):
        if e.get("gap_type") == "blank_ref" and keep(e):
            by_country[e["country"]]["blank_refs"].append(e)

    out_root = Path(args.out)
    index: dict[str, dict] = {r: {} for r in sorted(set(v["region"] for v in region_map.values()))}
    written = 0
    for country, info in sorted(region_map.items()):
        region, slug = info["region"], info["slug"]
        wl = by_country.get(country, {"stale_flags": [], "dev_pipeline": [], "blank_refs": []})
        counts = {k: len(v) for k, v in wl.items()}
        total = sum(counts.values())
        entry = {
            "slug": slug,
            "lng_terminals": len(per_country_terminals.get(country, ())),
            "lng_units": per_country_units.get(country, 0),
            **counts,
            "worklist_total": total,
        }
        if per_country_units.get(country, 0) > args.shard_state_threshold:
            entry["by_state"] = dict(per_country_state[country].most_common())
        index[region][country] = entry
        if total:
            d = out_root / region
            d.mkdir(parents=True, exist_ok=True)
            payload = {"country": country, "region": region, "slug": slug,
                       "source_csv": str(args.csv), "today": stale.get("today"),
                       "counts": counts, **wl}
            (d / f"{slug}.worklist.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            written += 1

    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "_index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"worklists written: {written} (of {len(region_map)} countries) -> {out_root}")
    for region in index:
        tot = sum(c["worklist_total"] for c in index[region].values())
        nz = sum(1 for c in index[region].values() if c["worklist_total"])
        print(f"  {region:12s} countries={len(index[region]):3d} with-worklist={nz:3d} items={tot}")


if __name__ == "__main__":
    main()
