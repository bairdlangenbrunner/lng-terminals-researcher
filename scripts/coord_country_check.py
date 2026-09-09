#!/usr/bin/env python3
"""Does every LNG terminal's coordinate actually lie in the country it claims?

A mechanical geolocation QC test. Every terminal row carries a `Country/Area`
and a lat/lon; nothing in the GEM editor cross-checks the two, so a sign flip,
a transposed lat/lon, or a copy-paste from a neighbouring record survives
indefinitely. This walks each terminal, measures the distance from its point to
the claimed country's polygon, and reports the ones that don't belong.

LNG terminals are coastal and often offshore (FSRUs, FLNG), so "outside the
polygon" is normal and is NOT the test — the test is *distance*. A berth sits
within a few km of its coastline; a point 700 km out to sea in another
country's waters is an error. Default gate is 30 km, tunable with --max-km.

For every flagged terminal the script also tries the three classic data-entry
transforms — negate the latitude, negate the longitude, swap lat/lon — and
reports any that land the point back inside the claimed country. A transform
that fixes the point is near-proof of the mechanism, and turns a vague
"coordinates look wrong" into a specific staged correction.

    python coord_country_check.py                     # all LNG terminals
    python coord_country_check.py --max-km 50         # looser gate
    python coord_country_check.py --country Cameroon
    python coord_country_check.py --status operating construction
    python coord_country_check.py --out ../batches/staging/qc-<stamp>/coord_country_check.json

Country geometry is Natural Earth 1:50m from cartopy's local cache (no
network). 1:50m is coarse in exactly the places LNG terminals sit, so four
false-positive classes are handled explicitly rather than reported:

* **Offshore by design.** An FLNG sits over its gas field, routinely 150-450 km
  out (Prelude, Ichthys, Coral South, Delfin). Anything whose name or
  FacilityType says FLNG/FSRU/floating gets the much wider `--max-km-offshore`
  gate.
* **Dependencies.** NE lists some territories as their own ADMIN — Ashmore and
  Cartier Islands is Australian, and NE's `Morocco` polygon covers the Dakhla
  coast its `Western Sahara` polygon omits. `TERRITORY_ALIASES` makes those
  count as the claimed country.
* **Disputed geometry.** NE assigns Crimea to Russia; GEM assigns it to Ukraine
  deliberately. `DISPUTED_GEOMETRY` reports those as `disputed_geometry`, never
  as an error — do not "fix" the coordinate.
* **Dropped small islands.** At 1:50m an archipelago loses its cays, so a
  correct point can measure 100 km from its own country (Das Island, Yangshan,
  Qushan, Ocean Cay). Every finding therefore also carries its distance to the
  1:10m coastline — a point a few km from *some* shore is an island or coastal
  berth the country polygon simply doesn't draw, and is graded `island_or_coastal`
  rather than reported as an error. `COARSE_GEOMETRY_COUNTRIES` widens the
  country gate on top of that.

A second, independent test runs over *every* terminal, whether or not it fails
the country gate: **distance to the nearest shoreline**. Past `--inland-km`
(default 75) the point is split by whether it sits over land or over water. Over
water it is an offshore field or berth — expected, and reported as info. Over
land it has no plausible marine access, which is a *scope* question, not a
coordinate one — `import`/`export` requires LNG crossing a
border by ship, so a landlocked plant is a domestic virtual-pipeline operation
that the methodology excludes. FLNG/FSRU rows are exempt: they float over the
field, hundreds of km out, and that is correct.

Read its output as three groups, because the mechanism differs:

* **Landlocked** (Botswana, Yakutsk, Prince George, Wyalusing) — genuinely no
  marine access. Either out of scope or the coordinate points at the wrong site.
* **Navigable river** (Yueyang, Wuhu, Jiujiang on the Yangtze; Itacoatiara on
  the Amazon) — a real berth, but whether LNG reaches it by sea-going carrier or
  by domestic barge decides scope. Itacoatiara takes ocean vessels; a Yangtze
  river terminal fed by coastal redistribution does not.
* **Wrong coordinate** (Pechora LNG sits 376 km inland; the project was at
  Indiga on the Barents coast) — the site is coastal, the stored point isn't.

Only FLNG/FPSO/deepwater names are exempt from this test. An FSRU is *not*: it
moors at a berth, so an FSRU 660 km up the Amazon (Itacoatiara) is a finding
worth seeing, whereas an FLNG 200 km over its field is not.

Below ~50 km this metric stops discriminating: ship-channel terminals (Lake
Charles, Cameron, Plaquemines) and offshore berths (Adriatic, Northeast Gateway,
Neptune) are correctly far from open coast. That is why the gate is 75 km and
not 10.

A working repair transform is evidence, not proof: UTM Offshore FLNG's
lat/lon swap lands neatly inside Nigeria, but inland near Osogbo — 250 km from
any water an FLNG could float in, so the flagged original is the right value.
Always sanity-check the repair against what the facility actually is.

Offline and read-only: the fresh export is the only input.
"""

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

