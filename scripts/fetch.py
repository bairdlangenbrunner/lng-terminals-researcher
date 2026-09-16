"""
Shared curl wrapper for every network-touching script.

All fetching in this repo shells out to the `curl` binary rather than a Python
HTTP library — a deliberate choice: several sources (Google Sheets export,
ChinaShipBuild, marinetraffic.org) block or degrade non-browser clients, and
curl with a browser User-Agent has been the reliable path since the May 2026
pilot. The cost is a system dependency that pip can't declare, so this module
checks for curl up front and fails with an actionable message instead of a
raw FileNotFoundError.

Library usage:
    from fetch import download, fetch_text, fetch_page, CHROME_UA, FetchError

CLI (any page, through the whole ladder — use this before concluding a URL
is unreachable):
    python scripts/fetch.py <url> [--text | --head 2000]

    download(url, out_path, timeout=60)          # save body to a file
    status, body = fetch_text(url, timeout=30)   # ("200", "<html>...")
    page = fetch_page(url)                       # Page(status, text, content_type,
                                                 #      final_url, is_pdf, ...)

`fetch_page` is the rich form the §3.8 verifier uses (ported 2026-09-16 from
the terminals/pipelines verifiers' fetch layers):
  - `--compressed`: some CDNs gzip the body regardless of request headers;
    without it the body decodes to garbage and a live page fails its content
    check.
  - PDF bodies (content-type, `.pdf` path, or `%PDF-` magic) are run through
    `pdftotext -layout` (pypdf fallback, tesseract OCR for scanned PDFs) so a
    DART/Bursa filing or a class-society PDF is verified on its TEXT, not on
    binary soup. A `.pdf` URL that returns HTML is an interstitial and is
    handed downstream as HTML. A PDF that extracts to nothing on a 200 is
    fetched once more (large PDFs on slow hosts truncate; note `pdf_retry`).
    ZIP bundles (some regulator portals serve a filing as one zip of PDFs)
    are unpacked and every PDF/text member concatenated (note `zip`,
    `is_pdf=True` downstream since there is no HTML title to check).
    OCR languages: module constant `OCR_LANG`; a repo's verifier overrides it
    at import if its sources need other packs (this module is shared verbatim
    by the carriers, terminals and pipelines repos — keep it identical).
  - Charset: honour the Content-Type charset, then the page's own <meta
    charset>, widening gb2312/gbk -> gb18030 and euc-kr -> cp949 (Chinese/
    Korean yard and press pages routinely declare the narrow one). Only then
    fall back to utf-8-with-replacement.
  - Retries: an SSL handshake failure retries once with `-k` (labelled
    `insecure_tls` — the bytes are real, the host identity was not verified);
    a 000/empty-body response retries once WITHOUT the browser UA (a few hosts
    abort on a Chrome UA and serve curl's default fine).
  - Bot walls (2026-09-16): a Cloudflare firewall page retries through
    `curl_cffi` (Chrome TLS fingerprint); a JS challenge (Cloudflare managed
    challenge, Imperva/Incapsula) earns the wall's cookies via a real Chrome
    (`cf_clearance.py`) and retries with them. Notes
    `cf_impersonate` / `cf_clearance` record the route. See the block above
    `_curl`.
"""
import codecs
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

# One canonical browser UA for the whole repo. pull_backend/csb_fetch used a
# bare "Mozilla/5.0" and url_verifier/imo_tracker a full Chrome string; the
# full string works everywhere the bare one did.
CHROME_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

_CURL_INSTALL_HINT = (
    "curl not found on PATH. Install it and re-run:\n"
    "  macOS:         xcode-select --install  (or `brew install curl`)\n"
    "  Debian/Ubuntu: sudo apt install curl\n"
    "  Windows:       ships with Windows 10+; otherwise winget install curl"
)

# A PDF whose text layer yields fewer characters than this is treated as a scan
# and sent to OCR (image-only PDFs often still carry a few stray characters
# from stamps or form fields). OCR is slow (~1-2 s/page) so it is capped.
_PDF_TEXT_MIN = 200
_OCR_MAX_PAGES = 25
# tesseract language packs for scanned PDFs; missing packs are dropped at run
# time. Override per repo (`fetch.OCR_LANG = ...`) rather than editing here.
OCR_LANG = "eng+kor+chi_sim"

# curl exit codes that mean the TLS handshake failed (not that the page is gone).
_CURL_SSL_EXITS = {35, 51, 58, 59, 60, 77, 83, 90, 91}

