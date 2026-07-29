"""Guard: bare-domain/homepage URLs are never citations (gulf-turkiye Dörtyol wiki-row miss).

A citation must be the specific page containing the claimed value; a homepage
(scheme + host, no path) can't durably contain it and can never pass
url_verifier against the claim. warn_bare_domain_urls flags them in every
staged lane's citation-carrying keys ([ref]/_ref fields, new_value, ref_urls,
source_urls) at build time.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_review_package import warn_bare_domain_urls


def test_flags_homepage_in_wiki_source_urls():
    hits = warn_bare_domain_urls("wiki_updates", [
        {"terminal_name": "Dörtyol FSRU",
         "source_urls": ["https://www.turkiyetoday.com",
                         "https://files.elfsightcdn.com/x/GIIGNL-2026.pdf"]},
    ])
    assert len(hits) == 1
    assert hits[0][3] == "https://www.turkiyetoday.com"


def test_flags_homepage_with_trailing_slash_in_ref_new_value():
    hits = warn_bare_domain_urls("updates", [
        {"terminal_id": "T1", "field_name": "Status [ref]",
         "new_value": "https://lngprime.com/, https://lngprime.com/a/b/123/"},
    ])
    assert len(hits) == 1


def test_specific_pages_do_not_false_positive():
    assert not warn_bare_domain_urls("updates", [
        {"field_name": "Owner [ref]",
         "ref_urls": ["https://www.dusup.ae/our-business/lng/"],
         "new_value": "https://cdn.prod.website-files.com/a/b_GIIGNL-2023-Annual-Report.pdf"},
    ])


def test_prose_keys_are_not_scanned():
    # qa 'issue' prose may legitimately name a domain; only citation keys count.
    assert not warn_bare_domain_urls("qa_review", [
        {"issue": "announced per https://www.turkiyetoday.com coverage"},
    ])