NE_DIR = Path.home() / ".local/share/cartopy/shapefiles/natural_earth"
NE_SHP = NE_DIR / "cultural" / "ne_50m_admin_0_countries.shp"
# 1:10m coastline resolves the small islands 1:50m country polygons drop
NE_COAST = NE_DIR / "physical" / "ne_10m_coastline.shp"
# land vs ocean tells an inland river port from an offshore gas field
NE_LAND = NE_DIR / "physical" / "ne_50m_land.shp"

# GEM `Country/Area` values with no Natural Earth 1:50m ADMIN/NAME/NAME_LONG match
NAME_FIXES = {
    "Türkiye": "Turkey",
    "Gibraltar": None,   # no polygon at 1:50m — reported, never flagged
}

# NE ADMIN names that are, for this test, the claimed country
TERRITORY_ALIASES = {
    "Ashmore and Cartier Islands": {"Australia"},
    "Coral Sea Islands": {"Australia"},
    "Heard Island and McDonald Islands": {"Australia"},
    # NE's Morocco polygon covers the Dakhla coast its Western Sahara omits
    "Morocco": {"Western Sahara"},
    "Western Sahara": {"Morocco"},
    "United States of America": {"United States"},
    "Turkey": {"Türkiye"},
}

# (GEM country, NE nearest) pairs where NE encodes a political assignment GEM
# deliberately differs on. Reported, never treated as a coordinate error.
DISPUTED_GEOMETRY = {
    ("Ukraine", "Russia"),          # Crimea
}

# 1:50m drops small cays, so a correct point can sit far from its own polygon
COARSE_GEOMETRY_COUNTRIES = {
    "Bahamas", "The Bahamas", "Maldives", "Marshall Islands", "Kiribati",
    "Tuvalu", "Micronesia", "Palau", "Seychelles", "Antigua and Barbuda",
    "Saint Vincent and the Grenadines", "Turks and Caicos Islands",
}
COARSE_GATE_KM = 150.0

# within this of any 1:10m shoreline, the point is on an island or a berth the
# 1:50m country polygon doesn't draw — not a misplaced coordinate
COASTLINE_TOLERANCE_KM = 8.0

# past this from any shoreline a facility has no plausible marine access, which
# is a scope question. Below ~50 km the metric can't tell a ship channel or an
# offshore berth from an error, so the gate sits well clear of that band.
INLAND_KM = 75.0

# a facility that floats or moors offshore is legitimately outside the country
# polygon; used for the country-distance gate
OFFSHORE_MARKERS = ("flng", "fsru", "floating", "fpso", "deepwater")

# only field-based facilities are exempt from the inland test — an FSRU moors at
# a berth, so its distance from shore is still meaningful
FIELD_BASED_MARKERS = ("flng", "fpso", "deepwater")

DEFAULT_MAX_KM = 30.0
DEFAULT_MAX_KM_OFFSHORE = 250.0
PROJECT_URL = "https://gem-project-db.herokuapp.com/projects/edit/{}"


