"""Owner parsing + name-folding helpers in report_diff.py.

These pin the edge-case fixes described in scripts/README.md's deep-dive:
spaced-slash co-owner split (Sodegaura 'Tokyo Gas / JERA'), tight-slash
company names left intact, Owner:/Charterer: role separation, shareholder
expansion out of parens, paren-aware top-level splitting, and the
expansion-row suffix folds (Train E / GL1Z / Stage III) with the
single-letter guard (Senboku II is a unit name, not a code).
"""
import report_diff as rd


# ---------------------------------------------------------------- owners

def test_spaced_slash_splits_into_two_owners():
    terminal, vessel, shareholders = rd.parse_report_owner("Tokyo Gas / JERA")
    assert terminal == ["tokyo-gas", "jera"]
    assert vessel == []
    assert shareholders == []


def test_tight_slash_is_one_company_name():
    terminal, vessel, shareholders = rd.parse_report_owner(
        "Japex/Fukushima Gas Power")
    assert len(terminal) == 1


def test_owner_charterer_roles_separate():
    terminal, vessel, _ = rd.parse_report_owner(
        "Owner: Excelerate Energy, Charterer: Engro")
    assert terminal == ["engro"]
    assert vessel == ["excelerate"]


def test_shareholders_extracted_from_parens():
    terminal, _, shareholders = rd.parse_report_owner(
        "UTE Escobar (50% Enarsa, 50% YPF)")
    assert terminal == ["ute escobar"]
    assert shareholders == ["enarsa", "ypf"]


def test_split_top_level_is_paren_aware():
    assert rd._split_top_level("ENGIE (63%), Ameris Capital (37%)") == [
        "ENGIE (63%)", "Ameris Capital (37%)"]


# ---------------------------------------------------------------- name folds

def test_train_word_suffix_folds():
    assert rd._strip_train_word_suffix("Bontang Train E") == "Bontang"


def test_unit_code_suffix_folds():
    assert rd._strip_unit_code_suffix("Arzew GL1Z") == "Arzew"


def test_single_letter_roman_guard():
    # Senboku II: "II" is part of the terminal name, not a unit code
    assert rd._strip_unit_code_suffix("Senboku II") is None


def test_stage_suffix_folds():
    assert rd._strip_stage_suffix("Corpus Christi Stage III") == "Corpus Christi"


def test_word_boundary_substring():
    assert rd._word_boundary_substring("nansha", "guangzhou nansha") is True
    assert rd._word_boundary_substring("nansha", "longkou nanshan") is False
    assert rd._word_boundary_substring("arzew", "arzew-bethioua") is True
