"""
Pull the full status timeline for a UnitID from the read-only GEM Postgres.

WHY THIS EXISTS: The CSV export does NOT contain the full status timeline —
only the current status, substatus, and a flat set of anchor years. Per
lifecycle_rules.md "Anchor years vs timeline (the export gap)":

  Any status timeline change requires pulling the existing timeline first.
  The export alone cannot tell you whether a status transition was previously
  recorded as planned, the order of entries, per-entry notes, or data-entry
  timestamps. Working blind from the export risks duplicate entries, incorrect
  ordering, and lost methodology-required context.

PRIMARY PATH — read-only Postgres (default): the whole `status_timeline` table is
readable via GEM_READONLY_DB_URL (the same connection `gem_query.py` and
`refsweep_missing_year.py` use), joined unit→plant. This is exact SQL, not a
heuristic scrape, and needs no session cookies. USE THIS to pull the ordered
timeline before staging any status change. It is read-only — no live-DB writes.

  So there is NO reason to punt a status change to a qa note "because the timeline
  tool is down": the timeline is always readable here. Pull it, then stage the
  status change + the new timeline milestone properly. (This is exactly the
  Quynh Lap miss — construction was found but the status edit was deferred to a
  qa note on the false premise that the timeline was unreadable.)

LEGACY PATH — web-UI scraper (`--web`): the old scraper hit the GEM project-DB
edit page and heuristically parsed the HTML. Its default Heroku host is retired
(404), so it is off by default and kept only for the case where the read-only DB
is itself unreachable AND a live web host is supplied via GEM_PROJECT_DB_BASE_URL.
Parser is best-effort — verify against the live UI if you must use it.

Only if BOTH the read-only DB and any web host are unreachable does the qa-note
fallback apply (record the status change as a qa_review item, do not stage a blind
timeline edit) — and that should be rare, not the default.

Usage:
    python fetch_timeline.py G100002027401
    # Reads the timeline from the read-only Postgres (GEM_READONLY_DB_URL)

    python fetch_timeline.py G100002027401 --output work/timeline.json
    python fetch_timeline.py G100002027401 --web   # legacy scraper (needs a live host)
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

DB_ENV_VAR = "GEM_READONLY_DB_URL"
LNG_PROJECT_TYPE = 8


# The legacy Heroku host is known-stale (404 through the 2026-06 sweep — see the
# module docstring's KNOWN ISSUE). Override with GEM_PROJECT_DB_BASE_URL once the
# live host is confirmed; until then the endpoint is unreachable and status
# changes go to qa notes, not staged timeline edits.
DEFAULT_BASE_URL = os.environ.get(
    "GEM_PROJECT_DB_BASE_URL", "https://gem-project-db.herokuapp.com")
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
    tmp = os.path.join(tempfile.gettempdir(), "fetch_timeline.html")

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
        sys.exit(
            f"ERROR: HTTP {status} fetching {url}\n"
            f"  The GEM project-DB host may have moved (the legacy Heroku host is\n"
            f"  retired). Set GEM_PROJECT_DB_BASE_URL to the current host, or pass\n"
            f"  --base-url. FALLBACK if the endpoint is unreachable: do NOT block the\n"
            f"  batch — record the status change as a qa_review note and copy the\n"
            f"  timeline from the live UI by hand (see the module docstring)."
        )

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
    """Fetch and parse the timeline for a UnitID via the legacy web scraper."""
    html = _fetch_unit_page(unit_id, base_url=base_url)
    entries = parse_timeline(html)
    return {
        "unit_id": unit_id,
        "source": "web_scraper",
        "source_base_url": base_url,
        "entry_count": len(entries),
        "entries": entries,
        "_warning": None if entries else (
            "Parser returned no entries. Verify by viewing the unit page manually. "
            "If the unit DOES have a timeline, the page HTML structure may differ "
            "from this parser's heuristics — update parse_timeline() accordingly."
        ),
    }


# The single-unit timeline query. Mirrors refsweep_missing_year.py's EXTRACT_SQL
# join (status_timeline → powerplant_unit → plant), minus the year-is-null filter:
# here we want the WHOLE ordered timeline for one unit so a status change can be
# staged without duplicating/reordering entries. st."order" is the DB's per-unit
# sort key (tl_order — not a dense index; units may start at 0 or 1, with gaps).
_TIMELINE_SQL = """
select st.id                       as st_id,
       st."order"                  as tl_order,
       st.status                   as status,
       coalesce(st.substatus, '')  as sub_status,
       st.year                     as year,
       coalesce(st."monthOrHalfYear", '') as part_of_year,
       coalesce(st.notes, '')      as notes,
       p.name                      as terminal,
       coalesce(nullif(pu.name, ''), '(default)') as unit