def load_countries():
    import geopandas as gpd
    if not NE_SHP.exists():
        sys.exit(f"Natural Earth 1:50m countries not found at {NE_SHP}\n"
                 f"populate cartopy's cache first, e.g.\n"
                 f"  python -c \"import cartopy.io.shapereader as s; "
                 f"s.natural_earth(resolution='50m', category='cultural', "
                 f"name='admin_0_countries')\"")
    gdf = gpd.read_file(NE_SHP)
    geoms = {}
    for col in ("ADMIN", "NAME_LONG", "NAME", "SOVEREIGNT"):
        if col not in gdf.columns:
            continue
        for name, geom in zip(gdf[col], gdf.geometry):
            if name and name not in geoms:      # first column wins; ADMIN is best
                geoms[name] = geom
    # a sovereign that owns several rows (dependencies) should union them
    from shapely.ops import unary_union
    grouped = defaultdict(list)
    for name, geom in zip(gdf["ADMIN"], gdf.geometry):
        grouped[name].append(geom)
    for name, parts in grouped.items():
        if len(parts) > 1:
            geoms[name] = unary_union(parts)
    return gdf, geoms


def load_coastline():
    """1:10m coastline, unioned once — used to tell an island from an error."""
    if not NE_COAST.exists():
        print(f"  NOTE: {NE_COAST.name} not cached; small-island findings will be "
              f"reported without a coastline check", file=sys.stderr)
        return None
    import geopandas as gpd
    from shapely.ops import unary_union
    return unary_union(list(gpd.read_file(NE_COAST).geometry))


def load_land():
    """1:50m land, unioned once — over land vs over water for the inland test."""
    if not NE_LAND.exists():
        print(f"  NOTE: {NE_LAND.name} not cached; far-from-shore findings can't be "
              f"split into inland vs offshore", file=sys.stderr)
        return None
    import geopandas as gpd
    from shapely.ops import unary_union
    return unary_union(list(gpd.read_file(NE_LAND).geometry))


def km_between(point, geom):
    """Approximate great-circle distance from a point to a polygon, in km.

    shapely works in degrees here, so scale the components separately: a degree
    of longitude shrinks with latitude. Good to a few percent, which is far
    inside the tolerance a 30 km gate needs.
    """
    from shapely.ops import nearest_points
    if geom.contains(point):
        return 0.0
    near = nearest_points(point, geom)[1]
    dlat = (near.y - point.y) * 111.32
    dlon = (near.x - point.x) * 111.32 * math.cos(math.radians((near.y + point.y) / 2))
    return math.hypot(dlat, dlon)