_META_CHARSET_RE = re.compile(
    rb"""<meta[^>]+charset\s*=\s*["']?\s*([A-Za-z0-9_\-]+)""", re.I)
# gb2312/gbk are proper subsets of gb18030 and euc-kr of cp949; pages declare
# the narrow one and serve characters outside it. Widening is always safe.
_CHARSET_WIDEN = {"gb2312": "gb18030", "gbk": "gb18030", "gb_2312-80": "gb18030",
                  "euc-cn": "gb18030", "big5": "big5hkscs", "big5-hkscs": "big5hkscs",
                  "euc-kr": "cp949", "ks_c_5601-1987": "cp949", "ksc5601": "cp949"}


class FetchError(RuntimeError):
    pass


@dataclass
class Page:
    """One fetched URL. `text` is always the best available TEXT rendering of
    the body (HTML source for HTML; extracted text for PDFs)."""
    status: str                 # HTTP status as a string; "000" = transport failure
    text: str
    content_type: str = ""
    final_url: str = ""         # after redirects (curl -L); "" if unknown
    is_pdf: bool = False
    raw_len: int = 0
    notes: list[str] = field(default_factory=list)   # "insecure_tls", "no_ua_retry", "pdf_ocr", ...

    # Backwards-compatible tuple view: `status, text = page` still works.
    def __iter__(self):
        yield self.status
        yield self.text


def require_curl() -> None:
    """Raise FetchError with install instructions if curl is missing."""
    if shutil.which("curl") is None:
        raise FetchError(_CURL_INSTALL_HINT)


def download(url: str, out_path: str | Path, *, timeout: int = 60,
             ua: str = CHROME_UA, min_bytes: int | None = None) -> Path:
    """
    curl `url` to `out_path`. Raises FetchError if curl fails or (when
    min_bytes is set) the body is suspiciously small — e.g. a Google Sheet
    that's no longer public, or a CSB error page.
    """
    require_curl()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["curl", "-sL", "--compressed", "-A", ua, "--max-time", str(timeout),
         url, "-o", str(out_path)],
        capture_output=True, text=True, timeout=timeout + 10,
    )
    if result.returncode != 0:
        raise FetchError(f"curl failed for {url}: {result.stderr.strip()}")
    if min_bytes is not None:
        size = out_path.stat().st_size
        if size < min_bytes:
            raise FetchError(
                f"{url} returned a suspiciously small body ({size} bytes; "
                f"expected >= {min_bytes}) — check the URL is still valid "
                f"and publicly accessible."
            )
    return out_path


# ---------------------------------------------------------------------------
# PDF / text extraction helpers
# ---------------------------------------------------------------------------

def _pdftotext(path: str) -> str:
    """poppler `pdftotext -layout`; '' on any failure."""
    try:
        r = subprocess.run(["pdftotext", "-layout", path, "-"],
                           capture_output=True, timeout=120)
        if r.returncode == 0:
            return r.stdout.decode("utf-8", errors="replace")
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    return ""


def _pypdf_text(path: str, max_pages: int = 400) -> str:
    """In-process fallback when pdftotext is missing/empty; '' on failure."""
    try:
        from pypdf import PdfReader
        rd = PdfReader(path)
        parts = []
        for pg in rd.pages[:max_pages]:
            try:
                parts.append(pg.extract_text() or "")
            except Exception:  # noqa: BLE001 — one bad page shouldn't sink the doc
                continue
        return "\n".join(parts)
    except Exception:  # noqa: BLE001
        return ""


def _pdf_ocr(path: str, lang: str | None = None) -> str:
    """OCR a scanned PDF via pdftoppm + tesseract, capped at _OCR_MAX_PAGES.
    '' when either binary is missing or nothing comes out. Only called when
    the text layer is (nearly) empty, since OCR is slow. OCR output mangles
    digits and accents, so prefer long alphabetic tokens when verifying
    against an OCR'd document."""
    if not (shutil.which("pdftoppm") and shutil.which("tesseract")):
        return ""
    lang = lang or OCR_LANG
    # Fall back to plain English if the extra language packs aren't installed.
    try:
        langs = subprocess.run(["tesseract", "--list-langs"], capture_output=True,
                               text=True, timeout=30).stdout.split()
        lang = "+".join(x for x in lang.split("+") if x in langs) or "eng"
    except (FileNotFoundError, subprocess.SubprocessError):
        lang = "eng"
    try:
        with tempfile.TemporaryDirectory(prefix="lngct_ocr_") as tmpdir:
            stem = os.path.join(tmpdir, "pg")
            r = subprocess.run(["pdftoppm", "-r", "200", "-gray", "-png",
                                "-l", str(_OCR_MAX_PAGES), path, stem],
                               capture_output=True, timeout=180)
            if r.returncode != 0:
                return ""
            chunks = []
            for name in sorted(os.listdir(tmpdir)):
                if not name.endswith(".png"):
                    continue
                t = subprocess.run(["tesseract", os.path.join(tmpdir, name), "stdout",
                                    "-l", lang, "--psm", "6"],
                                   capture_output=True, text=True, timeout=120)
                if t.returncode == 0 and t.stdout.strip():
                    chunks.append(t.stdout)
            return "\n".join(chunks)
    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        return ""


