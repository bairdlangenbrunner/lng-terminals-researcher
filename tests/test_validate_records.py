"""build_review_package._validate_records — the gating GUARD check for
staged-record vocabulary drift (an unknown key means no sheet reads it; a
missing required key means the sheet renders a blank/broken row).

It returns a finding COUNT, and main() blocks the build on a non-zero total
unless --allow-warnings is passed, so these tests assert the count as well as
the message: a finding that prints but returns 0 would not gate."""
import build_review_package as brp


def test_unknown_key_warns(capsys):
    assert brp._validate_records("updates", [
        {"terminal_id": "T1", "field_name": "Owner", "typo_field": "x"},
    ]) == 1
    out = capsys.readouterr().out
    assert "GUARD" in out
    assert "typo_field" in out


def test_missing_required_key_warns(capsys):
    assert brp._validate_records("updates", [
        {"terminal_id": "T1"},  # field_name required, missing
    ]) == 1
    out = capsys.readouterr().out
    assert "GUARD" in out
    assert "field_name" in out


def test_clean_records_are_silent(capsys):
    assert brp._validate_records("updates", [
        {"terminal_id": "T1", "field_name": "Owner", "new_value": "Foo"},
    ]) == 0
    out = capsys.readouterr().out
    assert out == ""


def test_non_list_input_is_a_finding(capsys):
    # A staged JSON file that fails to parse, or holds an object instead of a
    # list, used to arrive here as None/{} and be treated as "no records" — the
    # workbook then built clean off an input that had silently vanished. It is
    # now a gating finding.
    assert brp._validate_records("updates", None) == 1
    assert brp._validate_records("updates", {"not": "a list"}) == 1
    out = capsys.readouterr().out
    assert out.count("GUARD") == 2
    assert "expected a JSON list" in out


def test_unknown_label_with_no_spec_is_a_no_op(capsys):
    # No STAGED_KEYS entry for this label and no explicit spec passed.
    assert brp._validate_records("some_label_nobody_registered",
                                 [{"anything": "goes"}]) == 0
    out = capsys.readouterr().out
    assert out == ""


def test_explicit_spec_overrides_staged_keys_lookup(capsys):
    # new_terminals has no static STAGED_KEYS entry (its known-key set is built
    # dynamically from the live CSV header in main()) — confirm passing a spec
    # directly still validates against it.
    brp._validate_records("new_terminals", [{"TerminalName": "Foo", "bogus": "x"}],
                           spec={"known": {"TerminalName"}, "required": {"TerminalName"}})
    out = capsys.readouterr().out
    assert "bogus" in out
