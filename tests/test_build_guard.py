"""The URL-routing guard in build_review_package.build_update_csv_shaped_sheet:
a URL aimed at a data/enum column is REFUSED (never corrupts e.g. Status), URLs
route only to [ref] columns, ref_field misroutes are skipped, and read-only
columns are never written — the CLAUDE.md hard rules, enforced at build time.

Uses a synthetic mini-CSV so the test needs no live GEM export.
"""
import openpyxl
import pytest

import build_review_package as brp

HEADER = ["TerminalID", "UnitID", "TerminalName", "Status", "Status [ref]",
          "Owner", "Owner [ref]", "LH2"]
ROW = ["T001", "U001", "Foo LNG Terminal", "proposed", "", "Old Owner Co", "", ""]


@pytest.fixture
def gem_csv(tmp_path):
    p = tmp_path / "gem_export.csv"
    p.write_text(",".join(HEADER) + "\n" + ",".join(ROW) + "\n", encoding="utf-8")
    return str(p)


def _build(gem_csv, updates):
    wb = openpyxl.Workbook()
    brp.build_update_csv_shaped_sheet(wb, updates, gem_csv)
    ws = wb["updates_in_database_format"]
    # data row 2 as a {column_name: value} map
    return ws, {h: ws.cell(row=2, column=i + 1).value for i, h in enumerate(HEADER)}


def _rec(**kw):
    base = {"terminal_id": "T001", "unit_id": "U001", "confidence": "green",
            "ref_urls": []}
    base.update(kw)
    return base


def test_url_aimed_at_enum_column_is_refused(gem_csv):
    _, row = _build(gem_csv, [
        _rec(field_name="Status", new_value="https://example.com/announcement")])
    assert row["Status"] == "proposed"          # DB value untouched
    assert len(brp._BAD_VALUE_WRITES) == 1
    assert brp._BAD_VALUE_WRITES[0][2] == "Status"


def test_value_and_ref_urls_route_correctly(gem_csv):
    _, row = _build(gem_csv, [
        _rec(field_name="Owner", new_value="New Owner Ltd",
             ref_urls=["https://example.com/a", "https://example.org/b"])])
    assert row["Owner"] == "New Owner Ltd"
    assert row["Owner [ref]"] == "https://example.com/a, https://example.org/b"
    assert brp._BAD_VALUE_WRITES == []
    assert brp._BAD_REF_TARGETS == []


def test_ref_field_naming_a_base_column_is_skipped(gem_csv):
    # A blank-ref fill (field_name="Status [ref]") whose ref_field mistakenly
    # names the base column: the URL lands in Status [ref] (the field itself)
    # but is NEVER routed into Status.
    _, row = _build(gem_csv, [
        _rec(field_name="Status [ref]", new_value="https://example.com/s",
             ref_urls=["https://example.com/s"], ref_field="Status")])
    assert row["Status"] == "proposed"
    assert row["Status [ref]"] == "https://example.com/s"
    assert len(brp._BAD_REF_TARGETS) == 1
    assert brp._BAD_REF_TARGETS[0][3] == "Status"


def test_read_only_column_never_written(gem_csv):
    _, row = _build(gem_csv, [_rec(field_name="LH2", new_value="yes")])
    assert row["LH2"] == ""  # openpyxl reads empty as None
    # LH2 must be in the enforced read-only set for the skip to be deliberate
    assert "LH2" in brp.READ_ONLY_COLUMNS


def test_guard_lists_reset_between_builds(gem_csv):
    _build(gem_csv, [_rec(field_name="Status", new_value="https://example.com/x")])
    assert brp._BAD_VALUE_WRITES
    _build(gem_csv, [])
    assert brp._BAD_VALUE_WRITES == []


def test_giignl_mirror_urls_flagged_as_one_source():
    # Two host-variants of the SAME GIIGNL edition = one source (CLAUDE.md
    # corroboration rule); the build warns instead of letting it pass as ≥2.
    hits = brp.warn_duplicate_giignl_refs([
        _rec(field_name="Capacity", new_value="5.2", ref_urls=[
            "https://elfsightcdn.com/GIIGNL-Livre-2025.pdf",
            "https://website-files.com/GIIGNL%20Livre%202025.pdf"])])
    assert len(hits) == 1
    # ...but two DIFFERENT editions are independent — no warning
    assert brp.warn_duplicate_giignl_refs([
        _rec(field_name="Capacity", new_value="5.2", ref_urls=[
            "https://giignl.org/annual-report-2025.pdf",
            "https://giignl.org/annual-report-2026.pdf"])]) == []