def pdf_text(path: str) -> tuple[str, list[str]]:
    """Best-effort text of a PDF on disk: pdftotext -> pypdf -> OCR.
    Returns (text, notes)."""
    notes = []
    text = _pdftotext(path)
    if len(text.strip()) < _PDF_TEXT_MIN:
        alt = _pypdf_text(path)
        if len(alt.strip()) > len(text.strip()):
            text, _ = alt, notes.append("pdf_pypdf")
    if len(text.strip()) < _PDF_TEXT_MIN:
        ocr = _pdf_ocr(path)
        if ocr.strip():
            text, _ = ocr, notes.append("pdf_ocr")
    return text, notes


def _unzip_text(path: str) -> str:
    """Some regulator portals (e.g. Italy's va.mite.gov.it AIA/VIA dossiers)
    serve a whole filing as a single ZIP bundle of PDFs at what looks like a
    single-document URL. Extract every member, pdftotext any PDFs (and decode
    any plain-text members), and concatenate — so a value buried in one PDF
    inside the bundle is still verifiable against the bundle's own URL.
    '' on any failure (not a real zip, unzip missing, nothing extractable)."""
    try:
        with tempfile.TemporaryDirectory(prefix="lngct_zip_") as tmpdir:
            r = subprocess.run(["unzip", "-o", "-qq", path, "-d", tmpdir],
                               capture_output=True, text=True, timeout=60)
            if r.returncode not in (0, 1):  # 1 = some warnings, often still fine
                return ""
            chunks = []
            for root, _dirs, files in os.walk(tmpdir):
                for name in files:
                    fpath = os.path.join(root, name)
                    try:
                        with open(fpath, "rb") as f:
                            head = f.read(5)
                    except OSError:
                        continue
                    if head == b"%PDF-":
                        text = _pdftotext(fpath)
                    elif name.lower().endswith((".txt", ".csv", ".xml", ".html", ".htm")):
                        try:
                            text = Path(fpath).read_bytes().decode("utf-8", errors="replace")
                        except OSError:
                            text = ""
                    else:
                        continue
                    if text.strip():
                        chunks.append(text)
            return "\n".join(chunks)
    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        return ""


def _decode_html(raw: bytes, content_type: str) -> str:
    """Decode an HTML body honouring the declared charset (header, then meta),
    widening narrow CJK declarations; utf-8-with-replacement as the last resort."""
    enc = None
    m = re.search(r"charset\s*=\s*[\"']?\s*([A-Za-z0-9_\-]+)", content_type or "", re.I)
    if m:
        enc = m.group(1).lower()
    if not enc or enc in ("iso-8859-1", "ascii", "us-ascii", "latin-1", "latin1"):
        mm = _META_CHARSET_RE.search(raw[:4096])
        if mm:
            enc = mm.group(1).decode("ascii", "ignore").strip().lower()
    if enc:
        enc = _CHARSET_WIDEN.get(enc, enc)
        try:
            codecs.lookup(enc)
            return raw.decode(enc, errors="replace")
        except (LookupError, ValueError):
            pass
    return raw.decode("utf-8", errors="replace")


def _looks_like_pdf(url: str, content_type: str, raw: bytes) -> bool:
    return ("pdf" in (content_type or "").lower()
            or url.split("?")[0].lower().endswith(".pdf")
            or raw[:5] == b"%PDF-")


def _looks_like_zip(url: str, content_type: str, raw: bytes) -> bool:
    return ("zip" in (content_type or "").lower()
            or url.split("?")[0].lower().endswith(".zip")
            or raw[:4] == b"PK\x03\x04")


