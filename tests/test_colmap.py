"""colmap.load_colmap — the shared colmap.json loader consolidated out of 7
copy-pasted `_load_colmap` implementations (citation_qc, completeness_sweep,
entity_lookup, dedup_index, fsru_sync_check, stale_sweep, report_diff)."""
import json

import pytest

from colmap import load_colmap


def test_load_colmap_happy_path(tmp_path):
    csv_path = tmp_path / "gem_export.csv"
    csv_path.write_text("TerminalID,TerminalName\nT1,Foo\n", encoding="utf-8")
    map_path = tmp_path / "gem_export.colmap.json"
    map_path.write_text(json.dumps({
        "terminal_id": 0, "terminal_name": 1,
        "_header_columns": ["TerminalID", "TerminalName"],
    }), encoding="utf-8")

    colmap = load_colmap(str(csv_path))
    assert colmap["terminal_id"] == 0
    assert colmap["_header_columns"] == ["TerminalID", "TerminalName"]


def test_load_colmap_missing_raises_runtime_error(tmp_path):
    csv_path = tmp_path / "gem_export.csv"
    csv_path.write_text("TerminalID\nT1\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="pull_gem_db.py"):
        load_colmap(str(csv_path))


def test_load_colmap_rederives_header_columns_from_bom_csv(tmp_path):
    # pull_gem_db.py strips _header_columns before serializing to disk — the
    # loader must re-derive it from the CSV's own header row, BOM-safe.
    csv_path = tmp_path / "gem_export.csv"
    csv_path.write_bytes("TerminalID,TerminalName\nT1,Foo\n".encode("utf-8-sig"))
    map_path = tmp_path / "gem_export.colmap.json"
    map_path.write_text(json.dumps({"terminal_id": 0, "terminal_name": 1}), encoding="utf-8")

    colmap = load_colmap(str(csv_path))
    assert colmap["_header_columns"] == ["TerminalID", "TerminalName"]
    assert not colmap["_header_columns"][0].startswith("﻿")
