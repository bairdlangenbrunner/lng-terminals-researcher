#!/usr/bin/env python3
"""Who last changed each LNG terminal's location — from plant_history, not the export.

Companion to `location_accuracy_audit.py`. That script splits approximate
terminals by the export's `LastUpdated`/`Researcher` columns, but **those two
columns do not track coordinate edits**: they only move when a researcher
explicitly marks a unit "updated". A pass that fixes 60 terminals' coordinates
without adding new unit data leaves almost no trace in them (2026-08-07: a
three-day location pass touched 62 LNG plants but bumped only 11 unit rows).

So for the question "who last touched this terminal's location, and did person
X's pass cover it?", read the real audit log instead:

    plant_history(plant_id, editor_id, modified, plantJSON)

We walk each LNG plant's snapshots in time order and record the last revision
where (latitude, longitude, locationAccuracy) actually changed. That editor is
the provenance of the coordinates now in the database.

    python location_edit_provenance.py                      # all non-exact terminals
    python location_edit_provenance.py --editor Baird       # who last set location
    python location_edit_provenance.py --status operating construction
    python location_edit_provenance.py --touched-since 2026-08-01 --editor Natalia
    python location_edit_provenance.py --all                # include exact ones

Read-only: `GEM_READONLY_DB_URL` plus the fresh `gem_export.csv` for status.

Caveat: 14 LNG terminals carry `plantLevelLocation = false`, so their
coordinates live on the unit rows and the plant-level fields are NULL. They are
reported with `unit_level` in the `note` column — the plant-level history says
nothing about them, and provenance shows as `NO HISTORY`.
"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import paths  # noqa: E402  — GEM DB engine + sibling-repo resolution

PROJECT_URL = "https://gem-project-db.herokuapp.com/projects/edit/{}"

# most-built first: a terminal is reported under its most-built unit status
STATUS_RANK = [
    "operating", "mothballed", "idled", "retired",
    "construction", "proposed", "shelved", "cancelled",
]

# legacy crude/NGL deepwater-port records share the table but are out of LNG scope
LNG_FUELS = {"", "lng", "gas", "natural gas"}


def engine():
    """Read-only engine built by ../gem-db-ops (via paths.py) — the one place
    the connection, its read-only guard and the URL fixup are defined."""
    return paths.get_engine()


def _norm(value):
    """Compare coordinates numerically so 5.10 and 5.1 aren't a spurious edit."""
    if value in (None, ""):
        return None
    try:
        return round(float(value), 6)
    except (TypeError, ValueError):
        return str(value).strip()


def _loc_key(lat, lon, acc):
    return (_norm(lat), _norm(lon), (acc or "").strip().lower() or None)


def fetch(eng):
    """Location provenance + current plant state, keyed by plant id."""
    from sqlalchemy import text

    with eng.connect() as conn:
        users = {
            r[0]: (f"{r[1] or ''} {r[2] or ''}".strip() or r[3])
            for r in conn.execute(text(
                "select id, first_name, last_name, username from auth_user"))
        }
        history = defaultdict(list)
        for r in conn.execute(text("""
            select h.plant_id, h.editor_id, h.modified,
                   h."plantJSON"->>'latitude',
                   h."plantJSON"->>'longitude',
                   h."plantJSON"->>'locationAccuracy'
              from plant_history h
              join plant p on p.id = h.plant_id
             where p."projectType" = 8 and h."plantJSON" is not null
             order by h.plant_id, h.modified
        """)):
            history[r[0]].append(tuple(r[1:]))

        current = {
            r[0]: {"name": r[1], "notes": r[2] or "", "unit_level": not r[3]}
            for r in conn.execute(text("""
                select id, name, notes, "plantLevelLocation"
                  from plant where "projectType" = 8 and deleted = false
            """))
        }

    provenance = {}
    for pid, revisions in history.items():
        prev, last = None, None
        for editor, modified, lat, lon, acc in revisions:
            key = _loc_key(lat, lon, acc)
            if prev is None:
                if any(v is not None for v in key):
                    last = (modified, editor)
            elif key != prev:
                last = (modified, editor)
            prev = key
        provenance[pid] = last

    # every edit each person made, for "did their pass cover this terminal?"
    edits = defaultdict(list)
    for pid, revisions in history.items():
        for editor, modified, *_ in revisions:
            edits[pid].append((str(modified)[:10], editor))

    return users, provenance, edits, current


