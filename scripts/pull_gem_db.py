"""
Derive the column-index map for a GEM all-fields export CSV from its header row.

This script never fetches anything. Pull the CSV first via the sibling
gem-db-ops repo's engine (`python ../../gem-db-ops/gem_query.py --all-fields
lng -o gem_export.csv`, from scripts/), then run `python pull_gem_db.py
--map-only` to derive the .colmap.json. Running without `--map-only` exits
with a pointer to that command — the old cookie-based fetch path was
decommissioned 2026-07-21 and this repo keeps no pull-engine copies.

Why re-derive the column map every batch:
  - GEM's all-fields export is 115 columns (Q2 2026) but the schema can
    drift between releases (columns added, renamed, reordered)
  - Hard-coding column offsets means batch breakage on any schema change
  - The derived map is saved next to the CSV so other scripts use the same one

Usage:
    python pull_gem_db.py --map-only                 # derive map from ./gem_export.csv
    python pull_gem_db.py --map-only --output x.csv  # custom CSV path
"""
import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from schema_constants import COMPUTED_COLUMNS, OUT_OF_SCOPE_COLUMNS


DEFAULT_OUT = "./gem_export.csv"

# Columns we depend on — keyed by canonical short name, value is the expected
# header text (case-insensitive). The actual column index is derived from the
# header row at runtime.
EXPECTED_COLUMNS = {
    "terminal_id": "TerminalID",
    "unit_id": "UnitID",
    "wiki": "Wiki",
    "terminal_name": "TerminalName",
    "unit_name": "UnitName",
    "facility_type": "FacilityType",
    "facility_type_ref": "FacilityType [ref]",
    "fuel": "Fuel",
    "status": "Status",
    "substatus": "Substatus",
    "status_ref": "Status [ref]",
    "country": "Country/Area",
    "researcher": "Researcher",
    "last_updated": "LastUpdated",
    "researcher_notes_unit": "ResearcherNotesUnit",
    "researcher_notes_project": "ResearcherNotesProject",
    "other_names": "OtherNames",
    "local_names": "LocalNames",
    "language": "Language",
    "owner": "Owner",
    "owner_ref": "Owner [ref]",
    "parent": "Parent",
    "parent_hq_country": "ParentHQCountry",
    "parent_entity_id": "Parent GEM Entity ID",
    "operator": "Operator",
    "operator_ref": "Operator [ref]",
    "capacity": "Capacity",
    "capacity_units": "CapacityUnits",
    "capacity_mtpa": "CapacityinMtpa",
    "capacity_bcm": "CapacityinBcm/y",
    "capacity_ref": "Capacity [ref]",
    "tot_import_mtpa": "TotImportLNGTerminalCapacityinMtpa",
    "tot_import_bcm": "TotImportLNGTerminalCapacityinBcm/y",
    "tot_export_mtpa": "TotExportLNGTerminalCapacityinMtpa",
    "tot_export_bcm": "TotExportLNGTerminalCapacityinBcm/y",
    "proposal_year": "ProposalYear",
    "proposal_month": "ProposalMonth",
    "proposal_date_ref": "ProposalDate [ref]",
    "construction_year": "ConstructionYear",
    "construction_month": "ConstructionMonth",
    "construction_date_ref": "ConstructionDate [ref]",
    "original_planned_start": "OriginalPlannedStartYear",
    "latest_planned_start": "LatestPlannedStartYear",
    "actual_start_year": "ActualStartYear",
    "actual_start_month": "ActualStartMonth",
    "actual_start_year_2": "ActualStartYear2",
    "actual_start_year_3": "ActualStartYear3",
    "start_date_ref": "StartDate [ref]",
    "shelved_year": "ShelvedYear",
    "shelved_year_ref": "ShelvedYear [ref]",
    "cancelled_year": "CancelledYear",
    "cancelled_year_ref": "CancelledYear [ref]",
    "stop_year": "StopYear",
    "stop_year_ref": "StopYear [ref]",
    "planned_stop_year": "PlannedStopYear",
    "shelved_cancelled_status_type": "ShelvedCancelledStatusType",
    "temp_facility": "TempFacility",
    "import_export_only": "ImportExportOnly",
    "location": "Location",
    "region": "Region",
    "sub_region": "SubRegion",
    "prefecture_district": "Prefecture/District",
    "state_province": "State/Province",
    "latitude": "Latitude",
    "longitude": "Longitude",
    "accuracy": "Accuracy",
    "location_ref": "Location [ref]",
    "associated_terminals": "AssociatedTerminals",
    "associated_terminals_ref": "AssociatedTerminals [ref]",
    "source": "Source",
    "source_ref": "Source [ref]",
    "power_plants_supplied": "PowerPlantsSupplied",
    "power_plants_supplied_ref": "PowerPlantsSupplied [ref]",
    "captive_gas_power": "CaptiveGasPower",
    "captive_gas_power_ref": "CaptiveGasPower [ref]",
    "pipelines": "Pipelines",
    "pipelines_ref": "Pipelines [ref]",
    "cost": "Cost",
    "cost_units": "CostUnits",
    "cost_year": "CostYear",
    "cost_usd": "CostUSD",
    "cost_euro": "CostEuro",
    "cost_ref": "Cost [ref]",
    "tot_known_terminal_costs_usd": "TotKnownTerminalCostsUSD",
    "tot_terminal_cost_ref": "TotTerminalCost [ref]",
    "fid_status": "FIDStatus",
    "fid_year": "FIDYear",
    "fid_year_ref": "FIDYear [ref]",
    "financing": "Financing",
    "financing_ref": "Financing [ref]",
    "offshore": "Offshore",
    "floating": "Floating",
    "floating_vessel_name": "FloatingVesselName",
    "floating_vessel_name_ref": "FloatingVesselName [ref]",
    "vessel_owner": "VesselOwner",
    "vessel_owner_ref": "VesselOwner [ref]",
    "vessel_parent": "VesselParent",
    "vessel_operator": "VesselOperator",
    "vessel_operator_ref": "VesselOperator [ref]",
    "opposition": "Opposition",
    "esj_notes": "ESJNotes",
    "defeated": "Defeated",
    "pci_notes": "PCINotes",
    "pci3": "PCI3",
    "pci4": "PCI4",
    "pci5": "PCI5",
    "pci6": "PCI6",
    "lh2": "LH2",
    "nh3": "NH3",
    "synthetic_lng": "SyntheticLNG",
    "retrofit_proposed": "RetrofitProposed",
    "alt_fuel_prelim_agreement": "AltFuelPrelimAgreement",
    "alt_fuel_call_market_interest": "AltFuelCallMarketInterest",
    "ccs": "CCS",
    "ccs_notes": "CCSNotes",
}

