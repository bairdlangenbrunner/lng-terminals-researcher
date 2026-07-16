"""
coverage_status.py — the coverage ledger: when was each country last
researched, and by which workflow?

Reads every batches/staging/**/meta.json sidecar (one per staging directory,
maintained alongside each batch — see batches/staging/README.md) and
aggregates them into a per-country freshness table. Exists because this used
to live only in prose (run_records/*.md, SWEEP_PROGRESS.md), which already
caused a live near-duplicate: a batch re-researching countries an earlier
sweep had already covered.

meta.json shape:
    {"scope_slug": "levant-iraq", "workflow": "update+discovery",
     "tier": "exhaustive", "countries": ["Iraq", "Jordan"],
     "areas": ["Louisiana"],   # captive_power only
     "started": "2026-07-16", "built": "2026-07-16", "applied": null,
     "status": "in_progress|built|applied|abandoned|superseded",
     "run_record": "batches/run_records/<file>.md", "notes": "..."}

Global scopes (countries == ["*"], e.g. a tracker-wide GIIGNL reconciliation
or a missing-year ref-sweep) are NOT credited as per-country freshness —
reported separately so a country doesn't look fresh just because a global
pass technically touched every row.

Usage:
    python coverage_status.py
    # Scans batches/staging/**/meta.json, prints a markdown table to stdout.
    python coverage_status.py --gem-csv ../gem_export.csv
    # Cross-checks against the export's country universe: a country with
    # zero meta.json coverage is reported as "never touched".
    python coverage_status.py --stale-than 30
    # Only countries not touched (any lane) in the last 30 days.
    python coverage_status.py --json work/coverage_status.json
    # Write JSON instead of markdown.

Always exits 0 — this is a reporting tool, not a validator.
"""
import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
STAGING_ROOT = REPO_ROOT / "batches" / "staging"

# workflow -> ledger lane(s) it counts toward
LANES = {
    "update": ["update"],
    "update+discovery": ["update", "discovery"],
    "discovery": ["discovery"],
    "reconciliation": ["recon"],
    "captive_power": ["captive"],
    "refsweep": ["refsweep"],
    "record_repair": ["update"],
}
LANE_COLUMNS = ["update", "discovery", "recon", "captive"]


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def load_meta_files(staging_root=STAGING_ROOT):
    """Find every meta.json under staging_root, any depth. Malformed files
    are skipped with a warning on stderr, not a crash."""
    out = []
    for path in sorted(staging_root.glob("**/meta.json")):
        try:
            out.append((path, json.loads(path.read_text())))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"WARNING: skipping unreadable {path}: {exc}", file=sys.stderr)
    return out


def load_country_universe(gem_csv_path):
    """Distinct Country/Area values in a GEM export CSV, or None if absent."""
    p = Path(gem_csv_path)
    if not p.exists():
        return None
    with p.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header or "Country/Area" not in header:
            print(f"WARNING: 'Country/Area' column not found in {gem_csv_path}", file=sys.stderr)
            return None
        idx = header.index("Country/Area")
        return {row[idx].strip() for row in reader if len(row) > idx and row[idx].strip()}


def build_ledger(meta_records):
    """Returns (per_country, cross_cutting, in_flight).
    per_country: {country: {lane: (date, scope_slug, tier)}} — latest per lane.
    cross_cutting / in_flight: lists of (path, meta)."""
    per_country = defaultdict(dict)
    cross_cutting, in_flight = [], []

    for path, meta in meta_records:
        countries = meta.get("countries") or []
        if meta.get("status") == "in_progress":
            in_flight.append((path, meta))
        if countries == ["*"]:
            cross_cutting.append((path, meta))
            continue

        when_d = _parse_date(meta.get("applied") or meta.get("built") or meta.get("started"))
        if when_d is None:
            continue
        touch = (when_d, meta.get("scope_slug", path.parent.name), meta.get("tier"))

        for lane in LANES.get(meta.get("workflow"), []):
            for country in countries:
                existing = per_country[country].get(lane)
                if existing is None or when_d > existing[0]:
                    per_country[country][lane] = touch

    return per_country, cross_cutting, in_flight


def _fmt_touch(entry):
    if entry is None:
        return "—"
    when_d, scope_slug, tier = entry
    return f"{when_d.isoformat()} ({scope_slug}{'/' + tier if tier else ''})"