def terminals(csv_path, fuels):
    """One record per TerminalID; coordinates come off the first row that has them."""
    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        sys.exit(f"no rows in {csv_path}")

    by_tid = defaultdict(list)
    for r in rows:
        by_tid[r["TerminalID"]].append(r)

    out = []
    for tid, group in by_tid.items():
        if fuels and not any(r["Fuel"].strip().lower() in fuels for r in group):
            continue
        coord_row = next((r for r in group
                          if r["Latitude"].strip() and r["Longitude"].strip()), None)
        statuses = sorted({r["Status"].strip().lower() for r in group if r["Status"].strip()})
        rec = {
            "terminal_id": tid,
            "terminal": group[0]["TerminalName"],
            "country": group[0]["Country/Area"].strip(),
            "statuses": statuses,
            "accuracy": (coord_row or group[0])["Accuracy"].strip(),
            "facility_types": sorted({r["FacilityType"].strip() for r in group
                                      if r["FacilityType"].strip()}),
            "n_units": len(group),
            "project_url": PROJECT_URL.format(tid.lstrip("T")),
        }
        blob = " ".join([rec["terminal"]] + rec["facility_types"]).lower()
        rec["offshore_expected"] = any(m in blob for m in OFFSHORE_MARKERS)
        rec["field_based"] = any(m in blob for m in FIELD_BASED_MARKERS)

        if coord_row is None:
            rec.update(latitude=None, longitude=None, verdict="no_coordinates")
        else:
            try:
                rec["latitude"] = float(coord_row["Latitude"])
                rec["longitude"] = float(coord_row["Longitude"])
            except ValueError:
                rec.update(latitude=coord_row["Latitude"], longitude=coord_row["Longitude"],
                           verdict="unparseable_coordinates")
        out.append(rec)
    return len(rows), out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", default="gem_export.csv", help="fresh unit-row export")
    ap.add_argument("--max-km", type=float, default=DEFAULT_MAX_KM,
                    help=f"distance from the claimed country that counts as wrong "
                         f"(default {DEFAULT_MAX_KM:g} km)")
    ap.add_argument("--max-km-offshore", type=float, default=DEFAULT_MAX_KM_OFFSHORE,
                    help=f"the same gate for FLNG/FSRU/floating facilities, which sit "
                         f"over their field (default {DEFAULT_MAX_KM_OFFSHORE:g} km)")
    ap.add_argument("--inland-km", type=float, default=INLAND_KM,
                    help=f"further than this from any 1:10m shoreline raises a "
                         f"marine-access scope question (default {INLAND_KM:g} km; "
                         f"FLNG/FSRU exempt)")
    ap.add_argument("--strict", action="store_true",
                    help="report every terminal past --max-km, including the "
                         "offshore/dependency/disputed/coarse-geometry classes")
    ap.add_argument("--country", nargs="*", help="limit to these GEM Country/Area values")
    ap.add_argument("--status", nargs="*", help="limit to terminals with any of these statuses")
    ap.add_argument("--fuel", nargs="*", default=["lng"],
                    help="in-scope Fuel values (default: lng; pass nothing after "
                         "--fuel to include every fuel)")
    ap.add_argument("--out", help="write the findings as JSON here")
    args = ap.parse_args()

    fuels = {f.strip().lower() for f in args.fuel} if args.fuel else set()
    n_rows, recs = terminals(args.csv, fuels)
    _, geoms = load_countries()
    coastline = load_coastline()
    land = load_land()

    if args.country:
        want = {c.lower() for c in args.country}
        recs = [r for r in recs if r["country"].lower() in want]
    if args.status:
        want = {s.lower() for s in args.status}
        recs = [r for r in recs if set(r["statuses"]) & want]

    from shapely.geometry import Point

    findings, missing_geom, no_coords = [], [], []
    disputed, island_ok, inland, offshore_field, checked = [], [], [], [], 0
    for r in recs:
        if r.get("verdict") in ("no_coordinates", "unparseable_coordinates"):
            no_coords.append(r)
            continue
        gem_name = r["country"]
        ne_name = NAME_FIXES.get(gem_name, gem_name)
        geom = geoms.get(ne_name) if ne_name else None
        if geom is None:
            r["verdict"] = "no_geometry"
            missing_geom.append(r)
            continue

        checked += 1
        pt = Point(r["longitude"], r["latitude"])
        km = km_between(pt, geom)

        if coastline is not None and not r["field_based"]:
            kc = km_between(pt, coastline)
            if kc > args.inland_km:
                on_land = land is None or land.contains(pt)
                if on_land:
                    inland.append(dict(
                        r, verdict="inland_marine_access_question",
                        km_to_coastline=round(kc, 1), over_land=True,
                        severity="high" if kc > 3 * args.inland_km else "medium",
                        note=f"{kc:.0f} km inland — confirm LNG reaches this site by "
                             f"sea-going carrier. A landlocked or barge-fed domestic "
                             f"plant is out of scope; a coastal project stored at an "
                             f"inland point needs the coordinate fixed instead"))
                else:
                    offshore_field.append(dict(
                        r, verdict="offshore_field_or_berth",
                        km_to_coastline=round(kc, 1), over_land=False,
                        severity="info",
                        note=f"{kc:.0f} km offshore, over water — an offshore field "
                             f"or berth, expected for this facility type"))

        gate, gate_reason = args.max_km, "coastal"
        if r["offshore_expected"]:
            gate, gate_reason = args.max_km_offshore, "offshore_expected"
        if gem_name in COARSE_GEOMETRY_COUNTRIES and COARSE_GATE_KM > gate:
            gate, gate_reason = COARSE_GATE_KM, "coarse_geometry"
        r["gate_km"], r["gate_reason"] = gate, gate_reason

        if km <= (args.max_km if args.strict else gate):
            continue

        # which country IS this point in (or nearest to)?
        best, best_km = None, float("inf")
        for name, g in geoms.items():
            d = km_between(pt, g)
            if d < best_km:
                best, best_km = name, d
            if d == 0.0:
                break

        # the three classic data-entry transforms
        repairs = []
        for label, lat, lon in (
            ("negate_latitude", -r["latitude"], r["longitude"]),
            ("negate_longitude", r["latitude"], -r["longitude"]),
            ("swap_lat_lon", r["longitude"], r["latitude"]),
        ):
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                continue
            d = km_between(Point(lon, lat), geom)
            if d <= args.max_km:
                repairs.append({"transform": label, "latitude": lat,
                                "longitude": lon, "km_from_country": round(d, 1)})

        # a dependency of the claimed country is not "another country"
        nearest_is_claimed = (best == ne_name
                              or gem_name in TERRITORY_ALIASES.get(best, set())
                              or best in TERRITORY_ALIASES.get(ne_name, set()))

        if (gem_name, best) in DISPUTED_GEOMETRY and not args.strict:
            r.update(verdict="disputed_geometry",
                     km_from_claimed_country=round(km, 1), nearest_country=best,
                     km_to_nearest=round(best_km, 1), candidate_repairs=[],
                     severity="info",
                     note=f"Natural Earth assigns this area to {best}; GEM's "
                          f"{gem_name} is deliberate — do not change the coordinate")
            disputed.append(r)
            continue

        km_coast = round(km_between(pt, coastline), 1) if coastline is not None else None
        island = km_coast is not None and km_coast <= COASTLINE_TOLERANCE_KM

        if island and nearest_is_claimed and not args.strict:
            r.update(verdict="island_or_coastal",
                     km_from_claimed_country=round(km, 1), nearest_country=best,
                     km_to_nearest=round(best_km, 1), km_to_coastline=km_coast,
                     candidate_repairs=[], severity="info",
                     note=f"{km_coast:g} km from the 1:10m shoreline inside/nearest "
                          f"{best} — an island or berth the 1:50m country polygon "
                          f"omits, not a misplaced coordinate")
            island_ok.append(r)
            continue

        r.update(verdict="outside_claimed_country",
                 km_to_coastline=km_coast,
                 km_from_claimed_country=round(km, 1),
                 nearest_country=best,
                 km_to_nearest=round(best_km, 1),
                 nearest_is_claimed_country=nearest_is_claimed,
                 candidate_repairs=repairs,
                 severity=("high" if (not nearest_is_claimed and best_km < km) or repairs
                           else "medium"))
        findings.append(r)

    findings.sort(key=lambda r: (r["severity"] != "high", -r["km_from_claimed_country"]))

    print(f"coordinate/country check — {n_rows} export rows -> {len(recs)} terminals in scope")
    print(f"  checked against geometry : {checked}")
    print(f"  outside claimed country  : {len(findings)}"
          f"  ({sum(1 for f in findings if f['severity'] == 'high')} high)"
          f"  gates: {args.max_km:g} km coastal / {args.max_km_offshore:g} km offshore"
          f"{' [--strict: all classes reported]' if args.strict else ''}")
    print(f"  inland / no marine access: {len(inland)}"
          f"  ({sum(1 for r in inland if r['severity'] == 'high')} high;"
          f" gate {args.inland_km:g} km from shore, over land, FLNG/FPSO exempt)")
    print(f"  offshore field (info)    : {len(offshore_field)}"
          f"  (same gate, but over water)")
    print(f"  island/coastal (info)    : {len(island_ok)}"
          f"  (within {COASTLINE_TOLERANCE_KM:g} km of the 1:10m shoreline)")
    print(f"  disputed geometry (info) : {len(disputed)}")
    print(f"  no coordinates at all    : {len(no_coords)}")
    print(f"  no country geometry      : {len(missing_geom)}"
          f"{' — ' + ', '.join(sorted({m['country'] for m in missing_geom})) if missing_geom else ''}")

    if findings:
        print(f"\n{'country':22s} {'terminal':38s} {'lat':>11s} {'lon':>11s} "
              f"{'km off':>8s}  nearest / repair")
        print("-" * 120)
        for r in findings:
            fix = ("  FIX: " + ", ".join(
                f"{c['transform']} -> {c['latitude']:.4f},{c['longitude']:.4f}"
                for c in r["candidate_repairs"])) if r["candidate_repairs"] else ""
            print(f"{r['severity'][:4].upper():5s}{r['country'][:22]:22s} {r['terminal'][:36]:36s} "
                  f"{r['latitude']:11.5f} {r['longitude']:11.5f} "
                  f"{r['km_from_claimed_country']:8.0f}  "
                  f"in/near {r['nearest_country']} ({r['km_to_nearest']:.0f} km){fix}")
            print(f"{'':27s} {r['terminal_id']}  {'/'.join(r['statuses'])}  "
                  f"accuracy={r['accuracy'] or 'BLANK'}  gate={r['gate_km']:g}km/"
                  f"{r['gate_reason']}  {r['project_url']}")

    if inland:
        print(f"\ninland — no plausible marine access, so a scope question "
              f"(independent of the country test):")
        print(f"  {'km':>6s} {'country':18s} {'terminal':40s} {'status':22s} acc")
        for r in sorted(inland, key=lambda r: -r["km_to_coastline"]):
            print(f"  {r['km_to_coastline']:6.0f} {r['country'][:18]:18s} "
                  f"{r['terminal'][:40]:40s} {'/'.join(r['statuses'])[:22]:22s} "
                  f"{r['accuracy'] or 'BLANK'}  {r['latitude']:.4f},{r['longitude']:.4f}"
                  f"  {r['terminal_id']}")

    if offshore_field:
        print(f"\noffshore field or berth — far from shore but over water, expected:")
        for r in sorted(offshore_field, key=lambda r: -r["km_to_coastline"]):
            print(f"  {r['km_to_coastline']:6.0f} km  {r['country'][:18]:18s} "
                  f"{r['terminal'][:40]:40s} {'/'.join(r['statuses'])[:20]:20s} "
                  f"acc={r['accuracy'] or 'BLANK'}")

    if island_ok:
        print(f"\nisland or coastal berth — 1:50m country polygon just doesn't draw it:")
        for r in sorted(island_ok, key=lambda r: -r["km_from_claimed_country"]):
            print(f"  {r['country'][:20]:20s} {r['terminal'][:40]:40s} "
                  f"{r['km_from_claimed_country']:6.0f} km from polygon, "
                  f"{r['km_to_coastline']:5.1f} km from shoreline")

    if disputed:
        print(f"\ndisputed geometry — GEM's country is deliberate, leave the coordinate alone:")
        for r in disputed:
            print(f"  {r['country'][:20]:20s} {r['terminal'][:44]:44s} "
                  f"{r['terminal_id']}  {r['note']}")

    if no_coords:
        print(f"\nterminals with no usable coordinates ({len(no_coords)}):")
        for r in no_coords:
            print(f"  {r['country'][:20]:20s} {r['terminal'][:44]:44s} "
                  f"{r['terminal_id']}  {'/'.join(r['statuses'])}  {r['verdict']}")

    if args.out:
        payload = {
            "gate_km": args.max_km,
            "gate_km_offshore": args.max_km_offshore,
            "strict": args.strict,
            "inland_km": args.inland_km,
            "export_rows": n_rows,
            "terminals_in_scope": len(recs),
            "checked": checked,
            "geometry_source": str(NE_SHP),
            "findings": findings,
            "disputed_geometry": disputed,
            "island_or_coastal": island_ok,
            "inland_marine_access_question": inland,
            "offshore_field_or_berth": offshore_field,
            "no_coordinates": no_coords,
            "no_geometry": missing_geom,
        }
        Path(args.out).write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
