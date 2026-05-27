"""
Compute stale flags per lifecycle_rules.md dormancy thresholds.

Flags:
  - proposed/construction/idled/mothballed with no updates ≥ 2 years
    → candidate for inferred shelved
  - shelved with no updates ≥ 2 more years (i.e. 4y total stale)
    → candidate for inferred cancelled
  - operating with no updates ≥ 18 months
    → due for routine refresh (lower priority)
  - proposed with LatestPlannedStartYear < current_year - 1
    → planned start has slipped past; worth checking status

Used by Triage SOP §3.1 and Update SOP §3.4.

Usage:
    python stale_sweep.py
    # Reads ./gem_export.csv + .colmap.json
    # Writes ./stale_sweep.json

    python stale_sweep.py --country "United States"
    # Filter to a specific country
"""
import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def _load_colmap(csv_path):
    map_path = Path(csv_path).with_suffix(".colmap.json")
    if not map_path.exists():
        raise RuntimeError(f"colmap.json not found at {map_path}")
    return json.loads(map_path.read_text())


def _parse_date(s):
    """Parse a date string into a date object. Returns None if can't parse."""
    if not s:
        return None
    s = str(s).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%d/%m/%Y", "%Y-%m"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    # Just a year?
    if s.isdigit() and len(s) == 4:
        try:
            return date(int(s), 1, 1)
        except ValueError:
            return None
    return None


def _years_since(d, today):
    if d is None:
        return None
    return (today - d).days / 365.25


def compute_flags(csv_path, today=None, country_filter=None):
    """Walk the CSV and produce a list of flagged units."""
    if today is None:
        today = date.today()

    colmap = _load_colmap(csv_path)
    ci_tid = colmap.get("terminal_id")
    ci_uid = colmap.get("unit_id")
    ci_tname = colmap.get("terminal_name")
    ci_uname = colmap.get("unit_name")
    ci_country = colmap.get("country")
    ci_status = colmap.get("status")
    ci_substatus = colmap.get("substatus")
    ci_last_updated = colmap.get("last_updated")
    ci_latest_planned = colmap.get("latest_planned_start")
    ci_fuel = colmap.get("fuel")

    flags = []
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # header
        for row in reader:
            if len(row) < colmap["_total_columns"]:
                continue

            fuel = row[ci_fuel] if ci_fuel is not None else "LNG"
            if fuel != "LNG":
                continue  # out of scope per methodology

            country = row[ci_country]
            if country_filter and country != country_filter:
                continue

            status = row[ci_status] if ci_status is not None else ""
            substatus = row[ci_substatus] if ci_substatus is not None else ""
            last_updated = _parse_date(row[ci_last_updated]) if ci_last_updated is not None else None
            years_stale = _years_since(last_updated, today)
            latest_planned = row[ci_latest_planned] if ci_latest_planned is not None else ""

            unit_flags = []

            # Rule 1: proposed/construction/idled/mothballed → inferred shelved if 2y stale
            if status in ("proposed", "construction", "idled", "mothballed"):
                if years_stale is not None and years_stale >= 2.0:
                    unit_flags.append({
                        "flag": "inferred_shelved_candidate",
                        "severity": "high",
                        "years_stale": round(years_stale, 1),
                        "reason": (
                            f"{status} with no updates for {years_stale:.1f} years; "
                            f"methodology threshold for inferred shelved is 2 years"
                        ),
                    })

            # Rule 2: shelved → inferred cancelled if 2 more years stale (4y total)
            if status == "shelved":
                if years_stale is not None and years_stale >= 2.0:
                    unit_flags.append({
                        "flag": "inferred_cancelled_candidate",
                        "severity": "high",
                        "years_stale": round(years_stale, 1),
                        "reason": (
                            f"shelved ({substatus}) with no updates for {years_stale:.1f} years; "
                            f"methodology threshold for inferred cancelled is 4 years total since "
                            f"last active entry"
                        ),
                    })

            # Rule 3: operating → routine refresh if >18 months stale
            if status == "operating":
                if years_stale is not None and years_stale >= 1.5:
                    unit_flags.append({
                        "flag": "routine_refresh_due",
                        "severity": "low",
                        "years_stale": round(years_stale, 1),
                        "reason": (
                            f"operating with no updates for {years_stale:.1f} years; "
                            f"due for routine refresh"
                        ),
                    })

            # Rule 4: proposed with planned start in the past
            if status == "proposed" and latest_planned:
                try:
                    py = int(latest_planned)
                    if py < today.year - 1:
                        unit_flags.append({
                            "flag": "planned_start_slipped",
                            "severity": "medium",
                            "planned_year": py,
                            "reason": (
                                f"proposed with LatestPlannedStartYear={py}, "
                                f"now {today.year - py} years past planned start"
                            ),
                        })
                except ValueError:
                    pass

            if unit_flags:
                flags.append({
                    "terminal_id": row[ci_tid],
                    "unit_id": row[ci_uid],
                    "terminal_name": row[ci_tname],
                    "unit_name": row[ci_uname],
                    "country": country,
                    "status": status,
                    "substatus": substatus,
                    "last_updated": str(last_updated) if last_updated else "",
                    "flags": unit_flags,
                })
    return flags


def summarize(flags):
    """Print and return a summary."""
    by_flag = Counter()
    by_country = defaultdict(Counter)
    for f in flags:
        for uf in f["flags"]:
            by_flag[uf["flag"]] += 1
            by_country[f["country"]][uf["flag"]] += 1

    print(f"\n  Total flagged units: {len(flags)}")
    print(f"\n  By flag type:")
    for flag, count in by_flag.most_common():
        print(f"    {flag:35} {count}")

    print(f"\n  Top 10 countries by flag count:")
    country_totals = [(c, sum(counts.values())) for c, counts in by_country.items()]
    for c, n in sorted(country_totals, key=lambda x: -x[1])[:10]:
        breakdown = ", ".join(f"{k}={v}" for k, v in by_country[c].most_common())
        print(f"    {c:30} {n:4}  ({breakdown})")

    return {"by_flag": dict(by_flag), "by_country": {k: dict(v) for k, v in by_country.items()}}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", default="./gem_export.csv")
    p.add_argument("--out", default="./stale_sweep.json")
    p.add_argument("--country", help="Filter to a specific country")
    p.add_argument("--today", help="Override today's date (YYYY-MM-DD); useful for testing")
    args = p.parse_args()

    today = date.today()
    if args.today:
        today = datetime.strptime(args.today, "%Y-%m-%d").date()

    flags = compute_flags(args.csv, today=today, country_filter=args.country)
    summary = summarize(flags)

    out = {
        "today": str(today),
        "country_filter": args.country,
        "summary": summary,
        "flagged_units": flags,
    }
    Path(args.out).write_text(json.dumps(out, indent=2, default=str))
    print(f"\n  Saved to {args.out}")


if __name__ == "__main__":
    main()