# Read-only columns (build_review_package.py must NEVER write these). Derived
# from the canonical header-string sets in schema_constants.py, translated into
# this script's short/canonical column-name keys via EXPECTED_COLUMNS (this
# module keys everything by the short name, not the raw CSV header string).
READ_ONLY_COMPUTED = {k for k, v in EXPECTED_COLUMNS.items() if v in COMPUTED_COLUMNS}

READ_ONLY_OUT_OF_SCOPE = {k for k, v in EXPECTED_COLUMNS.items() if v in OUT_OF_SCOPE_COLUMNS}


def derive_column_map(csv_path):
    """Read header row, return {canonical_name: 0-indexed-column} dict.
    Unknown columns get None; missing expected columns also get None
    (so the caller can detect schema drift).
    """
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            sys.exit(f"ERROR: empty CSV at {csv_path}")

    # The first column has a BOM in the empirical export — strip it
    if header and header[0].startswith("\ufeff"):
        header[0] = header[0][1:]

    col_map = {"_header_columns": header, "_total_columns": len(header)}

    # For each expected column, find its index in the header
    for canonical, needle in EXPECTED_COLUMNS.items():
        idx = None
        for i, h in enumerate(header):
            if h.strip() == needle:
                idx = i
                break
        col_map[canonical] = idx

    # Also flag any header columns we don't have a canonical name for
    canonical_headers = set(EXPECTED_COLUMNS.values())
    unknown = [h for h in header if h.strip() not in canonical_headers]
    col_map["_unknown_columns"] = unknown

    return col_map


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", "--out", dest="out", default=DEFAULT_OUT)
    p.add_argument("--map-only", action="store_true",
                   help="Derive the map from an existing CSV (the only mode)")
    args = p.parse_args()

    if not args.map_only:
        sys.exit(
            "ERROR: this script never fetches the export — pull via the sibling\n"
            "  gem-db-ops repo's engine, then derive the map (from scripts/):\n\n"
            "    python ../../gem-db-ops/gem_query.py --all-fields lng -o gem_export.csv\n"
            "    python pull_gem_db.py --map-only\n"
        )

    col_map = derive_column_map(args.out)

    print(f"\nColumn-index map ({col_map['_total_columns']} total columns):")
    missing = []
    for k, v in col_map.items():
        if k.startswith("_"):
            continue
        status = "OK" if v is not None else "MISSING"
        if v is None:
            missing.append(k)
            print(f"  {k:35} = {'--':<5} [{status}]")
        else:
            print(f"  {k:35} = {v:<5}")

    if missing:
        print(f"\n  WARNING: {len(missing)} expected columns not found:")
        for k in missing:
            print(f"    {k}  (expected header text: {EXPECTED_COLUMNS[k]!r})")
        print(f"\n  Schema may have changed — check the live DB and update EXPECTED_COLUMNS.")

    if col_map["_unknown_columns"]:
        print(f"\n  NOTE: {len(col_map['_unknown_columns'])} unknown columns in header:")
        for h in col_map["_unknown_columns"]:
            print(f"    {h!r}")

    # Save the map next to the CSV
    map_path = Path(args.out).with_suffix(".colmap.json")
    # Serialize without the header columns list (large) for clean reading
    serializable = {k: v for k, v in col_map.items() if k != "_header_columns"}
    serializable["_header_columns_count"] = col_map["_total_columns"]
    map_path.write_text(json.dumps(serializable, indent=2))
    print(f"\n  Column map saved to {map_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
