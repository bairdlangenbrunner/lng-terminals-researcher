"""build_review_package._validate_records — the warn-only GUARD check for
staged-record vocabulary drift (an unknown key means no sheet reads it; a
missing required key means the sheet renders a blank/broken row)."""
import build_review_package as brp


def test_unknown_key_warns(capsys):
    brp._validate_records("updates", [
        {"terminal_id": "T1", "field_name": "Owner", "typo_field": "x"},
    ])
    out = capsys.readouterr().out
    assert "GUARD" in out
    assert "typo_field" in out


def test_missing_required_key_warns(capsys):
    brp._validate_records("updates", [
        {"terminal_id": "T1"},  # field_name required, missing
    ])
    out = capsys.readouterr().out
    assert "GUARD" in out
    assert "field_name" in out


def test_clean_records_are_silent(capsys):
    brp._validate_records("updates", [
        {"terminal_id": "T1", "field_name": "Owner", "new_value": "Foo"},
    ])
    out = capsys.readouterr().out
    assert out == ""


def test_non_list_input_is_a_no_op(capsys):
    brp._validate_records("updates", None)
    brp._validate_records("updates", {"not": "a list"})
    out = capsys.readouterr().out
    assert out == ""


def test_unknown_label_with_no_spec_is_a_no_op(capsys):
    # No STAGED_KEYS entry for this label and no explicit spec passed.
    brp._validate_records("some_label_nobody_registered", [{"anything": "goes"}])
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
