#!/usr/bin/env python3
"""Build the exhaustive dev-pipeline (proposed/construction/shelved) worklist + per-country worklists.

This is the scope-and-resume scaffolding for the EXHAUSTIVE update restricted to
Status in {proposed, construction, shelved} (the `dev_pipeline` block of stale_sweep.py).
It is deliberately SEPARATE from the standard-sweep region dirs so the two efforts don't collide.

  python batches/staging/devpipeline_exhaustive/_build_worklist.py            # (re)writes WORKLIST.json only
  python batches/staging/devpipeline_exhaustive/_build_worklist.py <region>   # + per-country <region>/<slug>.worklist.json

Inputs (must be fresh — pull + stale_sweep run this same batch):
  scripts/work/stale_sweep.json   -> dev_pipeline.units (the 473 in-scope unit rows)
  scripts/gem_export.csv          -> current field values (utf-8-sig; first header has a BOM)
  batches/staging/_region_map.json-> country -> {region, slug}

Per-unit worklist carries, for each in-scope unit-row:
  identity + status/substatus/last_updated + researcher notes + other/local names (context)
  cells_to_reverify: [{field_name, old_value, ref_field, ref_current}]  <- the exhaustive contract.
    The agent fills new_value (=old_value if confirmed unchanged), confidence, ref_urls (ALL verified
    URLs that contain the value), source_notes. ref_field is the CORRECT paired [ref] header
    (handles the irregular pairings: ConstructionYear->'ConstructionDate [ref]', etc.); null = no
    dedicated [ref] column (record colors the data cell; cite in source_notes).
  blank_refs_with_data: refs that are blank but whose paired data value is populated (fill targets).
"""
import csv, json, sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
STALE = ROOT / "scripts" / "work" / "stale_sweep.json"
CSV = ROOT / "scripts" / "gem_export.csv"
REGION_MAP = ROOT / "batches" / "staging" / "_region_map.json"

# Read-only / out-of-scope columns: never staged, never re-verified. Mirrors
# build_review_package.READ_ONLY_COLUMNS + CLAUDE.md out-of-scope list (+ CCS, per the
# country brief's never-write rule) + identity/admin/free-text/computed columns.
SKIP_FIELDS = {
    "TerminalID", "UnitID", "Wiki", "TerminalName", "UnitName", "Country/Area",
    "Researcher", "LastUpdated", "Region", "SubRegion", "Language",
    "OtherNames", "LocalNames", "ResearcherNotesUnit", "ResearcherNotesProject",
    "Parent GEM Entity ID",
    # computed / totals (read-only)
    "CapacityinMtpa", "CapacityinBcm/y",
    "TotImportLNGTerminalCapacityinMtpa", "TotImportLNGTerminalCapacityinBcm/y",
    "TotExportLNGTerminalCapacityinMtpa", "TotExportLNGTerminalCapacityinBcm/y",
    "CostUSD", "CostEuro", "TotKnownTerminalCostsUSD", "TotTerminalCost [ref]",
    # out-of-scope per methodology (no longer updated as of 2026)
    "PCINotes", "PCI3", "PCI4", "PCI5", "PCI6", "LH2", "NH3", "SyntheticLNG",
    "RetrofitProposed", "AltFuelPrelimAgreement", "AltFuelCallMarketInterest",
    "CCS", "CCSNotes",
    # GEM-internal ESG/advocacy (not externally re-verifiable as data values)
    "Opposition", "ESJNotes", "Defeated", "Fuel",
}

# data field -> its paired [ref] header (None = no dedicated ref column)
FIELD_TO_REF = {
    "FacilityType": "FacilityType [ref]",
    "Status": "Status [ref]", "Substatus": "Status [ref]",
    "Owner": "Owner [ref]",
    "Parent": None, "ParentHQCountry": None,
    "Operator": "Operator [ref]",
    "Capacity": "Capacity [ref]", "CapacityUnits": "Capacity [ref]",
    "ProposalYear": "ProposalDate [ref]", "ProposalMonth": "ProposalDate [ref]",
    "ConstructionYear": "ConstructionDate [ref]", "ConstructionMonth": "ConstructionDate [ref]",
    "OriginalPlannedStartYear": "StartDate [ref]", "LatestPlannedStartYear": "StartDate [ref]",
    "ActualStartYear": "StartDate [ref]", "ActualStartMonth": "StartDate [ref]",
    "ActualStartYear2": "StartDate [ref]", "ActualStartYear3": "StartDate [ref]",
    "ShelvedYear": "ShelvedYear [ref]",
    "CancelledYear": "CancelledYear [ref]",
    "StopYear": "StopYear [ref]", "PlannedStopYear": "StopYear [ref]",
    "ShelvedCancelledStatusType": None,
    "TempFacility": None, "ImportExportOnly": None,
    "Location": "Location [ref]", "State/Province": "Location [ref]",
    "Prefecture/District": "Location [ref]", "Latitude": "Location [ref]",
    "Longitude": "Location [ref]", "Accuracy": "Location [ref]",
    "AssociatedTerminals": "AssociatedTerminals [ref]",
    "Source": "Source [ref]",
    "PowerPlantsSupplied": "PowerPlantsSupplied [ref]",
    "CaptiveGasPower": "CaptiveGasPower [ref]",
    "Pipelines": "Pipelines [ref]",
    "Cost": "Cost [ref]", "CostUnits": "Cost [ref]", "CostYear": "Cost [ref]",
    "FIDStatus": "FIDYear [ref]", "FIDYear": "FIDYear [ref]",
    "Financing": "Financing [ref]",
    "Offshore": None, "Floating": None,
    "FloatingVesselName": "FloatingVesselName [ref]",
    "VesselOwner": "VesselOwner [ref]", "VesselParent": "VesselOwner [ref]",
    "VesselOperator": "VesselOperator [ref]",
}


