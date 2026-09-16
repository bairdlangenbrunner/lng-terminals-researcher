"""Tests for scripts/fetch.py's bot-wall escalation ladder and the
cf_clearance cookie store (Cloudflare and Imperva cookies alike).

Nothing here touches the network or launches Chrome: `_curl`, `_cffi_get` and
`_earn_clearance` are stubbed, and the cookie store is pointed at a temp dir.
"""
import subprocess
from pathlib import Path

import cf_clearance
import fetch
import pytest

_REAL_EARN = fetch._earn_clearance      # captured before the autouse stub replaces it

WALL_403 = b"<html><head><title>Just a moment...</title></head><body>cf_chl_opt</body></html>"
FIREWALL = b"<html><head><title>Attention Required! | Cloudflare</title></head></html>"
REAL = b"<html><head><title>HULL 2616 - LNG Tanker</title></head><body>HANWHA OCEAN</body></html>"
INCAPSULA = (b"<html><head><META NAME=\"robots\" CONTENT=\"noindex,nofollow\"><script src=\"/_Incapsula_Resource"
             b"?SWJIYLWA=5074a744e2e3d891814e9a2dace20bd4,719d34d31c8e3a6e6fffd425f7e032f3\"></script></head>"
             b"<body></body></html>")
NOT_FOUND = b"<html><head><title>404 Not Found</title></head><body>Page not found</body></html>"
AWS_WAF = (b"<html><head><title></title><script>window.awsWafCookieDomainList = ['listedcompany.com'];"
           b"</script><script src=\"https://x.token.awswaf.com/x/challenge.js\"></script></head>"
           b"<body><div id=\"challenge-container\"></div></body></html>")


class FakeCurl:
    """Scripted `_curl`: answers (status, body) per (cookie present?) and records calls."""

    def __init__(self, plain=("403", WALL_403), with_cookie=("200", REAL)):
        self.plain, self.with_cookie = plain, with_cookie
        self.calls = []

    def __call__(self, url, tmp, timeout, ua, insecure, headers=None, cookie=None):
        self.calls.append({"url": url, "ua": ua, "headers": headers, "cookie": cookie})
        status, body = self.with_cookie if cookie else self.plain
        Path(tmp).write_bytes(body)
        return subprocess.CompletedProcess(
            args=["curl"], returncode=0, stdout=f"{status}\ttext/html\t{url}", stderr="")


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setattr(cf_clearance, "store_path", lambda: tmp_path / "cf.json")
    monkeypatch.setattr(fetch, "require_curl", lambda: None)
    monkeypatch.setattr(fetch, "_earn_clearance", lambda url: (None, None))
    monkeypatch.setattr(fetch, "_cffi_get", lambda *a, **k: None)
    fetch._IMPERSONATE_HOSTS.clear()
    fetch._CLEARANCE_TRIED.clear()
    yield
    fetch._IMPERSONATE_HOSTS.clear()
    fetch._CLEARANCE_TRIED.clear()


class TestWallDetection:
    def test_challenge_page_is_a_wall(self):
        assert fetch._is_cf_wall("403", WALL_403)
        assert fetch._is_cf_wall("503", FIREWALL)

    def test_plain_403_without_markers_is_not(self):
        assert not fetch._is_cf_wall("403", b"<html>Forbidden by origin</html>")

    def test_200_with_markers_is_not(self):
        # an article ABOUT Cloudflare is content, not a wall
        assert not fetch._is_cf_wall("200", WALL_403)

    def test_non_cloudflare_walls(self):
        assert fetch._is_cf_wall("202", b"")                  # seatrium (AWS WAF) to curl
        assert fetch._is_cf_wall("202", AWS_WAF)              # ... and to curl_cffi
        assert fetch._is_cf_wall("200", INCAPSULA)            # Imperva script-only shell
        assert not fetch._is_cf_wall("202", b"<html>Accepted</html>")
        assert not fetch._is_cf_wall("404", NOT_FOUND)


