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

The whole `status_timeline` table is readable via GEM_READONLY_DB_URL (the same
connection `../gem-db-ops/gem_query.py` and `refsweep_missing_year.py` use), joined
unit→plant. This is exact SQL, not a heuristic scrape, and needs no session
cookies. USE THIS to pull the ordered timeline before staging any status
change. It is read-only — no live-DB writes.

  So there is NO reason to punt a status change to a qa note "because the
  timeline tool is down": the timeline is always readable here. Pull it, then
  stage the status change + the new timeline milestone properly. (This is
  exactly the Quynh Lap miss — construction was found but the status edit was
  deferred to a qa note on the false premise that the timeline was unreadable.)

If the read-only DB itself is unreachable (GEM_READONLY_DB_URL unset or the
connection fails), ESCALATE TO THE USER — don't stage a blind timeline edit,
and don't quietly punt to a qa note without flagging the outage. (A legacy
web-UI scraper used to live here as a fallback; its Heroku host is retired and
the scraper was removed 2026-07 — see git history if it's ever needed again.)

Usage:
    python fetch_timeline.py G100002027401
    python fetch_timeline.py G100002027401 --output work/timeline.json
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

DB_ENV_VAR = "GEM_READONLY_DB_URL"
LNG_PROJECT_TYPE = 8


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
    """Read the full ordered timeline for a UnitID from the read-only Postgres."""
    url = os.environ.get(DB_ENV_VAR)
    if not url:
        sys.exit(
            f"ERROR: {DB_ENV_VAR} not set — cannot read the timeline from the\n"
            f"  read-only Postgres. Set it (same URL as the gem-db-ops pulls). If the\n"
            f"  read-only DB is genuinely unreachable, escalate to the user before\n"
            f"  staging any status change (see the module docstring)."
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


def main():
    p = argparse.ArgumentParser(
        description="Fetch a unit's full status timeline from the read-only "
                    "Postgres (GEM_READONLY_DB_URL).",
        epilog=("Reads the ordered timeline straight from the read-only Postgres — "
                "always available, so a status change is NEVER blocked for want of "
                "a timeline. If the DB is unreachable, escalate to the user."))
    p.add_argument("unit_id", help="UnitID (e.g. G100002027401)")
    p.add_argument("--output", help="Write JSON to this path instead of stdout")
    args = p.parse_args()

    result = fetch_timeline_db(args.unit_id)

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