def _extract(url: str, tmp: str, content_type: str, raw: bytes,
             notes: list[str]) -> tuple[str, bool]:
    """(text, is_pdf) for a fetched body: zip -> members' text; PDF -> text
    layer / OCR; a .pdf URL that returned HTML is an interstitial (bot
    challenge, login wall) and is handed downstream as HTML; else decode."""
    if _looks_like_zip(url, content_type, raw):
        Path(tmp).write_bytes(raw)
        notes.append("zip")
        return _unzip_text(tmp), True
    is_pdf = _looks_like_pdf(url, content_type, raw)
    if is_pdf and raw[:5] != b"%PDF-" and raw.lstrip()[:1] == b"<":
        is_pdf = False
    if is_pdf:
        Path(tmp).write_bytes(raw)
        text, pdf_notes = pdf_text(tmp)
        notes.extend(pdf_notes)
        return text, True
    return _decode_html(raw, content_type), False


# ---------------------------------------------------------------------------
# The fetch
# ---------------------------------------------------------------------------

def _curl(url: str, tmp: str, timeout: int, ua: str | None, insecure: bool,
          headers: dict | None = None, cookie: str | None = None):
    cmd = ["curl", "-sL", "--compressed", "-o", tmp,
           "-w", "%{http_code}\t%{content_type}\t%{url_effective}",
           "--max-time", str(timeout)]
    if ua:
        cmd += ["-A", ua]
    if insecure:
        cmd += ["-k"]
    for k, v in (headers or {}).items():
        cmd += ["-H", f"{k}: {v}"]
    if cookie:
        cmd += ["-b", cookie]
    return subprocess.run(cmd + [url], capture_output=True, text=True,
                          timeout=timeout + 10)


# ---------------------------------------------------------------------------
# Bot walls (2026-09-16)
# ---------------------------------------------------------------------------
#
# Three kinds, two answers:
#   - the "Attention Required! | Cloudflare" firewall page (shipvault.com,
#     marinetraffic.com) keys on the TLS fingerprint. `curl_cffi` impersonating
#     Chrome's handshake gets HTTP 200 — no cookie, no browser.
#   - the JS managed challenge ("Just a moment...", cf-mitigated: challenge;
#     marinetraffic.org, marinevesseltraffic.com) needs a real browser once:
#     cf_clearance.refresh() drives Google Chrome over DevTools, and the
#     cf_clearance cookie it earns then works from plain curl for a year, as
#     long as the User-Agent matches that Chrome.
#   - other JS challenges that hide behind a "successful" status: AWS WAF
#     (investors.seatrium.com — empty HTTP 202 to curl, a 202 challenge.js
#     page to curl_cffi) and Imperva/Incapsula (script-only 200/202 shell).
#     Same answer as the managed challenge: the cookies a real Chrome earns
#     (aws-waf-token, incap_ses_/visid_incap_/nlbi_) replay through curl — and
#     for seatrium the page behind the wall is a genuine 404, which grades dead.
# fetch_page tries them in that order (impersonation first — no window pops),
# once per host per process, and labels the Page notes so the verifier's OK
# reason shows which route was used ("cf_impersonate" / "cf_clearance").

_CF_WALL_STATUSES = {"403", "503", "429"}
_CF_WALL_MARKERS = (b"just a moment", b"attention required", b"cf-mitigated",
                    b"challenge-platform", b"cf_chl_", b"cf-chl", b"cloudflare",
                    b"enable javascript and cookies to continue")
# Walls that hide behind a "successful" status: AWS WAF's challenge.js page
# (202), Imperva's script-only shell (200/202), PerimeterX's captcha page.
_WALL_MARKERS_ANY_STATUS = (b"awswaf", b"aws-waf-token",
                            b"_incapsula_resource", b"incapsula incident",
                            b"px-captcha", b"perimeterx")
# hosts where impersonation already cleared a wall this process: skip curl.
_IMPERSONATE_HOSTS: set[str] = set()
# hosts we already tried to earn a cookie for this process (one launch each).
_CLEARANCE_TRIED: set[str] = set()
_CFFI_HINTED = False


def _is_cf_wall(status: str, raw: bytes) -> bool:
    head = raw[:20000].lower()
    if any(m in head for m in _WALL_MARKERS_ANY_STATUS):
        return True
    if status == "202" and not head.strip():        # Imperva's empty 202 to curl
        return True
    if status not in _CF_WALL_STATUSES:
        return False
    return any(m in head for m in _CF_WALL_MARKERS)


