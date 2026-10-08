"""fsru_sync_check — the GEM↔carrier FSRU cross-check.

Both bugs pinned here failed the same way: silently. The check reported a
clean run having compared nothing (carrier side read as zero records, because
the live backend's name column is `Name` under a preamble row), over a fleet
that was a quarter FLNG export units (GEM side never filtered facility_type).
Pure logic, no network.
"""
import csv
import json

import pytest
from fsru_sync_check import (
    CARRIER_HEADER_SCAN_ROWS,
    cross_check,
    gather_gem_fsrus,
    load_carrier_vessels,
)

GEM_HEADER = [
    "TerminalID", "UnitID", "TerminalName", "UnitName", "Country", "Status",
    "FacilityType", "Fuel", "Floating", "FloatingVesselName", "VesselOwner",
    "VesselParent", "VesselOperator", "ImportExportOnly", "TempFacility",
]
GEM_COLMAP = {k: i for i, k in enumerate([
    "terminal_id", "unit_id", "terminal_name", "unit_name", "country", "status",
    "facility_type", "fuel", "floating", "floating_vessel_name", "vessel_owner",
    "vessel_parent", "vessel_operator", "import_export_only", "temp_facility",
])}
GEM_COLMAP["_total_columns"] = len(GEM_HEADER)
GEM_COLMAP["_header_columns"] = GEM_HEADER


def _gem_row(**vals):
    row = [""] * len(GEM_HEADER)
    row[GEM_COLMAP["fuel"]] = "LNG"
    row[GEM_COLMAP["floating"]] = "true"
    for k, v in vals.items():
        row[GEM_COLMAP[k]] = v
    return row


def _gem_csv(tmp_path, rows):
    path = tmp_path / "gem_export.csv"
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(GEM_HEADER)
        w.writerows(rows)
    (tmp_path / "gem_export.colmap.json").write_text(json.dumps(GEM_COLMAP))
    return str(path)


IMPORT_UNIT = _gem_row(terminal_id="T1", unit_id="U1", terminal_name="Jaigarh LNG Terminal",
                       facility_type="import", floating_vessel_name="Hoegh Giant",
                       vessel_owner="Hoegh LNG", status="operating")
EXPORT_UNIT = _gem_row(terminal_id="T2", unit_id="U2", terminal_name="Bahía Blanca FLNG Terminal",
                       facility_type="export", floating_vessel_name="Exmar Tango")
BLANK_TYPE_UNIT = _gem_row(terminal_id="T3", unit_id="U3", terminal_name="Browse FLNG Terminal",
                           facility_type="", floating_vessel_name="")


def test_flng_export_units_are_not_fsrus(tmp_path):
    """Floating=True alone swept FLNG export units into the FSRU fleet."""
    excluded = []
    fsrus = gather_gem_fsrus(_gem_csv(tmp_path, [IMPORT_UNIT, EXPORT_UNIT, BLANK_TYPE_UNIT]),
                             excluded=excluded)
    assert [u["terminal_id"] for u in fsrus] == ["T1"]
    assert [u["terminal_id"] for u in excluded] == ["T2", "T3"]


def test_facility_type_filter_can_be_turned_off(tmp_path):
    fsrus = gather_gem_fsrus(_gem_csv(tmp_path, [IMPORT_UNIT, EXPORT_UNIT]), facility_types=None)
    assert len(fsrus) == 2


def test_non_lng_and_non_floating_units_are_still_skipped(tmp_path):
    rows = [_gem_row(terminal_id="T4", facility_type="import", fuel="H2"),
            _gem_row(terminal_id="T5", facility_type="import", floating="")]
    assert gather_gem_fsrus(_gem_csv(tmp_path, rows)) == []


CARRIER_HEADER = ["original order in sheet", "IMO number", "Name", "Status",
                  "Shipowner", "Vessel type", "Operator/charterer"]


def _carrier_csv(tmp_path, rows, header=CARRIER_HEADER, preamble=True, name="backend.csv"):
    """The carrier backend's real shape: a spreadsheet-column preamble row,
    then the header, then data."""
    path = tmp_path / name
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        if preamble:
            w.writerow([str(i + 1) for i in range(len(header))])
        w.writerow(header)
        w.writerows(rows)
    return str(path)


