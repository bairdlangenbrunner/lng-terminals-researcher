"""
URL verification harness for the LNG Terminals workflow.

Per Update SOP §7 / Discovery SOP §8 / Reconciliation SOP §3.9: every URL cited
in a [ref] cell or candidate row MUST be verified to (1) return HTTP 200,
AND (2) contain the entities/values it's cited for, AND (3) not be a
soft-error page (200 with "404"/"429"/Cloudflare interstitial in the title).

Ported from the carrier project's url_verifier.py with terminals-specific
soft-error patterns added (GIIGNL members-only redirects, EU PCI portal SSO,
etc.).

PDF sources (FERC orders, regulator filings, sponsor IR decks — a large share of
Tier 1 citations) are detected by content-type / `.pdf` path / `%PDF` magic and
run through `pdftotext -layout` before the content check, so a cited PDF is
verified for its expected strings just like an HTML page. This requires the
poppler `pdftotext` CLI (already a project dependency for the GIIGNL extractor).
A scanned/image PDF with no text layer (or a missing pdftotext) fails with a
clear reason rather than a misleading "missing expected content".

Two modes:
  - strict=True: raises CitationError on failure (use in build scripts where
    a broken URL is a hard error)
  - strict=False: returns (False, reason) — caller drops the URL silently

A per-process cache prevents re-fetching the same URL multiple times in one
build. Clear between builds.

CLI usage:
    python url_verifier.py <url> <expected1> [<expected2> ...]
    # exits 0 if URL passes, 1 if not

Library usage:
    from url_verifier import verify_url, verify_and_format
    ok, reason = verify_url("https://...", ["Cheniere", "Sabine Pass", "23 MTPA"])
    url_or_none = verify_and_format(url, expected)

Audit log (optional): set env URL_VERIFIER_LOG=<path> or pass --log <path> on the
CLI to append one JSONL line per check ({ts, url, expected, ok, reason}). This is
the durable record of which URLs were verified with which tokens — without it a
batch's verification evidence lives only in scrollback.

Bot-block ≠ dead (Wayback fallback): a 401/403/429 — or a 200 serving a
Cloudflare/paywall interstitial — means the page is LIVE but refusing bots, not
gone. Dropping such a citation was the Al Zour / gulf-turkiye miss class. When
the live fetch hits one of these, the verifier now falls back to the newest
Wayback Machine snapshot and runs the same content check against it; a pass
returns ok=True with a reason string naming the snapshot, so a bot-blocked but
value-verified URL is a PASSING citation (keep the live URL in the cell — never
cite the web.archive.org address). Disable with wayback_fallback=False /
--no-wayback.
"""
import json
import re
import os
import subprocess
import tempfile
import sys
import time
import urllib.parse


class CitationError(Exception):
    pass


_CACHE = {}

# A PDF whose text layer yields less than this many characters is treated as a
# scan and sent to OCR. Set above zero because image-only PDFs often still carry
# a few stray characters from stamps or form fields.
_PDF_TEXT_MIN = 200
# OCR is slow (~1-2 s/page); cap it. Regulator permits put the installation's
# equipment table in the first pages, so this is rarely binding in practice.
_OCR_MAX_PAGES = 25

# JSONL audit-log path; None = disabled. Set via URL_VERIFIER_LOG or --log.
_LOG_PATH = os.environ.get("URL_VERIFIER_LOG") or None


def set_log_path(path):
    """Enable/disable the JSONL audit log (None disables)."""
    global _LOG_PATH
    _LOG_PATH = path or None


