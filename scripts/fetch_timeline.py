"""
Pull the full status timeline for a UnitID from the live GEM database web UI.

WHY THIS EXISTS: The CSV export does NOT contain the full status timeline —
only the current status, substatus, and a flat set of anchor years. Per
lifecycle_rules.md "Anchor years vs timeline (the export gap)":

  Any status timeline change requires pulling the existing timeline first.
  The export alone cannot tell you whether a status transition was previously
  recorded as planned, the order of entries, per-entry notes, or data-entry
  timestamps. Working blind from the export risks duplicate entries, incorrect
  ordering, and lost methodology-required context.

This script scrapes the unit edit page from the GEM project DB web UI.

IMPORTANT CAVEAT: This script is best-effort. The exact HTML structure of the
GEM unit edit page is not documented in this codebase; the parser below uses
heuristics. **Verify the parsed output against the live UI for at least one
unit per batch** before trusting it for many units.

If the parser fails or returns empty, the fallback is to manually view the unit
page in the browser and copy the timeline into the staging xlsx.

Usage:
    python fetch_timeline.py G100002027401
    # Prints the parsed timeline for that UnitID

    python fetch_timeline.py G100002027401 --output /tmp/timeline.json
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path


DEFAULT_BASE_URL = "https://gem-project-db.herokuapp.com"
TEST_BASE_URL = "https://testdata-gem-project-db-fc139ddfae43.herokuapp.com"

_DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _check_env():
    """Verify the same auth env vars as pull_gem_db.py."""
    missing = []
    for var in ("GEM_PROJECT_DB_SESSIONID", "GEM_PROJECT_DB_CSRFTOKEN"):
        if not os.environ.get(var):
            missing.append(var)
    if missing:
        sys.exit(
            f"ERROR: missing env var(s): {', '.join(missing)}\n"
            f"  See gem_export_via_web.py for the cookie extraction procedure."
        )


def _fetch_unit_page(unit_id, base_url=DEFAULT_BASE_URL, timeout=30):
    """curl the unit edit page using the session cookies."""
    _check_env()
    sid = os.environ["GEM_PROJECT_DB_SESSIONID"]
    csrf = os.environ["GEM_PROJECT_DB_CSRFTOKEN"]
    host = urllib.parse.urlparse(base_url).hostname
    # The unit detail URL — pattern based on observed GEM URL structure
    url = f"{base_url}/units/{unit_id}/"
    tmp = "/tmp/fetch_timeline.html"

    cookie = f"sessionid={sid}; csrftoken={csrf}"
    result = subprocess.run(
        ["curl", "-sL", "-A", _DEFAULT_UA,
         "-H", f"Cookie: {cookie}",
         "-o", tmp,
         "-w", "%{http_code}",
         "--max-time", str(timeout),
         url],
        capture_output=True, text=True, timeout=timeout + 5,
    )
    status = result.stdout.strip() or "000"

    if status == "302" or status == "301":
        sys.exit(
            f"ERROR: unit page redirected (status {status}). "
            f"Session cookie likely expired — re-export GEM_PROJECT_DB_SESSIONID."
        )
    if status != "200":
        sys.exit(f"ERROR: HTTP {status} fetching {url}")

    with open(tmp, encoding="utf-8", errors="replace") as f:
        return f.read()


def parse_timeline(html):
    """Heuristic parser for the timeline section of a unit edit page.
    
    Returns list of timeline entry dicts. Each entry has:
      - status (str)
      - sub_status (str)
      - year (str)
      - part_of_year (str)
      - notes (str)
      - source_url (str, optional)
    
    HEURISTIC: The page is assumed to render the timeline as a series of form
    rows or list items. The exact structure depends on GEM's UI implementation,
    which is not documented in this codebase.
    
    This parser uses pattern-matching on common HTML structures. If it returns
    nothing for a unit that should have a timeline, the structure differs from
    expectations and you should:
      1. View the unit page source manually
      2. Identify the actual HTML pattern
      3. Update this parser
    
    For initial batches, treat parser output as advisory — verify against the
    live UI for at least one unit before trusting.
    """
    entries = []

    # Pattern 1: look for table rows with status-like content
    # Common pattern in Django-admin-style forms:
    #   <tr><td>status</td><td>year</td><td>substatus</td>...</tr>
    statuses = "proposed|construction|operating|idled|mothballed|retired|shelved|cancelled|FID"
    substatuses = "actual|planned|confirmed|inferred 2 y|inferred 4 y"

    # Try to match in form fields
    # GEM likely uses Django form inlines like name="form-N-status"
    form_pattern = re.compile(
        r'name="(?:[^"]*-)?(\d+)-status"[^>]*value="(' + statuses + r')"',
        re.IGNORECASE
    )
    matches = form_pattern.findall(html)
    if matches:
        # Group by form index, then re-scan for each field
        form_indices = sorted(set(int(idx) for idx, _ in matches))
        for idx in form_indices:
            entry = {"_form_index": idx}
            for field in ("status", "sub_status", "year", "part_of_year", "notes"):
                fp = re.compile(
                    rf'name="(?:[^"]*-)?{idx}-{field}"[^>]*value="([^"]*)"',
                    re.IGNORECASE
                )
                m = fp.search(html)
                if m:
                    entry[field] = m.group(1)
            entries.append(entry)
        return entries

    # Pattern 2: timeline rendered as a non-form display (read-only view)
    # Look for blocks containing both a status and a year
    block_pattern = re.compile(
        rf'\b({statuses})\b[^<>]*?\b({substatuses}|\(planned\)|\(actual\))?\b[^<>]*?\b(19\d{{2}}|20\d{{2}})\b',
        re.IGNORECASE
    )
    for m in block_pattern.finditer(html):
        entries.append({
            "status": m.group(1).lower(),
            "sub_status": (m.group(2) or "").lower(),
            "year": m.group(3),
            "notes": "",
            "_pattern": "block_match",
        })

    return entries


def fetch_timeline(unit_id, base_url=DEFAULT_BASE_URL):
    """Fetch and parse the timeline for a UnitID."""
    html = _fetch_unit_page(unit_id, base_url=base_url)
    entries = parse_timeline(html)
    return {
        "unit_id": unit_id,
        "source_base_url": base_url,
        "entry_count": len(entries),
        "entries": entries,
        "_warning": None if entries else (
            "Parser returned no entries. Verify by viewing the unit page manually. "
            "If the unit DOES have a timeline, the page HTML structure may differ "
            "from this parser's heuristics — update parse_timeline() accordingly."
        ),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("unit_id", help="UnitID (e.g. G100002027401)")
    p.add_argument("--output", help="Write JSON to this path instead of stdout")
    p.add_argument("--base-url", default=DEFAULT_BASE_URL,
                   help=f"Base URL (default: {DEFAULT_BASE_URL})")
    p.add_argument("--test", action="store_true",
                   help=f"Use test database ({TEST_BASE_URL})")
    args = p.parse_args()

    base_url = TEST_BASE_URL if args.test else args.base_url
    result = fetch_timeline(args.unit_id, base_url=base_url)

    if args.output:
        Path(args.output).write_text(json.dumps(result, indent=2, default=str))
        print(f"  Wrote timeline to {args.output} ({result['entry_count']} entries)", file=sys.stderr)
    else:
        print(json.dumps(result, indent=2, default=str))

    if result["_warning"]:
        print(f"\n  WARNING: {result['_warning']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
