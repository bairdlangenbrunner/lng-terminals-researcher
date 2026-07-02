"""Name/country normalization + lifecycle helpers (normalize.py).

Cases are the real problem names from the deep-dives and run records —
diacritics (Pecém, Türkiye), numeral folding (Sakhalin-2 vs II), region-tag
stripping with the unbalanced-paren guard (Tortue FLNG), the
substatus=planned → effectively-proposed rule, and entity-list parsing.
"""
import pytest

import normalize as n


# ---------------------------------------------------------------- names

def test_diacritics_fold_to_ascii():
    assert n.normalize_terminal_name("Pecém FSRU") == n.normalize_terminal_name("Pecem")
    assert n.normalize_terminal_name("Mosjøen") == n.normalize_terminal_name("Mosjoen")


def test_country_diacritics():
    assert n.normalize_country("Türkiye") == n.normalize_country("Turkiye")


def test_roman_and_arabic_numerals_fold_together():
    assert (n.normalize_terminal_name("Sakhalin-2")
            == n.normalize_terminal_name("Sakhalin II LNG Terminal"))
    # ...but distinct unit numbers must stay distinct
    assert (n.normalize_terminal_name("Senboku 1")
            != n.normalize_terminal_name("Senboku 2"))


def test_apostrophe_dropped():
    assert n.normalize_terminal_name("Hua'an") == "huaan"


def test_region_suffix_stripped_after_comma():
    assert n.normalize_terminal_name("Chaozhou, Guangdong") == "chaozhou"
    assert n.normalize_terminal_name("Saint John, New Brunswick") == "saint john"


def test_comma_inside_parens_not_treated_as_region_tag():
    # Unbalanced-paren guard: the comma sits inside "(Gimi FLNG, Greater
    # Tortue Ahmeyim Phase 1)" — naive comma-splitting would leave "(Gimi FLNG"
    got = n.normalize_terminal_name(
        "Tortue FLNG (Gimi FLNG, Greater Tortue Ahmeyim Phase 1)")
    assert got.count("(") == got.count(")")


def test_facility_type_tag_stripped():
    assert n.normalize_terminal_name("Prelude (FLNG)") == "prelude"


def test_chinese_transliteration_produces_pinyin_candidate():
    pytest.importorskip("jieba")
    pytest.importorskip("pypinyin")
    cands = n.transliterate_to_english("中石油唐山曹妃甸LNG接收站")
    assert any("tangshan" in c and "caofeidian" in c for c in cands)


# ---------------------------------------------------------------- lifecycle

@pytest.mark.parametrize(
    "status, substatus, expected",
    [
        ("operating", "planned", "proposed"),      # the LNG Canada T3/T4 rule
        ("construction", "planned", "proposed"),
        ("operating", "actual", "operating"),
        ("proposed", "", "proposed"),
    ],
)
def test_effective_status_substatus_planned_means_proposed(status, substatus, expected):
    assert n.effective_status(status, substatus) == expected


# ---------------------------------------------------------------- entities

def test_parse_entity_list_with_bracket_percentages():
    got = n.parse_entity_list("QatarEnergy [70%]; Exxon Mobil Corp [30%]")
    assert [e["raw"] for e in got] == ["QatarEnergy", "Exxon Mobil Corp"]
    assert [e["pct"] for e in got] == [70.0, 30.0]


def test_parse_entity_list_spaced_slash_splits():
    got = n.parse_entity_list("New Fortress Energy / Celba")
    assert len(got) == 2