def rollup(csv_path):
    """Terminal-level status/accuracy from the unit-row export."""
    with open(csv_path, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        sys.exit(f"no rows in {csv_path}")

    by_terminal = defaultdict(list)
    for r in rows:
        by_terminal[r["TerminalID"]].append(r)

    out = {}
    for tid, group in by_terminal.items():
        statuses = [r["Status"].strip().lower() for r in group]
        accs = {r["Accuracy"].strip().lower() for r in group}
        fuels = {r["Fuel"].strip().lower() for r in group}
        out[int(tid.lstrip("T"))] = {
            "terminal_id": tid,
            "name": group[0]["TerminalName"],
            "country": group[0]["Country/Area"],
            "status": next((s for s in STATUS_RANK if s in statuses),
                           statuses[0] if statuses else ""),
            # coarsest wins; a mixed project is usually a proposed sibling unit
            "accuracy": "approximate" if "approximate" in accs else (
                next(iter(sorted(a for a in accs if a)), "")),
            "mixed": len(accs) > 1,
            "latitude": group[0]["Latitude"],
            "longitude": group[0]["Longitude"],
            "offscope": bool(fuels) and not (fuels & LNG_FUELS),
            "n_units": len(group),
        }
    return len(rows), out


def dp(value):
    """Effective decimal places — trailing zeros are not precision."""
    value = (value or "").strip()
    if "." not in value:
        return 0 if value else None
    return len(value.rsplit(".", 1)[1].rstrip("0"))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", default="gem_export.csv", help="fresh unit-row export")
    ap.add_argument("--editor", help="only terminals whose location this person set "
                                     "(substring, case-insensitive)")
    ap.add_argument("--status", nargs="*", help=f"filter status ({', '.join(STATUS_RANK)})")
    ap.add_argument("--touched-since", metavar="YYYY-MM-DD",
                    help="add a column: did --touched-by edit this plant since this date")
    ap.add_argument("--touched-by", help="person for --touched-since (default: --editor)")
    ap.add_argument("--all", action="store_true", help="include accuracy = exact")
    ap.add_argument("--include-offscope", action="store_true",
                    help="include legacy oil/NGL deepwater-port records")
    ap.add_argument("--out", help="write CSV here as well as printing")
    args = ap.parse_args()

    n_units, terminals = rollup(args.csv)
    users, provenance, edits, current = fetch(engine())

    def who(pid):
        p = provenance.get(pid)
        return (users.get(p[1], f"user {p[1]}"), str(p[0])[:10]) if p else ("NO HISTORY", "")

    touch_name = (args.touched_by or args.editor or "").lower()

    rows = []
    for pid, t in terminals.items():
        if not args.all and t["accuracy"] == "exact":
            continue
        if t["offscope"] and not args.include_offscope:
            continue
        if args.status and t["status"] not in args.status:
            continue
        editor, when = who(pid)
        if args.editor and args.editor.lower() not in editor.lower():
            continue

        touched = ""
        if args.touched_since and touch_name:
            days = sorted({d for d, ed in edits.get(pid, [])
                           if d >= args.touched_since
                           and touch_name in users.get(ed, "").lower()})
            touched = days[-1] if days else "no"

        cur = current.get(pid, {})
        notes = []
        if t["mixed"]:
            notes.append("mixed")

        if cur.get("unit_level"):
            notes.append("unit_level")
        precision = min([d for d in (dp(t["latitude"]), dp(t["longitude"]))
                         if d is not None], default=None)
        if precision is not None and precision <= 2 and t["accuracy"] == "exact":
            notes.append(f"COARSE({precision}dp)")
        if t["offscope"]:
            notes.append("off-scope-fuel")

        rows.append({
            "status": t["status"], "country": t["country"], "terminal": t["name"],
            "terminal_id": t["terminal_id"], "accuracy": t["accuracy"] or "BLANK",
            "latitude": t["latitude"], "longitude": t["longitude"],
            "precision_dp": "" if precision is None else precision,
            "last_location_editor": editor, "last_location_edit": when,
            "touched": touched, "note": " ".join(notes),
            "project_url": PROJECT_URL.format(t["terminal_id"].lstrip("T")),
        })

    rows.sort(key=lambda r: (STATUS_RANK.index(r["status"]) if r["status"] in STATUS_RANK
                             else 99, r["country"], r["terminal"]))

    label = f" last set by {args.editor}" if args.editor else ""
    scope = "all" if args.all else "non-exact"
    print(f"{len(rows)} {scope} terminals{label}   "
          f"({n_units} unit rows -> {len(terminals)} terminals)\n")
    head = f"{'status':13s} {'country':16s} {'terminal':40s} {'acc':11s} {'last location edit':32s}"
    if args.touched_since:
        head += f" {'touched':10s}"
    print(head + " note")
    print("-" * (len(head) + 20))
    for r in rows:
        line = (f"{r['status']:13s} {r['country'][:16]:16s} {r['terminal'][:40]:40s} "
                f"{r['accuracy'][:11]:11s} "
                f"{r['last_location_editor'][:20] + ' ' + r['last_location_edit']:32s}")
        if args.touched_since:
            line += f" {r['touched']:10s}"
        print(line + " " + r["note"])

    if args.out:
        with open(args.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["status"])
            w.writeheader()
            w.writerows(rows)
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
