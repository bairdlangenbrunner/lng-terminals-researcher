"""monitor_store.py — the durable cross-batch monitor_list/current.json store.

Covers the two halves of the loop (seed / update) plus the dedup/merge
semantics described in the module docstring: normalized (country,
candidate_name) key, first_observed_batch preserved, last_observed_batch
bumped, and promoted-to-new_terminals entries dropped out.

All tests monkeypatch monitor_store.STORE_PATH into tmp_path so the real
repo-committed monitor_list/current.json is never touched.
"""
import json

import pytest

import monitor_store as ms


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(ms, "STORE_PATH", tmp_path / "monitor_list" / "current.json")
    return tmp_path


def test_load_store_missing_file_returns_empty_list():
    assert ms.load_store() == []


def test_save_then_load_round_trips():
    entries = [
        {"country": "Vietnam", "candidate_name": "Cai Mep LNG", "notes": "early rumor"},
    ]
    ms.save_store(entries)
    assert ms.load_store() == entries


def test_load_store_tolerates_legacy_empty_dict(tmp_path):
    ms.STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ms.STORE_PATH.write_text("{}", encoding="utf-8")
    assert ms.load_store() == []


def test_load_store_tolerates_wrapped_dict(tmp_path):
    ms.STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ms.STORE_PATH.write_text(
        json.dumps({"monitor_list": [{"country": "X", "candidate_name": "Y"}]}),
        encoding="utf-8",
    )
    assert ms.load_store() == [{"country": "X", "candidate_name": "Y"}]


def test_entry_key_normalizes_country_and_name():
    a = {"country": "Vietnam ", "candidate_name": "Cai Mep LNG"}
    b = {"country": "vietnam", "candidate_name": "cai mep lng"}
    assert ms._entry_key(a) == ms._entry_key(b)


def test_cmd_update_dedup_on_reobservation_preserves_first_bumps_last(tmp_path):
    inputs_dir = tmp_path / "batch1"
    inputs_dir.mkdir()
    ms.save_store([{
        "country": "Vietnam", "candidate_name": "Cai Mep LNG",
        "first_observed_batch": "20260101_0000_ET",
        "last_observed_batch": "20260101_0000_ET",
        "notes": "old note",
    }])
    (inputs_dir / "staged_monitor_list.json").write_text(json.dumps([
        {"country": "vietnam", "candidate_name": "cai mep lng", "notes": "new note"},
    ]), encoding="utf-8")
    (inputs_dir / "staged_new_terminals.json").write_text("[]", encoding="utf-8")

    ms.cmd_update(str(inputs_dir), batch_label="20260601_0900_ET")

    store = ms.load_store()
    assert len(store) == 1  # deduped, not duplicated
    entry = store[0]
    assert entry["first_observed_batch"] == "20260101_0000_ET"  # preserved
    assert entry["last_observed_batch"] == "20260601_0900_ET"   # bumped
    assert entry["notes"] == "new note"                         # non-empty overwrites


def test_cmd_update_drops_entries_promoted_to_new_terminals(tmp_path):
    inputs_dir = tmp_path / "batch2"
    inputs_dir.mkdir()
    ms.save_store([{
        "country": "Vietnam", "candidate_name": "Cai Mep LNG",
        "first_observed_batch": "20260101_0000_ET",
    }])
    (inputs_dir / "staged_monitor_list.json").write_text("[]", encoding="utf-8")
    (inputs_dir / "staged_new_terminals.json").write_text(json.dumps([
        {"Country/Area": "Vietnam", "TerminalName": "Cai Mep LNG"},
    ]), encoding="utf-8")

    ms.cmd_update(str(inputs_dir), batch_label="20260601_0900_ET")

    assert ms.load_store() == []


def test_cmd_seed_writes_prior_monitor_list(tmp_path):
    inputs_dir = tmp_path / "batch3"
    inputs_dir.mkdir()
    ms.save_store([{"country": "Nigeria", "candidate_name": "Some FSRU"}])

    ms.cmd_seed(str(inputs_dir))

    out = inputs_dir / "prior_monitor_list.json"
    assert out.exists()
    assert json.loads(out.read_text(encoding="utf-8")) == [
        {"country": "Nigeria", "candidate_name": "Some FSRU"}
    ]