class TestBodies:
    def test_zip_bundle_members_are_read(self, monkeypatch, tmp_path):
        import io, zipfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("dossier/summary.txt", "Capacity 4.5 mtpa at Ravenna")
            z.writestr("dossier/logo.png", b"\x89PNG")
        curl = FakeCurl(plain=("200", buf.getvalue()))
        monkeypatch.setattr(fetch, "_curl", curl)
        p = fetch.fetch_page("https://va.mite.gov.it/File/Documento/12345")
        assert p.is_pdf and p.notes == ["zip"] and "Ravenna" in p.text

    def test_empty_pdf_on_200_is_fetched_once_more(self, monkeypatch):
        curl = FakeCurl(plain=("200", b"%PDF-1.4 truncated"))
        monkeypatch.setattr(fetch, "_curl", curl)
        monkeypatch.setattr(fetch, "pdf_text", lambda path: ("", []))
        p = fetch.fetch_page("https://example.com/big.pdf")
        assert p.is_pdf and p.status == "200" and len(curl.calls) == 2
        assert "pdf_retry" in p.notes

    def test_ocr_language_is_overridable(self, monkeypatch):
        seen = {}
        monkeypatch.setattr(fetch.shutil, "which", lambda name: "/usr/bin/" + name)
        monkeypatch.setattr(fetch.subprocess, "run",
                            lambda cmd, **k: seen.setdefault("langs", cmd) and
                            subprocess.CompletedProcess(cmd, 1, stdout="eng\nfra\n", stderr=""))
        monkeypatch.setattr(fetch, "OCR_LANG", "fra+eng+ita")
        assert fetch._pdf_ocr("/nonexistent.pdf") == ""      # pdftoppm "fails" (rc 1)
        assert seen["langs"][:2] == ["tesseract", "--list-langs"]


class TestLadder:
    def test_plain_page_needs_no_escalation(self, monkeypatch):
        curl = FakeCurl(plain=("200", REAL))
        monkeypatch.setattr(fetch, "_curl", curl)
        p = fetch.fetch_page("https://example.com/x")
        assert p.status == "200" and p.notes == [] and len(curl.calls) == 1

    def test_firewall_page_falls_back_to_impersonation(self, monkeypatch):
        curl = FakeCurl(plain=("403", FIREWALL))
        monkeypatch.setattr(fetch, "_curl", curl)
        monkeypatch.setattr(fetch, "_cffi_get",
                            lambda url, t, ua, h, c: ("200", "text/html", url, REAL))
        p = fetch.fetch_page("https://www.shipvault.com/ships/1")
        assert p.status == "200" and "HANWHA" in p.text
        assert p.notes == ["cf_impersonate"]
        # the host is remembered: the next fetch skips curl entirely
        p2 = fetch.fetch_page("https://www.shipvault.com/ships/2")
        assert p2.notes == ["cf_impersonate"] and len(curl.calls) == 1

    def test_memoised_impersonation_that_walls_again_falls_through(self, monkeypatch):
        curl = FakeCurl()
        monkeypatch.setattr(fetch, "_curl", curl)
        fetch._IMPERSONATE_HOSTS.add("www.shipvault.com")
        monkeypatch.setattr(fetch, "_cffi_get",
                            lambda url, t, ua, h, c: ("403", "text/html", url, WALL_403))
        monkeypatch.setattr(fetch, "_earn_clearance",
                            lambda url: ("cf_clearance=abc", "UA-153"))
        p = fetch.fetch_page("https://www.shipvault.com/ships/1")
        assert p.status == "200" and p.notes == ["cf_clearance"]
        assert "www.shipvault.com" not in fetch._IMPERSONATE_HOSTS

    def test_js_challenge_earns_a_cookie_then_retries_curl(self, monkeypatch):
        curl = FakeCurl()
        monkeypatch.setattr(fetch, "_curl", curl)
        # impersonation alone does not pass the JS challenge
        monkeypatch.setattr(fetch, "_cffi_get",
                            lambda url, t, ua, h, c: ("403", "text/html", url, WALL_403))
        monkeypatch.setattr(fetch, "_earn_clearance",
                            lambda url: ("cf_clearance=abc", "Mozilla/5.0 Chrome/153"))
        p = fetch.fetch_page("https://www.marinetraffic.org/v/1")
        assert p.status == "200" and p.notes == ["cf_clearance"]
        assert curl.calls[-1]["cookie"] == "cf_clearance=abc"
        assert curl.calls[-1]["ua"] == "Mozilla/5.0 Chrome/153"   # cookie needs its own UA

    def test_stored_cookie_is_sent_up_front(self, monkeypatch):
        cf_clearance.save_store({"ua": "UA-153", "cookies": {
            ".marinetraffic.org": {"value": "zzz", "expires": 4e9, "saved": 0}}})
        curl = FakeCurl()
        monkeypatch.setattr(fetch, "_curl", curl)
        p = fetch.fetch_page("https://www.marinetraffic.org/v/1")
        assert p.status == "200" and p.notes == ["cf_clearance"]
        assert len(curl.calls) == 1 and curl.calls[0]["cookie"] == "cf_clearance=zzz"
        assert curl.calls[0]["ua"] == "UA-153"

    def test_aws_waf_wall_clears_to_the_real_status(self, monkeypatch):
        # seatrium: empty 202 to curl, challenge page to curl_cffi; with the
        # browser's cookie the page is a genuine 404, which must come back as
        # 404 (dead), not as a wall.
        curl = FakeCurl(plain=("202", b""), with_cookie=("404", NOT_FOUND))
        monkeypatch.setattr(fetch, "_curl", curl)
        monkeypatch.setattr(fetch, "_cffi_get",
                            lambda url, t, ua, h, c: ("202", "text/html", url, AWS_WAF))
        monkeypatch.setattr(fetch, "_earn_clearance",
                            lambda url: ("aws-waf-token=t; visid_incap_1=b", "UA-153"))
        p = fetch.fetch_page("https://investors.seatrium.com/x")
        assert p.status == "404" and p.notes == ["cf_clearance"]
        assert curl.calls[-1]["cookie"] == "aws-waf-token=t; visid_incap_1=b"

    def test_unpassable_wall_is_reported_not_raised(self, monkeypatch):
        monkeypatch.setattr(fetch, "_curl", FakeCurl())
        p = fetch.fetch_page("https://www.marinetraffic.org/v/1")
        assert p.status == "403" and "Just a moment" in p.text and p.notes == []

    def test_extra_headers_reach_curl(self, monkeypatch):
        curl = FakeCurl(plain=("200", b'{"name": "X"}'))
        monkeypatch.setattr(fetch, "_curl", curl)
        fetch.fetch_page("https://api.example.com/units/1", headers={"tx": "abc"})
        assert curl.calls[0]["headers"] == {"tx": "abc"}


