"""Integration snapshot: run giignl_extract.py against the committed
data/GIIGNL-2026-Annual-Report-0526b.pdf and pin known-good rows.

This is the regression net for the extractor's edge-case hardening (owner
cross-row bleed, footer contamination, status hints, ', BC'-style site tags) —
the exact defects described in scripts/README.md's deep-dive. If the numbers
here drift after an extractor edit, the edit broke a defended case.

Skipped when poppler's pdftotext is unavailable (the extractor shells out to it).
Runs the extraction ONCE per session (module-scoped fixture); takes a few seconds.
"""
import csv
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PDF = REPO_ROOT / "data" / "GIIGNL-2026-Annual-Report-0526b.pdf"
SCRIPT = REPO_ROOT / "scripts" / "giignl_extract.py"

pytestmark = [
    pytest.mark.skipif(shutil.which("pdftotext") is None,
                       reason="poppler pdftotext not installed"),
    pytest.mark.skipif(not PDF.exists(),
                       reason="committed GIIGNL 2026 PDF not present"),
]


@pytest.fixture(scope="module")
def rows(tmp_path_factory):
    out = tmp_path_factory.mktemp("giignl") / "giignl_2026.csv"
    r = subprocess.run(
        [sys.executable, str(SCRIPT), str(PDF), "--year", "2026",
         "--output", str(out)],
        capture_output=True, text=True, timeout=300,
    )
    assert r.returncode == 0, f"extractor failed:\n{r.stderr}"
    with open(out, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_total_row_count(rows):
    assert len(rows) == 348


def test_section_totals_track_report(rows):
    liq = sum(float(r["capacity_mtpa"]) for r in rows
              if r["section_type"] == "liquefaction" and r["capacity_mtpa"])
    regas = sum(float(r["capacity_mtpa"]) for r in rows
                if r["section_type"] == "regasification" and r["capacity_mtpa"])
    assert liq == pytest.approx(529.5, abs=1.0)
    assert regas == pytest.approx(1247.9, abs=1.0)


def test_qatar_s2_three_trains_sum(rows):
    s2 = [r for r in rows if r["site_name"] == "QatarEnergy LNG S(2)"]
    assert sorted(r["trains"] for r in s2) == ["T3", "T4", "T5"]
    assert sum(float(r["capacity_mtpa"]) for r in s2) == pytest.approx(14.1)


def test_owner_cross_row_bleed_stays_fixed(rows):
    # Niigata's owner is Nihonkai LNG — the neighbouring Tokyo Gas terms must
    # not bleed in (the paren-balance head-bleed repair)
    niigata = next(r for r in rows if r["site_name"] == "Niigata")
    assert niigata["owner"] == "Nihonkai LNG"
    niihama = next(r for r in rows if r["site_name"] == "Niihama")
    assert niihama["owner"].startswith("Niihama LNG")


def test_sodegaura_spaced_slash_co_owner_survives_extraction(rows):
    sode = next(r for r in rows if r["site_name"] == "Sodegaura")
    assert sode["owner"] == "Tokyo Gas / JERA"
    assert float(sode["capacity_mtpa"]) == pytest.approx(29.3)


def test_bontang_mothballed_hint_tags_only_train_e(rows):
    bontang = {r["site_name"]: r for r in rows
               if r["site_name"].startswith("Bontang")}
    assert bontang["Bontang Train E"]["status"] == "mothballed"
    assert bontang["Bontang Train F"]["status"] == ""


def test_lng_canada_site_tag_stripped(rows):
    lc = [r for r in rows if r["site_name"] == "LNG Canada"]
    # ", BC" stripped from the site name; two 7.0 mtpa trains
    assert sorted(r["trains"] for r in lc) == ["T1", "T2"]
    assert all(float(r["capacity_mtpa"]) == pytest.approx(7.0) for r in lc)


def test_no_footer_contamination(rows):
    for r in rows:
        for field in ("site_name", "country", "owner"):
            assert "edition" not in (r[field] or "").lower(), r
