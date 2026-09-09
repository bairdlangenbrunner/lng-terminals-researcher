"""staging_qc.py is the merge-time gate — it must EXIT NONZERO on findings.

It went fail-closed in 2026-09 after the 2026-08-11 miss, where the gate echoed
`_validate_records`' warnings, counted none of them, and printed GATE CLEAN over
a shard whose 13 qa records would all have rendered blank. The bug was not the
detection; it was the exit code. So these tests assert the *return value*, which
is the only part a caller (`&&`, CI, a sweep script) can act on.
"""
import json

import pytest

import staging_qc


@pytest.fixture
def region(tmp_path, monkeypatch):
    """A staging region under a fake REPO, so nothing touches the real tree."""
    monkeypatch.setattr(staging_qc, "REPO", tmp_path)
    base = tmp_path / "batches" / "staging" / "testregion"
    base.mkdir(parents=True)
    (tmp_path / "gem_export.csv").write_text(
        "TerminalID,UnitID,TerminalName,Status,Status [ref],Owner,Owner [ref]\n"
        "T001,U001,Foo LNG,proposed,,Old Owner Co,\n", encoding="utf-8")
    return base


def shard(region, name, records):
    (region / name).write_text(json.dumps(records), encoding="utf-8")


def run(*extra):
    return staging_qc.main(["testregion", "--csv", "gem_export.csv", "--no-pg", *extra])


CLEAN = {"terminal_id": "T001", "unit_id": "U001", "field_name": "Owner",
         "new_value": "New Owner Co", "confidence": "green",
         "ref_urls": ["https://example.com/filings/foo-lng"]}


def test_clean_region_passes(region):
    shard(region, "ghana.updates.json", [CLEAN])
    assert run() == 0


def test_key_schema_drift_exits_nonzero(region):
    # The 2026-08-11 shape exactly: plausible-looking keys no sheet builder reads.
    shard(region, "argentina.qa.json",
          [{"description": "check this", "field_name": "Owner"}])
    assert run() == 1


def test_banned_source_exits_nonzero(region):
    shard(region, "ghana.updates.json",
          [{**CLEAN, "ref_urls": ["https://abarrelfull.wikidot.com/foo"]}])
    assert run() == 1


def test_bare_domain_citation_exits_nonzero(region):
    # A homepage is never a citation in any lane.
    shard(region, "ghana.updates.json", [{**CLEAN, "ref_urls": ["https://example.com"]}])
    assert run() == 1


def test_unreadable_shard_exits_nonzero(region):
    (region / "ghana.updates.json").write_text("{ this is not json", encoding="utf-8")
    assert run() == 1


def test_allow_warnings_downgrades_to_exit_zero(region):
    shard(region, "argentina.qa.json", [{"description": "check this"}])
    assert run() == 1
    assert run("--allow-warnings") == 0