def _host(url: str) -> str:
    from urllib.parse import urlsplit
    try:
        return (urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def _cffi_get(url: str, timeout: int, ua: str | None, headers: dict | None,
              cookie: str | None):
    """(status, content_type, final_url, raw) via curl_cffi, or None if unavailable."""
    global _CFFI_HINTED
    try:
        from curl_cffi import requests as cffi_requests
    except ImportError:
        if not _CFFI_HINTED:
            _CFFI_HINTED = True
            print("  [fetch] curl_cffi not installed — Cloudflare firewall pages cannot be "
                  "passed (pip install curl_cffi)", file=sys.stderr)
        return None
    hdrs = dict(headers or {})
    if ua:
        hdrs["User-Agent"] = ua
    cookies = {}
    for part in (cookie or "").split(";"):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            cookies[k] = v
    try:
        r = cffi_requests.get(url, impersonate="chrome", headers=hdrs, cookies=cookies,
                              timeout=timeout, allow_redirects=True)
    except Exception as e:  # transport / TLS / timeout
        print(f"  [fetch] curl_cffi error for {url}: {e}", file=sys.stderr)
        return None
    return (str(r.status_code), (r.headers.get("content-type") or "").lower(),
            str(r.url or ""), r.content or b"")


def _clearance_cookie(url: str) -> tuple[str | None, str | None]:
    """(Cookie header value, UA it was earned with) from the cf_clearance store."""
    try:
        from cf_clearance import cookie_for
    except ImportError:
        return None, None
    hit = cookie_for(url)
    if not hit:
        return None, None
    header, ua = hit
    return header, (ua or None)


def _earn_clearance(url: str) -> tuple[str | None, str | None]:
    """Launch Chrome once for this host to earn the wall's cookies."""
    host = _host(url)
    if host in _CLEARANCE_TRIED:
        return None, None
    _CLEARANCE_TRIED.add(host)
    try:
        from cf_clearance import ClearanceError, browser_allowed, forget, refresh
    except ImportError:
        return None, None
    if not browser_allowed():
        print(f"  [fetch] {host}: bot challenge; browser refresh disabled "
              f"(LNGCT_NO_BROWSER)", file=sys.stderr)
        return None, None
    forget(url)
    print(f"  [fetch] {host}: bot challenge — opening Chrome to clear it",
          file=sys.stderr)
    try:
        refresh([url])
    except ClearanceError as e:
        print(f"  [fetch] {host}: clearance failed: {e}", file=sys.stderr)
        return None, None
    return _clearance_cookie(url)


def fetch_page(url: str, *, timeout: int = 30, ua: str = CHROME_UA,
               headers: dict | None = None) -> Page:
    """
    Fetch `url` and return a Page. HTTP errors are reported in `status`
    ("404", "000" when curl couldn't connect), never raised — callers like the
    §3.8 gate turn them into (False, reason). Only a missing curl binary raises.

    `headers` are extra request headers (a host's JSON API may need them).
    Cloudflare walls are escalated automatically — see the block above _curl.

    The body lands in a private temp file that is always cleaned up. A fixed
    filename would let concurrent verifier runs (parallel subagents in one
    batch) overwrite each other's download — never reuse a shared path here.
    """
    require_curl()
    fd, tmp = tempfile.mkstemp(prefix="lngct_fetch_", suffix=".bin")
    os.close(fd)
    notes: list[str] = []
    status, content_type, final_url, raw = "000", "", "", b""
    host = _host(url)
    cookie, cookie_ua = _clearance_cookie(url)
    if cookie:
        ua = cookie_ua or ua          # the cookie is only honoured with its own UA
    try:
        if host in _IMPERSONATE_HOSTS:
            got = _cffi_get(url, timeout, ua, headers, cookie)
            if got and not _is_cf_wall(got[0], got[3]):
                status, content_type, final_url, raw = got
                notes.append("cf_impersonate")
            else:
                _IMPERSONATE_HOSTS.discard(host)     # the wall changed; run the full ladder
        if not notes:
            status, content_type, final_url, raw = _curl_attempts(
                url, tmp, timeout, ua, headers, cookie, notes)
            if _is_cf_wall(status, raw):
                # 1. TLS-fingerprint impersonation (no window, no cookie).
                got = _cffi_get(url, timeout, ua, headers, cookie)
                if got and not _is_cf_wall(got[0], got[3]):
                    status, content_type, final_url, raw = got
                    notes.append("cf_impersonate")
                    _IMPERSONATE_HOSTS.add(host)
                else:
                    # 2. JS challenge (Cloudflare or Imperva): earn its cookies with real Chrome.
                    cookie, cookie_ua = _earn_clearance(url)
                    if cookie:
                        status, content_type, final_url, raw = _curl_attempts(
                            url, tmp, timeout, cookie_ua or ua, headers, cookie, notes)
            if cookie and status != "000" and not _is_cf_wall(status, raw):
                notes.append("cf_clearance")     # the page behind the wall, whatever its status

        text, is_pdf = _extract(url, tmp, content_type, raw, notes)
        if is_pdf and not text.strip() and status == "200":
            # Large PDFs on slow hosts truncate often enough that one empty
            # extraction is not evidence of a missing text layer.
            notes.append("pdf_retry")
            status, content_type, final_url, raw = _curl_attempts(
                url, tmp, timeout, ua, headers, cookie, notes)
            text, is_pdf = _extract(url, tmp, content_type, raw, notes)
        return Page(status=status, text=text, content_type=content_type,
                    final_url=final_url, is_pdf=is_pdf, raw_len=len(raw), notes=notes)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _curl_attempts(url: str, tmp: str, timeout: int, ua: str | None,
                   headers: dict | None, cookie: str | None,
                   notes: list[str]) -> tuple[str, str, str, bytes]:
    """The curl retry ladder: browser UA; -k after an SSL failure; no UA after
    a transport failure / empty body. Returns (status, content_type, final_url, raw)."""
    status, content_type, final_url, raw = "000", "", "", b""
    attempts = [(ua, False)]
    while attempts:
        cur_ua, insecure = attempts.pop(0)
        try:
            result = _curl(url, tmp, timeout, cur_ua, insecure, headers, cookie)
        except subprocess.TimeoutExpired:
            return "000", "", "", b""
        parts = (result.stdout or "").split("\t")
        status = (parts[0].strip() if parts and parts[0].strip() else "000")
        content_type = parts[1].strip().lower() if len(parts) > 1 else ""
        final_url = parts[2].strip() if len(parts) > 2 else ""
        try:
            raw = Path(tmp).read_bytes()
        except OSError:
            raw = b""
        if result.returncode == 0 and (raw or status not in ("000", "")):
            if insecure:
                notes.append("insecure_tls")
            if cur_ua is None:
                notes.append("no_ua_retry")
            break
        err = (result.stderr or "").strip()
        if result.returncode in _CURL_SSL_EXITS and not insecure:
            attempts.append((cur_ua, True))
            continue
        if status in ("000", "") and cur_ua is not None:
            attempts.append((None, insecure))
            continue
        if err:
            # Surface the failure instead of silently treating it as an
            # empty page (the old behavior masked DNS/TLS errors).
            print(f"  [fetch] curl error for {url}: {err}", file=sys.stderr)
    return status, content_type, final_url, raw


def fetch_text(url: str, *, timeout: int = 30, ua: str = CHROME_UA,
               headers: dict | None = None) -> tuple[str, str]:
    """(http_status, body_text) — the simple form. See fetch_page for the rest."""
    p = fetch_page(url, timeout=timeout, ua=ua, headers=headers)
    return p.status, p.text


def page_title(body: str) -> str:
    """Extract the <title> text of an HTML body ("" if none)."""
    m = re.search(r"<title[^>]*>([^<]+)</title>", body, re.IGNORECASE)
    return m.group(1).strip() if m else ""


def main():
    """CLI: fetch one URL through the whole ladder and print status, notes, body."""
    import argparse
    p = argparse.ArgumentParser(
        description="Fetch a URL through the full escalation ladder (curl -> curl_cffi -> "
                    "Chrome clearance cookie) and print what came back.")
    p.add_argument("url")
    p.add_argument("--text", action="store_true", help="print the body (HTML or PDF text)")
    p.add_argument("--head", type=int, default=0, help="print only the first N body characters")
    p.add_argument("--timeout", type=int, default=30)
    args = p.parse_args()
    page = fetch_page(args.url, timeout=args.timeout)
    print(f"status: {page.status}  content-type: {page.content_type or '-'}  "
          f"bytes: {page.raw_len}  pdf: {page.is_pdf}")
    if page.final_url and page.final_url != args.url:
        print(f"final url: {page.final_url}")
    print(f"title: {page_title(page.text) or '-'}")
    print(f"notes: {', '.join(page.notes) or '-'}")
    if args.text or args.head:
        body = page.text[:args.head] if args.head else page.text
        print(body)


if __name__ == "__main__":
    main()