from status_timeline st
join powerplant_unit pu on pu.id = st.unit_id
join plant p           on p.id  = pu.plant_id
where st.unit_id = :uid
  and coalesce(p.deleted, false)  = false
  and coalesce(pu.deleted, false) = false
order by st."order"
"""


def _pu_id(unit_id):
    """GEM UnitID (e.g. 'G100001065714') -> numeric powerplant_unit.id."""
    digits = re.sub(r"\D", "", str(unit_id))
    if not digits:
        sys.exit(f"ERROR: could not parse a numeric unit id from {unit_id!r}")
    return int(digits)


def fetch_timeline_db(unit_id):
    """Read the full ordered timeline for a UnitID from the read-only Postgres.

    This is the PRIMARY path — exact SQL, no scrape, no cookies. Read-only.
    """
    url = os.environ.get(DB_ENV_VAR)
    if not url:
        sys.exit(
            f"ERROR: {DB_ENV_VAR} not set — cannot read the timeline from the\n"
            f"  read-only Postgres. Set it (same URL as gem_query.py). To force the\n"
            f"  legacy web scraper instead, pass --web with a live GEM_PROJECT_DB_BASE_URL."
        )
    try:
        from sqlalchemy import create_engine, text
    except ImportError:
        sys.exit("error: pip install 'sqlalchemy>=2.0' psycopg2-binary")
    if url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url[len("postgres://"):]
    eng = create_engine(url)
    pu = _pu_id(unit_id)
    with eng.connect() as conn:
        rows = conn.execute(text(_TIMELINE_SQL), {"uid": pu}).mappings().all()
    entries = []
    for r in rows:
        entries.append({
            "tl_order": r["tl_order"],
            "status": r["status"],
            "sub_status": r["sub_status"],
            "year": r["year"],
            "part_of_year": r["part_of_year"],
            "notes": r["notes"],
            "_st_id": r["st_id"],
        })
    terminal = rows[0]["terminal"] if rows else None
    unit = rows[0]["unit"] if rows else None
    return {
        "unit_id": unit_id,
        "pu_id": pu,
        "terminal": terminal,
        "unit": unit,
        "source": "readonly_postgres",
        "entry_count": len(entries),
        "entries": entries,
        "_warning": None if entries else (
            f"No timeline rows for unit {unit_id} (pu_id {pu}). Either the unit id "
            f"is wrong, the unit/plant is deleted, or it genuinely has no timeline. "
            f"Confirm the UnitID against the fresh export before staging a status change."
        ),
    }


_STALE_HOST = "https://gem-project-db.herokuapp.com"

def main():
    p = argparse.ArgumentParser(
        description="Fetch a unit's full status timeline. Default: read-only Postgres "
                    "(GEM_READONLY_DB_URL). --web uses the legacy scraper.",
        epilog=("Default path reads the ordered timeline straight from the read-only "
                "Postgres — always available, so a status change is NEVER blocked for "
                "want of a timeline. Only if GEM_READONLY_DB_URL is unset AND the web "
                "host is dead does the qa-note fallback apply."))
    p.add_argument("unit_id", help="UnitID (e.g. G100002027401)")
    p.add_argument("--output", help="Write JSON to this path instead of stdout")
    p.add_argument("--web", action="store_true",
                   help="Use the legacy web-UI scraper instead of the read-only DB "
                        "(needs a live GEM_PROJECT_DB_BASE_URL; default host is 404).")
    p.add_argument("--base-url", default=DEFAULT_BASE_URL,
                   help=f"[--web only] Base URL (default: {DEFAULT_BASE_URL})")
    p.add_argument("--test", action="store_true",
                   help=f"[--web only] Use test database ({TEST_BASE_URL})")
    args = p.parse_args()

    if not args.web:
        result = fetch_timeline_db(args.unit_id)
    else:
        base_url = TEST_BASE_URL if args.test else args.base_url
        if base_url.rstrip("/") == _STALE_HOST:
            print("  WARNING: using the built-in default host, which is KNOWN STALE "
                  "(404). Set GEM_PROJECT_DB_BASE_URL or pass --base-url with the "
                  "live host — this request will almost certainly fail. The read-only "
                  "DB path (drop --web) does not have this problem.",
                  file=sys.stderr)
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
