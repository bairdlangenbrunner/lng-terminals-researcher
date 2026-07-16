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
"""
import json
import re
import os
import subprocess
import tempfile
import sys
import time


class CitationError(Exception):
    pass


_CACHE = {}

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


def _fetch(url, timeout=30, ua=_DEFAULT_UA):
    """Fetch URL, return (status_code, body_text, is_pdf). Cached per URL per
    process. PDF bodies are run through pdftotext so the content check sees text,
    not raw binary; is_pdf lets verify_url skip the HTML-only title check."""
    if url in _CACHE:
        return _CACHE[url]

    tmp = os.path.join(tempfile.gettempdir(), "verify_page.bin")
    result = subprocess.run(
        ["curl", "-sL", "-A", ua, "-o", tmp,
         "-w", "%{http_code} %{content_type}", "--max-time", str(timeout), url],
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

    is_pdf = (
        "pdf" in content_type
        or url.split("?")[0].lower().endswith(".pdf")
        or raw[:5] == b"%PDF-"
    )
    if is_pdf:
        text = _run_pdftotext(tmp)
    else:
        text = raw.decode("utf-8", errors="replace")

    _CACHE[url] = (status, text, is_pdf)
    return status, text, is_pdf


def verify_url(url, expected, strict=False, require_all=True):
    """Verify URL passes three checks:
      1. HTTP 200
      2. Not a soft-error page
      3. Body contains the strings in `expected` (case-insensitive)
    
    Args:
      url: the URL to verify
      expected: list of substrings that must appear in the page body.
                For terminals: typically [TerminalName, Owner, value-being-cited]
      strict: raise CitationError on failure instead of returning False
      require_all: every expected substring must be present (default True)
    
    Returns: (ok: bool, reason: str)
    """
    ok, reason = _check(url, expected, require_all)
    _log_check(url, expected, ok, reason)
    if not ok and strict:
        raise CitationError(f"URL failed verification ({reason}): {url}")
    return ok, reason


def _check(url, expected, require_all):
    """The three checks; returns (ok, reason) with no side effects."""
    status, text, is_pdf = _fetch(url)

    if status != "200":
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
                    return False, f"soft-error page (title: {title_match.group(1).strip()!r})"

    # Content check
    text_lower = text.lower()
    found = [s for s in expected if s.lower() in text_lower]
    missing = [s for s in expected if s.lower() not in text_lower]

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
            print("Usage: python url_verifier.py [--log <path>] <url> [<expected1> ...]")
            sys.exit(2)
        del argv[i:i + 2]
    if len(argv) < 1:
        print("Usage: python url_verifier.py [--log <path>] <url> [<expected1> <expected2> ...]")
        sys.exit(2)
    url = argv[0]
    expected = argv[1:]
    ok, reason = verify_url(url, expected, strict=False, require_all=True)
    print(f"  URL: {url}")
    print(f"  Expected: {expected}")
    print(f"  Result: {'PASS' if ok else 'FAIL'}  ({reason})")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
