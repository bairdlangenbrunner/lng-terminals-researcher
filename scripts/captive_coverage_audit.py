#!/usr/bin/env python3
"""Coordinate-first coverage audit for the captive-power cross-tracker workflow.

The universe is EVERY TerminalID in the fresh GEM export, anchored by its
lat/lon point — never a country list. Terminals with missing/invalid
coordinates are a first-class bucket that must be explicitly incorporated,
not silently dropped (the ST-LNG/blank-state and americas-residue misses were
both filter-defined-universe bugs; see CLAUDE.md and the captive SOP).

For each terminal the audit reports:
  - crawled / uncrawled against the union of every LIVE (non-superseded)
    increment's captive_terminal_first.json under batches/staging/captive_power/
  - coordinate status (ok / missing / unparseable / out-of-range)
  - a coarse continent bucket derived from the COORDINATES, cross-checked
    against the Country/Area tag — mismatches are flagged (the Black Sea LNG
    Romania-tag-Georgia-coords class)

Exit status is non-zero if any terminal is uncrawled outside the regions
passed via --pending (comma-separated planned increments), so the audit can
gate a "coverage complete" claim.

Usage (from scripts/):
    python captive_coverage_audit.py                      # full report
    python captive_coverage_audit.py --pending africa,oceania
    python captive_coverage_audit.py --csv out.csv        # per-terminal dump
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STAGING = REPO / "batches" / "staging" / "captive_power"
DEFAULT_EXPORT = Path(__file__).resolve().parent / "gem_export.csv"

# Country -> planned/completed increment, for bucketing the uncrawled set.
# This maps ONLY how work is sharded; it never defines the universe.
REGION_OF_COUNTRY = {}
for _c in (
    "United States,Canada,Mexico,Puerto Rico,Dominican Republic,Jamaica,Panama,"
    "Colombia,Brazil,Chile,Peru,Argentina,Suriname,Trinidad and Tobago,"
    "El Salvador,Venezuela,Antigua and Barbuda,Aruba,Bahamas,Ecuador,Haiti,"
    "Honduras,Nicaragua,Uruguay,Barbados,Bermuda,Costa Rica,Cuba,Curaçao,"
    "Grenada,Guatemala,Guyana,Saint Lucia,US Virgin Islands,Bolivia,Paraguay"
).split(","):
    REGION_OF_COUNTRY[_c] = "americas"
for _c in (
    "Albania,Belgium,Croatia,Cyprus,Estonia,Finland,France,Georgia,Germany,"
    "Gibraltar,Greece,Ireland,Italy,Latvia,Lithuania,Malta,Montenegro,"
    "Netherlands,Norway,Poland,Portugal,Romania,Russia,Spain,Sweden,Türkiye,"
    "Ukraine,United Kingdom,Bulgaria,Denmark,Iceland,Slovenia"
).split(","):
    REGION_OF_COUNTRY[_c] = "europe"
for _c in (
    "Bangladesh,Brunei,Cambodia,China,Hong Kong,India,Indonesia,Japan,"
    "Malaysia,Myanmar,Pakistan,Philippines,Singapore,South Korea,Sri Lanka,"
    "Taiwan,Thailand,Turkmenistan,Vietnam"
).split(","):
    REGION_OF_COUNTRY[_c] = "asia"
for _c in (
    "Bahrain,Iran,Iraq,Israel,Jordan,Kuwait,Lebanon,Oman,Qatar,"
    "United Arab Emirates,Yemen,Saudi Arabia"
).split(","):
    REGION_OF_COUNTRY[_c] = "middle-east-gulf"
for _c in (
    "Algeria,Angola,Benin,Botswana,Cameroon,Côte d'Ivoire,Djibouti,Egypt,"
    "Equatorial Guinea,Gabon,Ghana,Guinea,Kenya,Libya,Mauritania,Mauritius,"
    "Morocco,Mozambique,Namibia,Nigeria,Republic of the Congo,Senegal,"
    "Sierra Leone,South Africa,Sudan,Tanzania,Western Sahara"
).split(","):
    REGION_OF_COUNTRY[_c] = "africa"
for _c in "Australia,New Zealand,Papua New Guinea,Timor-Leste,Fiji".split(","):
    REGION_OF_COUNTRY[_c] = "oceania"


def continent_from_coords(lat: float, lon: float) -> str:
    """Coarse continent bucket from a point. Advisory cross-check only —
    boxes are deliberately rough; a mismatch is a flag to look, not a verdict."""
    if lon < -30:
        return "americas"
    if lat < -8 and lon > 100:
        return "oceania"
    if lon > 58 or (lat < 12 and lon > 42):
        return "asia" if lat > -12 or lon > 100 else "africa"
    if lat > 36 and -12 <= lon <= 60:
        return "europe"
    if 12 <= lat <= 36 and 32 <= lon <= 60:
        return "middle-east-gulf"
    if lat < 38 and -20 <= lon <= 52:
        return "africa"
    return "unassigned"


def parse_coord(raw: str, lo: float, hi: float):
    raw = (raw or "").strip()
    if not raw:
        return None, "missing"
    try:
        v = float(raw)
    except ValueError:
        return None, "unparseable"
    if not lo <= v <= hi:
        return None, "out_of_range"
    return v, "ok"


def load_crawled() -> dict[str, list[str]]:
    """terminal_id -> live increments that researched it (SCREENED counts:
    a screen is a recorded verdict, but it must be recorded, not implicit)."""
    crawled = defaultdict(list)
    for meta_path in sorted(STAGING.glob("*/meta.json")):
        meta = json.loads(meta_path.read_text())
        if meta.get("status") == "superseded" or meta.get("superseded_by"):
            continue
        tf_path = meta_path.parent / "captive_terminal_first.json"
        if not tf_path.exists():
            continue
        for rec in json.loads(tf_path.read_text()):
            tid = rec.get("terminal_id")
            if tid:
                crawled[tid].append(meta_path.parent.name)
    return crawled


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gem-csv", default=str(DEFAULT_EXPORT))
    ap.add_argument("--pending", default="",
                    help="comma-separated increments still planned; uncrawled "
                         "terminals bucketed there don't fail the audit")
    ap.add_argument("--csv", help="write the per-terminal table to this path")
    args = ap.parse_args()

    pending = {s.strip() for s in args.pending.split(",") if s.strip()}
    crawled = load_crawled()

    terminals = {}
    with open(args.gem_csv, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            tid = row["TerminalID"]
            if tid in terminals:
                continue  # unit-rows duplicate terminal-level fields
            lat, lat_st = parse_coord(row.get("Latitude", ""), -90, 90)
            lon, lon_st = parse_coord(row.get("Longitude", ""), -180, 180)
            coord_status = "ok" if lat_st == lon_st == "ok" else (
                lat_st if lat_st != "ok" else lon_st)
            country = (row.get("Country/Area") or "").strip()
            region = REGION_OF_COUNTRY.get(country, "UNMAPPED_COUNTRY")
            cont = (continent_from_coords(lat, lon)
                    if coord_status == "ok" else "no_coords")
            terminals[tid] = {
                "terminal_id": tid,
                "terminal": row.get("TerminalName", ""),
                "country": country,
                "region": region,
                "coord_status": coord_status,
                "lat": lat, "lon": lon,
                "coord_continent": cont,
                "crawled_by": ";".join(crawled.get(tid, [])),
            }

    universe = set(terminals)
    crawled_ids = universe & set(crawled)
    orphan_crawled = set(crawled) - universe  # staged ids absent from export
    uncrawled = universe - crawled_ids

    by_region = defaultdict(list)
    for tid in uncrawled:
        by_region[terminals[tid]["region"]].append(tid)

    print(f"universe (unique TerminalIDs in export): {len(universe)}")
    print(f"crawled (live increments):               {len(crawled_ids)}")
    print(f"uncrawled:                               {len(uncrawled)}")
    missing_coords = [t for t in terminals.values() if t["coord_status"] != "ok"]
    print(f"missing/invalid coordinates:             {len(missing_coords)}"
          f" (crawled: {sum(1 for t in missing_coords if t['crawled_by'])})")
    for t in missing_coords:
        mark = "OK-crawled" if t["crawled_by"] else "** UNCRAWLED **"
        print(f"    [{t['coord_status']}] {t['terminal_id']} {t['terminal']}"
              f" ({t['country']}) {mark}")

    mismatches = [t for t in terminals.values()
                  if t["coord_status"] == "ok"
                  and t["coord_continent"] not in ("unassigned", t["region"])]
    if mismatches:
        print(f"\ncountry-tag vs coordinate mismatches to eyeball: {len(mismatches)}")
        for t in sorted(mismatches, key=lambda x: x["terminal_id"]):
            print(f"    {t['terminal_id']} {t['terminal']}: tagged"
                  f" {t['country']} ({t['region']}) but coords sit in"
                  f" {t['coord_continent']}")

    print("\nuncrawled by increment bucket:")
    failing = 0
    for region in sorted(by_region):
        ids = by_region[region]
        tag = "pending (planned)" if region in pending else "** NOT COVERED **"
        if region not in pending:
            failing += len(ids)
        print(f"  {region}: {len(ids)}  [{tag}]")
        for tid in sorted(ids):
            t = terminals[tid]
            print(f"      {tid} {t['terminal']} ({t['country']},"
                  f" coords {t['coord_status']})")

    if orphan_crawled:
        print(f"\ncrawled ids no longer in the export (renamed/deleted?): "
              f"{sorted(orphan_crawled)}")

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(next(iter(terminals.values()))))
            w.writeheader()
            w.writerows(terminals.values())
        print(f"\nper-terminal table -> {args.csv}")

    if failing:
        print(f"\nFAIL: {failing} terminals uncrawled outside planned "
              f"increments ({', '.join(sorted(pending)) or 'none declared'})")
        return 1
    print("\nOK: every terminal is crawled or in a declared planned increment")
    return 0


if __name__ == "__main__":
    sys.exit(main())