def _last_touch(lanes):
    dates = [v[0] for v in lanes.values()]
    return max(dates) if dates else None


def _country_rows(per_country, universe, today):
    """(country, lanes, days_since) for every known country, stalest first."""
    all_countries = set(per_country.keys()) | (universe or set())
    rows = []
    for country in all_countries:
        lanes = per_country.get(country, {})
        last = _last_touch(lanes)
        days_since = (today - last).days if last else None
        rows.append((country, lanes, days_since))
    # stalest first: never-touched (∞) at the top, then descending days-since
    rows.sort(key=lambda r: (-(float("inf") if r[2] is None else r[2]), r[0]))
    return rows


def render_markdown(per_country, cross_cutting, in_flight, universe, today, stale_than):
    rows = _country_rows(per_country, universe, today)
    if stale_than is not None:
        rows = [r for r in rows if r[2] is None or r[2] >= stale_than]

    lines = [f"# Coverage ledger — as of {today.isoformat()}\n"]
    lines.append("## Per-country freshness (stalest first)\n")
    lines.append("| Country | Last update | Last discovery | Last recon | Last captive | Days since last touch |")
    lines.append("|---|---|---|---|---|---|")
    for country, lanes, days_since in rows:
        days_str = "never touched since ledger began" if days_since is None else str(days_since)
        cells = " | ".join(_fmt_touch(lanes.get(c)) for c in LANE_COLUMNS)
        lines.append(f"| {country} | {cells} | {days_str} |")

    lines.append("\n## Cross-cutting passes (global scope — NOT credited toward any single country's freshness above)\n")
    if cross_cutting:
        lines.append("| Scope | Workflow | Tier | Started | Built | Applied | Status | Run record |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for path, meta in cross_cutting:
            lines.append(
                f"| {meta.get('scope_slug', path.parent.name)} | {meta.get('workflow')} | "
                f"{meta.get('tier') or '—'} | {meta.get('started') or '—'} | {meta.get('built') or '—'} | "
                f"{meta.get('applied') or '—'} | {meta.get('status')} | {meta.get('run_record') or '—'} |"
            )
    else:
        lines.append("(none)")

    lines.append("\n## In flight (status=in_progress — NOT completed coverage)\n")
    if in_flight:
        for path, meta in in_flight:
            countries = ", ".join(meta.get("countries") or []) or "—"
            lines.append(f"- **{meta.get('scope_slug', path.parent.name)}** — {countries} (started {meta.get('started') or '?'})")
    else:
        lines.append("(none)")

    if universe is not None:
        never = sorted(universe - set(per_country.keys()))
        lines.append(f"\n## Countries in the GEM export with no meta.json coverage at all ({len(never)})\n")
        lines.append(", ".join(never) if never else "(none)")

    return "\n".join(lines)


def render_json(per_country, cross_cutting, in_flight, universe, today):
    rows = _country_rows(per_country, universe, today)
    per_country_out = {
        country: {
            **{c: (lanes.get(c) and {"date": lanes[c][0].isoformat(), "scope_slug": lanes[c][1], "tier": lanes[c][2]}) for c in LANE_COLUMNS},
            "days_since_last_touch": days_since,
        }
        for country, lanes, days_since in rows
    }
    rel = lambda p: str(p.relative_to(REPO_ROOT))
    return {
        "generated": today.isoformat(),
        "per_country": per_country_out,
        "cross_cutting_passes": [{**meta, "meta_path": rel(path)} for path, meta in cross_cutting],
        "in_flight": [{**meta, "meta_path": rel(path)} for path, meta in in_flight],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gem-csv", default="./gem_export.csv", help="GEM export CSV (default ./gem_export.csv); omit-friendly if absent")
    ap.add_argument("--json", metavar="PATH", help="Write JSON to PATH instead of printing markdown")
    ap.add_argument("--stale-than", type=int, metavar="N", help="Only show countries not touched in the last N days")
    args = ap.parse_args()

    today = date.today()
    per_country, cross_cutting, in_flight = build_ledger(load_meta_files())
    universe = load_country_universe(args.gem_csv)

    if args.json:
        Path(args.json).write_text(json.dumps(render_json(per_country, cross_cutting, in_flight, universe, today), indent=2))
        print(f"Wrote {args.json}")
    else:
        print(render_markdown(per_country, cross_cutting, in_flight, universe, today, args.stale_than))
    return 0


if __name__ == "__main__":
    sys.exit(main())
