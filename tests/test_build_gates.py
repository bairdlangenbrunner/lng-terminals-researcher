"""The fail-closed build gates in build_review_package.main(), end to end.

These are deliberately *negative* tests: they assert that bad input produces no
workbook. The gates were made fail-closed in 2026-09 (they had been warn-only),
and a gate with no test that it still blocks is a gate that quietly reverts to a
print statement. Each test therefore checks the exit code AND that the output
file was never created — a build that blocks but has already written the xlsx
would still hand a reviewer a workbook built off bad input.

Runs the script as a subprocess against a synthetic mini-CSV, so it exercises the
real argument parsing, gate arithmetic and exit codes without a live GEM export.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

BUILD = Path(__file__).resolve().parent.parent / "scripts" / "build_review_package.py"

HEADER = "TerminalID,UnitID,TerminalName,Country,Status,Status [ref],Owner,Owner [ref]"
ROW = "T001,U001,Foo LNG,Ghana,proposed,,Old Owner Co,"

CLEAN_UPDATE = {
    "terminal_id": "T001", "unit_id": "U001", "field_name": "Owner",
    "new_value": "New Owner Co", "confidence": "green",
    "ref_urls": ["https://example.com/filings/foo-lng"],
}


@pytest.fixture
def batch(tmp_path):
    """A minimal batch dir: synthetic export + an inputs/ dir to fill per test."""
    (tmp_path / "gem.csv").write_text(f"{HEADER}\n{ROW}\n", encoding="utf-8")
    (tmp_path / "inputs").mkdir()
    return tmp_path


def stage(batch, name, payload):
    (batch / "inputs" / name).write_text(json.dumps(payload), encoding="utf-8")


def build(batch, *extra, output="batch.xlsx"):
    out = batch / output
    proc = subprocess.run(
        [sys.executable, str(BUILD), "--mode", "update", "--output", str(out),
         "--inputs-dir", str(batch / "inputs"), "--gem-csv", str(batch / "gem.csv"),
         *extra],
        capture_output=True, text=True, cwd=batch,
    )
    return proc, out


def test_clean_inputs_build(batch):
    # The control: without this, a test asserting "blocked" proves nothing.
    stage(batch, "staged_updates.json", [CLEAN_UPDATE])
    proc, out = build(batch)
    assert proc.returncode == 0, proc.stderr
    assert out.exists()
    assert Path(str(out) + ".manifest.json").exists()


def test_unknown_key_blocks_the_build(batch):
    stage(batch, "staged_updates.json", [{**CLEAN_UPDATE, "typo_field": "x"}])
    proc, out = build(batch)
    assert proc.returncode == 2
    assert "BUILD BLOCKED" in proc.stderr
    assert not out.exists()


def test_missing_required_key_blocks_the_build(batch):
    stage(batch, "staged_updates.json", [{k: v for k, v in CLEAN_UPDATE.items()
                                          if k != "field_name"}])
    proc, out = build(batch)
    assert proc.returncode == 2
    assert not out.exists()


def test_url_aimed_at_a_data_column_blocks_the_build(batch):
    # The CLAUDE.md hard rule: a URL belongs only in a [ref] column. Status is an
    # enum; a link there would be pasted straight into the live DB.
    stage(batch, "staged_updates.json", [{**CLEAN_UPDATE, "field_name": "Status",
                                          "new_value": "https://example.com/x"}])
    proc, out = build(batch)
    assert proc.returncode == 2
    assert not out.exists()


@pytest.mark.parametrize("payload, label", [
    ({"not": "a list"}, "object instead of a list"),
    (["oops", "not objects"], "list of non-objects"),
])
def test_malformed_staging_blocks_instead_of_crashing(batch, payload, label):
    # Regression: a malformed staged file was counted as a finding but still
    # handed to the sheet builders, which call .get() on each record — the build
    # died with an AttributeError traceback (exit 1) partway through instead of
    # stopping at the gate. Fail-closed must mean a *clean* stop: exit 2, the
    # guard message, and no traceback for the operator to misread as a crash.
    stage(batch, "staged_updates.json", payload)
    proc, out = build(batch)
    assert proc.returncode == 2, f"{label}: {proc.stderr}"
    assert "BUILD BLOCKED" in proc.stderr
    assert "Traceback" not in proc.stderr
    assert not out.exists()


def test_malformed_fsru_sync_report_blocks(batch):
    # fsru_sync.json is an object, not a list — and main() calls fsru.get() on it
    # in several places, so a list here was the same crash-not-gate shape.
    stage(batch, "staged_updates.json", [CLEAN_UPDATE])
    stage(batch, "fsru_sync.json", ["not", "an object"])
    proc, out = build(batch)
    assert proc.returncode == 2
    assert "Traceback" not in proc.stderr
    assert not out.exists()


def test_allow_warnings_is_the_documented_escape_hatch(batch):
    stage(batch, "staged_updates.json", [{**CLEAN_UPDATE, "typo_field": "x"}])
    proc, out = build(batch, "--allow-warnings")
    assert proc.returncode == 0, proc.stderr
    assert "WARNING OVERRIDE" in proc.stderr
    assert out.exists()


def test_existing_output_is_never_overwritten(batch):
    # "Never overwrite an existing batch file" — every rebuild gets a new stamp.
    stage(batch, "staged_updates.json", [CLEAN_UPDATE])
    proc, out = build(batch)
    assert proc.returncode == 0
    before = out.read_bytes()

    proc, _ = build(batch)
    assert proc.returncode == 2
    assert "output already exists" in proc.stderr
    assert out.read_bytes() == before


def test_orphaned_manifest_also_blocks(batch):
    # Deleting just the xlsx must not make the stamp look free again — the
    # manifest is the record that a build already claimed it.
    stage(batch, "staged_updates.json", [CLEAN_UPDATE])
    proc, out = build(batch)
    assert proc.returncode == 0
    out.unlink()

    proc, _ = build(batch)
    assert proc.returncode == 2
    assert "manifest already exists" in proc.stderr
    assert not out.exists()


def test_force_replaces_deliberately(batch):
    stage(batch, "staged_updates.json", [CLEAN_UPDATE])
    assert build(batch)[0].returncode == 0
    proc, out = build(batch, "--force")
    assert proc.returncode == 0, proc.stderr
    assert out.exists()


def test_missing_inputs_dir_is_an_error_not_an_empty_build(batch):
    # An empty workbook built off a mistyped --inputs-dir is the silent failure
    # this guard exists to prevent.
    out = batch / "batch.xlsx"
    proc = subprocess.run(
        [sys.executable, str(BUILD), "--mode", "update", "--output", str(out),
         "--inputs-dir", str(batch / "does-not-exist"),
         "--gem-csv", str(batch / "gem.csv")],
        capture_output=True, text=True, cwd=batch,
    )
    assert proc.returncode == 2
    assert "inputs directory not found" in proc.stderr
    assert not out.exists()
