"""
Pull the latest GEM database export and derive the column-index map from the
header row.

Wraps the user-supplied gem_export_via_web.py script. Requires the env vars:
  - GEM_PROJECT_DB_SESSIONID
  - GEM_PROJECT_DB_CSRFTOKEN
(set from the user's browser session; expires periodically — re-export when
auth fails)

Why re-derive the column map every batch:
  - GEM's all-fields export is 115 columns (Q2 2026) but the schema can
    drift between releases (columns added, renamed, reordered)
  - Hard-coding column offsets means batch breakage on any schema change
  - The derived map is saved next to the CSV so other scripts use the same one

Usage:
    python pull_gem_db.py                            # default: lng export
    python pull_gem_db.py --out /tmp/gem.csv         # custom path
    python pull_gem_db.py --map-only                 # skip fetch, derive map only
    python pull_gem_db.py --kind lng_export          # the shorter "LNG Export" format
"""
import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path


DEFAULT_OUT = "./gem_export.csv"
WRAPPER_SCRIPT = "gem_export_via_web.py"  # user-supplied; must be in same dir or PYTHONPATH

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

# Read-only columns (build_review_package.py must NEVER write these)
READ_ONLY_COMPUTED = {
    "capacity_mtpa", "capacity_bcm",
    "tot_import_mtpa", "tot_import_bcm",
    "tot_export_mtpa", "tot_export_bcm",
    "cost_usd", "cost_euro",
    "tot_known_terminal_costs_usd", "tot_terminal_cost_ref",
    "terminal_id", "unit_id", "wiki",
}

READ_ONLY_OUT_OF_SCOPE = {
    "pci_notes", "pci3", "pci4", "pci5", "pci6",
    "lh2", "nh3", "synthetic_lng", "retrofit_proposed",
    "alt_fuel_prelim_agreement", "alt_fuel_call_market_interest",
}


def _check_env():
    """Verify auth env vars are set before invoking the wrapper."""
    missing = []
    for var in ("GEM_PROJECT_DB_SESSIONID", "GEM_PROJECT_DB_CSRFTOKEN"):
        if not os.environ.get(var):
            missing.append(var)
    if missing:
        sys.exit(
            f"ERROR: missing env var(s): {', '.join(missing)}\n\n"
            f"  See {WRAPPER_SCRIPT} for the cookie extraction procedure.\n"
            f"  Briefly: log into the GEM project DB in your browser, copy the\n"
            f"  sessionid and csrftoken cookies, export as env vars."
        )


def fetch_gem_export(out_path, kind="lng"):
    """Invoke the user's gem_export_via_web.py wrapper to download the CSV."""
    _check_env()
    # The wrapper expects to be invoked as `python gem_export_via_web.py <kind> -o <path>`
    # We use sys.executable to be explicit about the python interpreter
    script_dir = Path(__file__).parent
    wrapper = script_dir / WRAPPER_SCRIPT
    if not wrapper.exists():
        sys.exit(
            f"ERROR: {WRAPPER_SCRIPT} not found in {script_dir}.\n"
            f"  This script wraps the user-supplied {WRAPPER_SCRIPT}.\n"
            f"  Materialize it from project files into the same directory before running."
        )
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [sys.executable, str(wrapper), kind, "-o", out_path],
        capture_output=False,  # let stderr stream through for auth diagnostics
    )
    if result.returncode != 0:
        sys.exit(f"ERROR: {WRAPPER_SCRIPT} failed with exit code {result.returncode}")
    size = Path(out_path).stat().st_size
    if size < 1000:
        sys.exit(f"ERROR: CSV suspiciously small ({size} bytes) — verify auth and try again")
    print(f"  Pulled {size:,} bytes to {out_path}", file=sys.stderr)


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
    p.add_argument("--out", default=DEFAULT_OUT)
    p.add_argument("--kind", default="lng",
                   choices=["lng", "lng_export"],
                   help="Which export format (default: lng)")
    p.add_argument("--map-only", action="store_true",
                   help="Skip the fetch; just derive the map from an existing CSV")
    args = p.parse_args()

    if not args.map_only:
        fetch_gem_export(args.out, kind=args.kind)

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
