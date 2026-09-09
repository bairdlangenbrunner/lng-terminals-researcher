"""Unit conversions + range parsing (capacity_normalize.py, which delegates to
normalize.py's single _CAPACITY_TO_MTPA table — one definition total)."""
import pytest

import capacity_normalize as cn


def test_bcm_to_mtpa_round_trip():
    # 1 mtpa LNG ~ 1.36 bcm/y (unit_conventions.md)
    assert cn.to_mtpa(1.36, "bcm/y") == pytest.approx(1.0)
    assert cn.to_bcm(1.0, "mtpa") == pytest.approx(1.36)


def test_mtpa_identity_and_synonym():
    assert cn.to_mtpa(5.2, "mtpa") == pytest.approx(5.2)
    assert cn.to_mtpa(5.2, "MMTPA") == pytest.approx(5.2)


def test_exotic_units():
    # Volumetric-per-day units derive from the SAME 1 mtpa = 1.36 bcm/y
    # equivalence as the bcm test above: 1 bcm = 35.3147 bcf, so
    # 1 mtpa = 1.36 * 35.3147 = 48.03 bcf/y.
    # These expectations were updated 2026-07-29 with the normalize.py fix that
    # replaced the old 365/130 constants (1 bcf/d ~ 2.81 mtpa). Those were off by
    # ~2.7x and contradicted both unit_conventions.md and GEM's own precomputed
    # CapacityinMtpa values (Stade/Wilhelmshaven FSRU: 750 MMcf/d -> 5.75 mtpa,
    # i.e. ~0.00767 mtpa per MMcf/d, not 0.00281).
    assert cn.to_mtpa(1.0, "bcf/d") == pytest.approx(365 / 48.03, abs=1e-3)
    assert cn.to_mtpa(600, "MMcf/d") == pytest.approx(600 * 365 / 48_030, rel=1e-6)
    # Cross-check against the database's own figure for a real row. Allow 1%:
    # GEM's stored 5.75 implies ~0.00767 mtpa per MMcf/d against our 0.00760, a
    # sub-1% spread from rounding the mtpa<->bcm equivalence, not a unit error.
    assert cn.to_mtpa(750, "MMcf/d") == pytest.approx(5.75, rel=0.01)


def test_unknown_unit_returns_none():
    assert cn.to_mtpa(3, "nonsense-unit") is None
    assert cn.to_bcm(3, "nonsense-unit") is None


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("5.2 mtpa", (5.2, 5.2, "mtpa")),
        ("5.2 to 5.6 mtpa", (5.2, 5.6, "mtpa")),
        ("5.2-5.6 mtpa", (5.2, 5.6, "mtpa")),
        ("5.2–5.6 MTPA", (5.2, 5.6, "mtpa")),  # en-dash + case fold
        ("around 5.2 mtpa", (5.2, 5.2, "mtpa")),
    ],
)
def test_parse_range(raw, expected):
    assert cn.parse_range(raw) == expected


def test_parse_range_failure():
    assert cn.parse_range("no capacity here") == (None, None, None)


def test_normalize_for_db_converts_and_carries_no_warning():
    out = cn.normalize_for_db(7.5, "bcm/y")
    assert out["mtpa_equivalent"] == pytest.approx(7.5 / 1.36)
    assert out["bcm_equivalent"] == pytest.approx(7.5)
    assert out["warning"] is None