def _log_check(url, expected, ok, reason):
    """Append one audit line; never let logging break verification."""
    if not _LOG_PATH:
        return
    try:
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "url": url,
            "expected": list(expected),
            "ok": ok,
            "reason": reason,
        }
        with open(_LOG_PATH, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except OSError as e:
        print(f"  WARNING: url_verifier log write failed ({e}); continuing", file=sys.stderr)

_DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Soft-error signals: HTTP 200 but title indicates an error / paywall / SSO template
_SOFT_ERROR_TITLES = (
    "404", "429", "503",
    "not found", "page not found",
    "too many requests",
    "access denied", "forbidden",
    "temporarily unavailable",
    "just a moment",         # Cloudflare interstitial
    "attention required",    # Cloudflare block
    "sign in",               # paywall / SSO
    "log in to continue",
    "subscribe to continue",
    "members only",          # GIIGNL members-only
    "login required",
    "this page is restricted",
)


def _run_pdftotext(path):
    """Extract text from a saved PDF via poppler's pdftotext. '' on any failure
    (missing binary, encrypted/scanned PDF with no text layer)."""
    try:
        r = subprocess.run(
            ["pdftotext", "-layout", path, "-"],
            capture_output=True, text=True, timeout=60,
        )
        if r.returncode == 0:
            return r.stdout
    except (FileNotFoundError, subprocess.SubprocessError):
        pass
    return ""


def _run_pdf_ocr(path, lang="fra+eng+ita+spa+deu"):
    """OCR a scanned/image-only PDF via poppler's pdftoppm + tesseract.

    Regulator filings are routinely published as scans with no text layer --
    French prefectural arretes especially (the Le Havre FSRU GHG permit that
    enumerates the Cape Ann's 4 dual-fuel engines is one). Without this the
    verifier FAILs them for want of any text at all, and a decisive primary
    source becomes uncitable.

    Only called when pdftotext returned (nearly) nothing, since OCR is slow.
    Capped at _OCR_MAX_PAGES; '' on any failure (either binary missing, etc).

    CAVEAT for token choice: OCR output is imperfect and its errors land
    exactly where the substring check is strictest -- accents and digits get
    mangled ("moteurs" -> "moteurs", "3x11,4" -> "8x114"). Prefer a long
    unaccented alphabetic token ("bicombustibles") over anything with an
    accent or a number in it.
    """
    try:
        with tempfile.TemporaryDirectory(prefix="verify_ocr_") as tmpdir:
            stem = os.path.join(tmpdir, "pg")
            r = subprocess.run(
                ["pdftoppm", "-r", "200", "-gray", "-png",
                 "-l", str(_OCR_MAX_PAGES), path, stem],
                capture_output=True, text=True, timeout=180,
            )
            if r.returncode != 0:
                return ""
            chunks = []
            for name in sorted(os.listdir(tmpdir)):
                if not name.endswith(".png"):
                    continue
                img = os.path.join(tmpdir, name)
                t = subprocess.run(
                    ["tesseract", img, "stdout", "-l", lang, "--psm", "6"],
                    capture_output=True, text=True, timeout=120,
                )
                if t.returncode == 0 and t.stdout.strip():
                    chunks.append(t.stdout)
            return "\n".join(chunks)
    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        return ""


def _run_unzip_text(path):
    """Some regulator portals (e.g. Italy's va.mite.gov.it AIA/VIA dossiers)
    serve a whole filing as a single ZIP bundle of PDFs at what looks like a
    single-document URL. Extract every member, pdftotext any PDFs (and decode
    any plain-text members), and concatenate -- so a value buried in one PDF
    inside the bundle is still verifiable against the bundle's own URL.
    '' on any failure (not a real zip, unzip missing, nothing extractable)."""
    try:
        with tempfile.TemporaryDirectory(prefix="verify_zip_") as tmpdir:
            r = subprocess.run(
                ["unzip", "-o", "-qq", path, "-d", tmpdir],
                capture_output=True, text=True, timeout=60,
            )
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
                        text = _run_pdftotext(fpath)
                    elif name.lower().endswith((".txt", ".csv", ".xml", ".html", ".htm")):
                        try:
                            with open(fpath, "rb") as f:
                                text = f.read().decode("utf-8", errors="replace")
                        except OSError:
                            text = ""
                    else:
                        continue
                    if text.strip():
                        chunks.append(text)
            return "\n".join(chunks)
    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        return ""


def _fetch(url, timeout=30, ua=_DEFAULT_UA):
    """Fetch URL, return (status_code, body_text, is_pdf). Cached per URL per
    process. PDF bodies are run through pdftotext so the content check sees text,
    not raw binary; is_pdf lets verify_url skip the HTML-only title check."""
    if url in _CACHE:
        return _CACHE[url]

    # Unique per invocation: a fixed filename lets concurrent verifier runs
    # (parallel subagents in one batch) overwrite each other's download, which
    # silently produces false FAILs -- or worse, a PASS against another URL's
    # content. Never reuse a shared path here.
    fd, tmp = tempfile.mkstemp(prefix="verify_page_", suffix=".bin")
    os.close(fd)
    try:
        # --compressed: some CDNs return a gzip/br body regardless of the request
        # headers. Without this, the body decodes to binary garbage and the content
        # check FAILs on a page that plainly contains the value (atlanticlng.com).
        # Two attempts: large PDFs on slow hosts (iaac-aeic.gc.ca) truncate often
        # enough that a single empty extraction is not evidence of missing content.
        # Attempt 3 retries WITHOUT the browser User-Agent. This is the inverse of
        # the usual bot-block: a few government hosts abort the connection outright
        # when sent a Chrome UA ("HTTP2 framing layer" / "empty reply from server",
        # curl status 000) and serve the file perfectly to curl's own default UA.
        # The French prefecture sites do this -- seine-maritime.gouv.fr and
        # bouches-du-rhone.gouv.fr, which between them hold the Le Havre FSRU and
        # Fos Cavaou permits. Without this retry both read as dead and a decisive
        # primary source gets dropped as a failed citation.
        for attempt in (1, 2, 3):
            cmd = ["curl", "-sL", "--compressed", "-o", tmp,
                   "-w", "%{http_code} %{content_type}", "--max-time", str(timeout)]
            if attempt < 3:
                cmd += ["-A", ua]
            result = subprocess.run(
                cmd + [url],
                capture_output=True, text=True, timeout=timeout + 5,
            )
            parts = result.stdout.strip().split()
            status = parts[0] if parts else "000"
            content_type = " ".join(parts[1:]).lower()

            try:
                with open(tmp, "rb") as f:
                    raw = f.read()
            except Exception:
                raw = b""

            is_zip = (
                "zip" in content_type
                or url.split("?")[0].lower().endswith(".zip")
                or raw[:4] == b"PK\x03\x04"
            )
            is_pdf = (
                not is_zip
                and (
                    "pdf" in content_type
                    or url.split("?")[0].lower().endswith(".pdf")
                    or raw[:5] == b"%PDF-"
                )
            )
            if is_zip:
                text = _run_unzip_text(tmp)
                # Reuse the PDF path downstream: no HTML <title> to soft-error
                # check, and an empty result means "no extractable text" same
                # as a scanned/image-only PDF.
                is_pdf = True
            elif is_pdf:
                text = _run_pdftotext(tmp)
                # No text layer -> scanned image. OCR rather than call it empty.
                if len(text.strip()) < _PDF_TEXT_MIN and raw[:5] == b"%PDF-":
                    text = _run_pdf_ocr(tmp) or text
            else:
                text = raw.decode("utf-8", errors="replace")

            if text.strip() or attempt == 3:
                break
            # A real 4xx/5xx is an answer, not a transport failure -- only the
            # 000-class (connection aborted) is worth the HTTP/1.0 downgrade.
            if attempt == 2 and status != "000":
                break
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass

    _CACHE[url] = (status, text, is_pdf)
    return status, text, is_pdf


# Live-fetch outcomes that mean "bot-blocked, page presumptively live" — these
# route to the Wayback fallback instead of a hard fail.
_BOT_BLOCK_STATUSES = ("401", "403", "429")
_BOT_BLOCK_TITLES = (
    "just a moment", "attention required", "access denied", "forbidden",
    "too many requests",
)


def _wayback_snapshot(url):
    """Newest Wayback snapshot for `url` via the availability API.
    Returns (snapshot_url, timestamp) or (None, None). Cached per process."""
    key = ("__wayback__", url)
    if key in _CACHE:
        return _CACHE[key]
    api = ("https://archive.org/wayback/available?url="
           + urllib.parse.quote(url, safe=""))
    snap = (None, None)
    try:
        r = subprocess.run(
            ["curl", "-sL", "-A", _DEFAULT_UA, "--max-time", "30", api],
            capture_output=True, text=True, timeout=35,
        )
        data = json.loads(r.stdout or "{}")
        closest = (data.get("archived_snapshots") or {}).get("closest") or {}
        if closest.get("available") and closest.get("url"):
            # Force https; the API often returns http:// snapshot URLs.
            u = closest["url"].replace("http://web.archive.org",
                                       "https://web.archive.org", 1)
            snap = (u, closest.get("timestamp", ""))
    except (subprocess.SubprocessError, ValueError):
        pass
    _CACHE[key] = snap
    return snap


_WS_RE = re.compile(r"\s+")


def _norm(s):
    """Lowercase and collapse every whitespace run to one space.

    PDF extraction wraps lines mid-phrase, so a token that IS present verbatim
    ('electric drive is the preferred alternative') fails a raw substring match
    purely because pdftotext put a newline inside it -- a false FAIL on exactly
    the regulatory PDFs the SOP prefers as primary sources. Normalising both
    haystack and needle kills that class without loosening the match otherwise.
    """
    return _WS_RE.sub(" ", s).lower()


def _check_wayback(url, expected, require_all, live_reason):
    """Bot-block fallback: run the content check against the newest Wayback
    snapshot. Returns (ok, reason); ok=True means the LIVE url stays citable."""
    snap_url, ts = _wayback_snapshot(url)
    if not snap_url:
        return False, f"{live_reason}; no Wayback snapshot to verify against"
    status, text, _is_pdf = _fetch(snap_url)
    if status != "200":
        return False, f"{live_reason}; Wayback snapshot fetch failed (HTTP {status})"
    text_lower = _norm(text)
    missing = [s for s in expected if _norm(s) not in text_lower]
    found = [s for s in expected if _norm(s) in text_lower]
    if (require_all and missing) or (not require_all and not found):
        return False, (f"{live_reason}; Wayback snapshot {ts} missing expected "
                       f"content: {missing if require_all else expected}")
    return True, (f"bot-blocked live ({live_reason}); value verified via "
                  f"Wayback snapshot {ts}")


def verify_url(url, expected, strict=False, require_all=True, wayback_fallback=True):
    """Verify URL passes three checks:
      1. HTTP 200
      2. Not a soft-error page
      3. Body contains the strings in `expected` (case-insensitive)

    A bot-blocked live page (401/403/429, or a 200 Cloudflare/paywall
    interstitial) is NOT treated as dead when wayback_fallback is on: the same
    content check runs against the newest Wayback snapshot, and a pass counts
    as verification of the live URL (bot-block ≠ dead).

    Args:
      url: the URL to verify
      expected: list of substrings that must appear in the page body.
                For terminals: typically [TerminalName, Owner, value-being-cited]
      strict: raise CitationError on failure instead of returning False
      require_all: every expected substring must be present (default True)
      wayback_fallback: on bot-block, verify against the newest Wayback snapshot

    Returns: (ok: bool, reason: str)
    """
    ok, reason = _check(url, expected, require_all, wayback_fallback)
    _log_check(url, expected, ok, reason)
    if not ok and strict:
        raise CitationError(f"URL failed verification ({reason}): {url}")
    return ok, reason


def _check(url, expected, require_all, wayback_fallback=True):
    """The three checks; returns (ok, reason) with no side effects."""
    status, text, is_pdf = _fetch(url)

    if status != "200":
        if wayback_fallback and status in _BOT_BLOCK_STATUSES:
            return _check_wayback(url, expected, require_all, f"HTTP {status}")
        return False, f"HTTP {status}"

    if is_pdf:
        # No HTML <title> to soft-error-check; require a usable text layer instead.
        if not text.strip():
            return False, ("PDF has no extractable text (scanned/image PDF, or the "
                           "poppler pdftotext CLI is unavailable)")
    else:
        # Soft-error detection via title (HTML only)
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", text, re.IGNORECASE)
        if title_match:
            title = title_match.group(1).lower()
            for bad in _SOFT_ERROR_TITLES:
                if bad in title:
                    reason = f"soft-error page (title: {title_match.group(1).strip()!r})"
                    if wayback_fallback and any(b in title for b in _BOT_BLOCK_TITLES):
                        # Bot-wall/paywall interstitial served as 200 — same
                        # bot-block ≠ dead treatment as a 401/403.
                        return _check_wayback(url, expected, require_all, reason)
                    return False, reason

    # Content check
    text_lower = _norm(text)
    found = [s for s in expected if _norm(s) in text_lower]
    missing = [s for s in expected if _norm(s) not in text_lower]

    if require_all and missing:
        return False, f"missing expected content: {missing}"
    if not require_all and not found:
        return False, f"none of expected content found: {expected}"

    return True, "OK"


def verify_and_format(url, expected):
    """Verify a URL. If it passes, return the URL. If not, return None.
    Logs the failure reason to stderr.
    """
    ok, reason = verify_url(url, expected, strict=False)
    if ok:
        return url
    print(f"  [CITATION DROPPED] {url}\n    reason: {reason}", file=sys.stderr)
    return None


def clear_cache():
    """Clear the in-memory cache. Call between builds."""
    _CACHE.clear()


def main():
    argv = sys.argv[1:]
    if "--log" in argv:
        i = argv.index("--log")
        try:
            set_log_path(argv[i + 1])
        except IndexError:
            print("Usage: python url_verifier.py [--log <path>] [--no-wayback] <url> [<expected1> ...]")
            sys.exit(2)
        del argv[i:i + 2]
    wayback = True
    if "--no-wayback" in argv:
        wayback = False
        argv.remove("--no-wayback")
    if len(argv) < 1:
        print("Usage: python url_verifier.py [--log <path>] [--no-wayback] <url> [<expected1> <expected2> ...]")
        sys.exit(2)
    url = argv[0]
    expected = argv[1:]
    ok, reason = verify_url(url, expected, strict=False, require_all=True,
                            wayback_fallback=wayback)
    print(f"  URL: {url}")
    print(f"  Expected: {expected}")
    print(f"  Result: {'PASS' if ok else 'FAIL'}  ({reason})")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