def load_csv_rows():
    with open(CSV, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = {}
        ui = header.index("UnitID")
        for r in reader:
            if len(r) <= ui:
                continue
            rows[r[ui]] = r
    return header, rows


def main():
    region_arg = sys.argv[1] if len(sys.argv) > 1 else None
    ss = json.loads(STALE.read_text())
    units = ss["dev_pipeline"]["units"]
    rmap = json.loads(REGION_MAP.read_text())["map"]
    header, rows = load_csv_rows()
    col = {h: i for i, h in enumerate(header)}
    ref_cols = [h for h in header if h.endswith("[ref]") and h != "TotTerminalCost [ref]"]

    def region_slug(country):
        e = rmap.get(country, {})
        return e.get("region", "UNMAPPED"), e.get("slug", country.lower().replace(" ", "-"))

    # ---- WORKLIST.json: full 473-unit frozen scope, by region/country ----
    by_region = {}
    for u in units:
        c = u["country"]
        reg, slug = region_slug(c)
        rd = by_region.setdefault(reg, {"count": 0, "countries": {}})
        cd = rd["countries"].setdefault(c, {"slug": slug, "count": 0, "units": []})
        cd["units"].append({k: u.get(k) for k in
                            ("terminal_id", "unit_id", "terminal_name", "unit_name",
                             "status", "substatus", "last_updated", "recently_updated")})
        cd["count"] += 1
        rd["count"] += 1
    worklist = {
        "_comment": "EXHAUSTIVE dev-pipeline (proposed/construction/shelved) scope, frozen at this batch's GEM pull.",
        "scope_statuses": ["proposed", "construction", "shelved"],
        "tier": "exhaustive",
        "csv_mtime": os.path.getmtime(CSV),
        "total_units": len(units),
        "by_status": ss["dev_pipeline"]["by_status"],
        "region_counts": {r: d["count"] for r, d in sorted(by_region.items())},
        "by_region": by_region,
    }
    (HERE / "WORKLIST.json").write_text(json.dumps(worklist, ensure_ascii=False, indent=2))
    print("WORKLIST.json:", len(units), "units;",
          {r: d["count"] for r, d in sorted(by_region.items())})

    if not region_arg:
        return
    if region_arg not in by_region:
        sys.exit(f"region {region_arg!r} not in worklist (have {list(by_region)})")

    # ---- per-country worklists for the requested region ----
    rdir = HERE / region_arg
    rdir.mkdir(parents=True, exist_ok=True)
    for country, cd in sorted(by_region[region_arg]["countries"].items()):
        slug = cd["slug"]
        out_units = []
        for un in cd["units"]:
            row = rows.get(un["unit_id"])
            if not row:
                out_units.append({**un, "_error": "unit_id not found in CSV"})
                continue
            def val(h):
                i = col.get(h)
                return (row[i].strip() if i is not None and i < len(row) else "")
            cells = []
            for field, ref_field in FIELD_TO_REF.items():
                v = val(field)
                if v == "":
                    continue  # exhaustive re-verifies POPULATED fields; blanks handled below
                cells.append({
                    "field_name": field,
                    "old_value": v,
                    "ref_field": ref_field,
                    "ref_current": val(ref_field) if ref_field else "",
                })
            # blank [ref] cells whose paired data value is populated -> fill targets
            blank_ref_fills = []
            for field, ref_field in FIELD_TO_REF.items():
                if ref_field and val(field) and not val(ref_field):
                    blank_ref_fills.append({"data_field": field, "data_value": val(field),
                                            "ref_field": ref_field})
            out_units.append({
                "terminal_id": un["terminal_id"], "unit_id": un["unit_id"],
                "terminal_name": un["terminal_name"], "unit_name": un["unit_name"],
                "country": country, "status": un["status"], "substatus": un["substatus"],
                "last_updated": un["last_updated"], "recently_updated": un["recently_updated"],
                "other_names": val("OtherNames"), "local_names": val("LocalNames"),
                "researcher_notes_unit": val("ResearcherNotesUnit"),
                "researcher_notes_project": val("ResearcherNotesProject"),
                "is_fsru": bool(val("Floating") and val("Floating").lower() in ("yes", "true", "1")),
                "cells_to_reverify": cells,
                "blank_refs_with_data": blank_ref_fills,
            })
        payload = {"region": region_arg, "country": country, "slug": slug,
                   "tier": "exhaustive", "n_units": len(out_units), "units": out_units}
        (rdir / f"{slug}.worklist.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        print(f"  {country:24s} {slug:24s} units={len(out_units)} "
              f"cells={sum(len(u.get('cells_to_reverify', [])) for u in out_units)} "
              f"blankref_fills={sum(len(u.get('blank_refs_with_data', [])) for u in out_units)}")


if __name__ == "__main__":
    main()