class TestEarnClearance:
    def test_no_browser_env_blocks_the_launch(self, monkeypatch):
        monkeypatch.setenv("LNGCT_NO_BROWSER", "1")
        monkeypatch.setattr(fetch, "_earn_clearance", _REAL_EARN)
        launched = []
        monkeypatch.setattr(cf_clearance, "refresh", lambda urls, **k: launched.append(urls))
        assert fetch._earn_clearance("https://www.marinetraffic.org/v/1") == (None, None)
        assert launched == []
        assert "www.marinetraffic.org" in fetch._CLEARANCE_TRIED

    def test_one_launch_per_host_per_process(self, monkeypatch):
        monkeypatch.setattr(fetch, "_earn_clearance", _REAL_EARN)
        monkeypatch.delenv("LNGCT_NO_BROWSER", raising=False)
        launches = []

        def fake_refresh(urls, **k):
            launches.append(urls)
            cf_clearance.save_store({"ua": "UA", "cookies": {
                ".marinetraffic.org": {"cookies": {"cf_clearance": "new"}, "expires": 4e9, "saved": 0}}})
        monkeypatch.setattr(cf_clearance, "refresh", fake_refresh)
        assert fetch._earn_clearance("https://www.marinetraffic.org/a") == ("cf_clearance=new", "UA")
        assert fetch._earn_clearance("https://www.marinetraffic.org/b") == (None, None)
        assert len(launches) == 1