def test_the_live_backend_shape_reads_its_vessels(tmp_path):
    """`Name`, under a preamble row — what a plain DictReader reads as zero."""
    path = _carrier_csv(tmp_path, [
        ["547", "9655016", "Hoegh Giant", "active", "Hoegh LNG", "FSRU", ""],
        ["548", "9420452", "Energos Freeze", "active", "Energos", "FSRU", ""],
    ])
    records = load_carrier_vessels(path)
    assert set(records) == {"hoegh giant", "energos freeze"}
    assert records["hoegh giant"]["IMO number"] == "9655016"


def test_the_older_vesselname_header_still_reads(tmp_path):
    path = _carrier_csv(tmp_path, [["Hoegh Giant", "Hoegh LNG"]],
                        header=["VesselName", "Owner"], preamble=False)
    assert list(load_carrier_vessels(path)) == ["hoegh giant"]


def test_an_unrecognized_carrier_export_raises_instead_of_reading_nothing(tmp_path):
    path = _carrier_csv(tmp_path, [["x", "y"]], header=["Ship", "Operator"], preamble=False)
    with pytest.raises(ValueError, match="no vessel-name column"):
        load_carrier_vessels(path)


def test_a_header_below_the_scan_window_raises(tmp_path):
    rows = [[str(i)] * len(CARRIER_HEADER) for i in range(CARRIER_HEADER_SCAN_ROWS + 2)]
    path = _carrier_csv(tmp_path, rows + [CARRIER_HEADER], header=["a"] * 7, preamble=False)
    with pytest.raises(ValueError):
        load_carrier_vessels(path)


def test_short_rows_and_nameless_rows_are_tolerated(tmp_path):
    path = _carrier_csv(tmp_path, [["1", "9655016"], ["2", "", "", "active"]])
    assert load_carrier_vessels(path) == {}


def test_owner_disagreement_is_read_off_the_live_column_names(tmp_path):
    """The owner comparison read `Owner`/`VesselOwner`; the backend says
    `Shipowner`, so every pair matched clean whatever the values were."""
    fsrus = gather_gem_fsrus(_gem_csv(tmp_path, [IMPORT_UNIT]))
    carrier = load_carrier_vessels(_carrier_csv(tmp_path, [
        ["547", "9655016", "Hoegh Giant", "active", "Excelerate Energy", "FSRU", ""]]))
    result = cross_check(fsrus, carrier)
    pair, = result["matched_pairs"]
    assert pair["carrier_imo"] == "9655016"
    assert [d["field"] for d in pair["disagreements"]] == ["owner"]
    assert pair["in_sync"] is False


def test_matching_owners_are_in_sync(tmp_path):
    fsrus = gather_gem_fsrus(_gem_csv(tmp_path, [IMPORT_UNIT]))
    carrier = load_carrier_vessels(_carrier_csv(tmp_path, [
        ["547", "9655016", "Hoegh Giant", "active", "Hoegh LNG", "FSRU", ""]]))
    pair, = cross_check(fsrus, carrier)["matched_pairs"]
    assert pair["in_sync"] is True


def test_a_carrier_fsru_with_no_gem_unit_is_reported(tmp_path):
    fsrus = gather_gem_fsrus(_gem_csv(tmp_path, [IMPORT_UNIT]))
    carrier = load_carrier_vessels(_carrier_csv(tmp_path, [
        ["547", "9655016", "Hoegh Giant", "active", "Hoegh LNG", "FSRU", ""],
        ["901", "9922022", "Energos Power", "active", "Energos", "FSRU", ""],
        ["902", "9111111", "LNG Aquarius", "active", "Hanochem", "conventional", ""]]))
    result = cross_check(fsrus, carrier)
    assert [v["vessel_name"] for v in result["carrier_only_fsrus"]] == ["Energos Power"]
    assert result["stats"]["carrier_record_count"] == 3
