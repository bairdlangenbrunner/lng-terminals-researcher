"""Guard: banned sources are never citations, even corroborated.

User directive 2026-07-17: abarrelfull (abarrelfull.wikidot.com, abarrelfull.co.uk)
must never appear as a reference anywhere. gem.wiki/globalenergymonitor.org are in
the same banned list as a build-time backstop to the merge-QC circularity gate.
Prose fields (source_notes, qa issue text) are not scanned — they may document a
banned source's removal.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_review_package import warn_banned_domain_urls


def test_flags_abarrelfull_wikidot_in_ref_new_value():
    hits = warn_banned_domain_urls("updates", [
        {"terminal_id": "T1", "field_name": "Capacity [ref]",
         "new_value": "http://abarrelfull.wikidot.com/mina-al-ahmadi-lng-terminal"},
    ])
    assert len(hits) == 1


def test_flags_abarrelfull_couk_and_gemwiki_in_lists():
    hits = warn_banned_domain_urls("wiki_updates", [
        {"terminal_name": "Zeebrugge",
         "source_urls": ["https://www.abarrelfull.co.uk/Fluxys_Zeebrugge_LNG_Terminal",
                         "https://www.gem.wiki/Zeebrugge_LNG_Terminal",
                         "https://www.fluxys.com/en/about-us/dunkerque-lng"]},
    ])
    assert len(hits) == 2


def test_clean_sources_do_not_flag():
    assert not warn_banned_domain_urls("updates", [
        {"field_name": "Owner [ref]",
         "ref_urls": ["https://excelerateenergy.com/projects/mina-al-ahmadi-gasport/"]},
    ])


def test_prose_mention_of_removal_not_flagged():
    assert not warn_banned_domain_urls("updates", [
        {"field_name": "Capacity [ref]",
         "new_value": "https://excelerateenergy.com/projects/mina-al-ahmadi-gasport/",
         "source_notes": "replaced banned http://abarrelfull.wikidot.com/x per user directive"},
    ])