class TestCookieStore:
    def test_round_trip_and_suffix_match(self):
        cf_clearance.save_store({"ua": "UA", "cookies": {
            ".marinetraffic.org": {"cookies": {"cf_clearance": "v1"}, "expires": 4e9, "saved": 0}}})
        assert cf_clearance.cookie_for("https://www.marinetraffic.org/x") == ("cf_clearance=v1", "UA")
        assert cf_clearance.cookie_for("https://marinetraffic.org/") == ("cf_clearance=v1", "UA")
        assert cf_clearance.cookie_for("https://notmarinetraffic.org/") is None
        assert cf_clearance.cookie_for("https://www.shipvault.com/") is None

    def test_legacy_single_value_entry_still_reads(self):
        cf_clearance.save_store({"ua": "UA", "cookies": {
            ".marinetraffic.org": {"value": "v1", "expires": 4e9, "saved": 0}}})
        assert cf_clearance.cookie_for("https://www.marinetraffic.org/x") == ("cf_clearance=v1", "UA")

    def test_cookies_across_matching_domains_join(self):
        cf_clearance.save_store({"ua": "UA", "cookies": {
            "investors.seatrium.com": {"cookies": {"incap_ses_9_1": "s"}, "expires": 4e9, "saved": 0},
            ".seatrium.com": {"cookies": {"visid_incap_1": "v", "nlbi_1": "n"}, "expires": 4e9, "saved": 0}}})
        header, ua = cf_clearance.cookie_for("https://investors.seatrium.com/news")
        assert set(header.split("; ")) == {"incap_ses_9_1=s", "visid_incap_1=v", "nlbi_1=n"}
        assert cf_clearance.cookie_for("https://www.seatrium.com/") == ("visid_incap_1=v; nlbi_1=n", "UA")

    def test_merge_keeps_only_wall_cookies(self):
        store = {"ua": "", "cookies": {}}
        kept = cf_clearance.merge_cookies(store, [
            {"name": "cf_clearance", "value": "c", "domain": ".marinetraffic.org", "expires": 4e9},
            {"name": "incap_ses_9_1", "value": "s", "domain": "investors.seatrium.com", "expires": -1},
            {"name": "_ga", "value": "x", "domain": ".seatrium.com", "expires": 4e9},
        ], "UA-153", now=1000.0)
        assert kept == 2 and store["ua"] == "UA-153"
        assert store["cookies"][".marinetraffic.org"]["cookies"] == {"cf_clearance": "c"}
        assert store["cookies"]["investors.seatrium.com"] == {
            "cookies": {"incap_ses_9_1": "s"}, "expires": 1000.0 + 1800, "saved": 1000.0}
        assert ".seatrium.com" not in store["cookies"]

    def test_expired_cookie_is_ignored(self):
        cf_clearance.save_store({"ua": "UA", "cookies": {
            ".marinetraffic.org": {"cookies": {"cf_clearance": "old"}, "expires": 1.0, "saved": 0}}})
        assert cf_clearance.cookie_for("https://www.marinetraffic.org/x") is None

    def test_forget_drops_only_that_host(self):
        cf_clearance.save_store({"ua": "UA", "cookies": {
            ".marinetraffic.org": {"cookies": {"cf_clearance": "a"}, "expires": 4e9, "saved": 0},
            ".marinevesseltraffic.com": {"cookies": {"cf_clearance": "b"}, "expires": 4e9, "saved": 0}}})
        cf_clearance.forget("https://www.marinetraffic.org/x")
        assert cf_clearance.cookie_for("https://www.marinetraffic.org/x") is None
        assert cf_clearance.cookie_for("https://www.marinevesseltraffic.com/x") == ("cf_clearance=b", "UA")

    def test_missing_store_is_empty(self):
        assert cf_clearance.load_store() == {"ua": "", "cookies": {}}
        assert cf_clearance.cookie_for("https://www.marinetraffic.org/x") is None

    def test_challenge_titles(self):
        assert cf_clearance._is_challenge_title("Just a moment...")
        assert cf_clearance._is_challenge_title("")
        assert not cf_clearance._is_challenge_title("HULL 2616 - LNG Tanker, IMO 1175527")

    def test_challenge_bodies(self):
        assert cf_clearance._is_challenge_body("")
        assert cf_clearance._is_challenge_body(AWS_WAF.decode())
        assert cf_clearance._is_challenge_body(INCAPSULA.decode())
        assert not cf_clearance._is_challenge_body(NOT_FOUND.decode())
