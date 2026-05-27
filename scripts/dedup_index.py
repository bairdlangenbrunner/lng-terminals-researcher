"""
Build dedup indexes from the GEM export CSV.

Three indexes per Discovery SOP §6 and Update SOP §11.4:
  - project_index: (country_norm, terminal_name_norm) -> [terminal_rows]
      For matching discovery candidates against existing terminals by name.
  - sponsor_country_index: (country_norm, owner_norm) -> [terminal_rows]
      For matching by sponsor when name isn't an exact hit.
  - unit_index: UnitID -> unit_row
      For mass lookups by UnitID (used by fetch_timeline.py, stale_sweep.py).

Usage:
    python dedup_index.py
    # Reads ./gem_export.csv + .colmap.json
    # Writes ./dedup_index.json

Library:
    from dedup_index import build_indexes
    project_idx, sponsor_idx, unit_idx = build_indexes("./gem_export.csv")
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

# Import sibling
sys.path.insert(0, str(Path(__file__).parent))
from normalize import normalize_country, normalize_entity, normalize_terminal_name


def _load_colmap(csv_path):
    """Load the colmap.json sibling, or raise if missing."""
    map_path = Path(csv_path).with_suffix(".colmap.json")
    if not map_path.exists():
        raise RuntimeError(
            f"colmap.json not found at {map_path}. Run pull_gem_db.py first."
        )
    return json.loads(map_path.read_text())


def build_indexes(csv_path):
    """Build all three indexes from the GEM CSV.
    
    Returns (project_index, sponsor_country_index, unit_index, all_rows).
    """
    colmap = _load_colmap(csv_path)

    # Required column indices
    ci_tid = colmap.get("terminal_id")
    ci_uid = colmap.get("unit_id")
    ci_country = colmap.get("country")
    ci_terminal_name = colmap.get("terminal_name")
    ci_unit_name = colmap.get("unit_name")
    ci_owner = colmap.get("owner")
    ci_status = colmap.get("status")
    ci_facility_type = colmap.get("facility_type")
    ci_fuel = colmap.get("fuel")

    if None in (ci_tid, ci_uid, ci_country, ci_terminal_name, ci_owner):
        sys.exit("ERROR: required columns missing from colmap. Re-run pull_gem_db.py.")

    project_idx = defaultdict(list)
    sponsor_idx = defaultdict(list)
    unit_idx = {}
    all_rows = []

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row_num, row in enumerate(reader, start=2):
            if len(row) < colmap["_total_columns"]:
                # Skip malformed rows
                continue
            tid = row[ci_tid]
            uid = row[ci_uid]
            country = row[ci_country]
            tname = row[ci_terminal_name]
            uname = row[ci_unit_name]
            owner = row[ci_owner]
            status = row[ci_status] if ci_status is not None else ""
            ftype = row[ci_facility_type] if ci_facility_type is not None else ""
            fuel = row[ci_fuel] if ci_fuel is not None else ""

            country_norm = normalize_country(country)
            tname_norm = normalize_terminal_name(tname)

            row_data = {
                "row_num": row_num,
                "terminal_id": tid,
                "unit_id": uid,
                "country": country,
                "country_norm": country_norm,
                "terminal_name": tname,
                "terminal_name_norm": tname_norm,
                "unit_name": uname,
                "owner": owner,
                "status": status,
                "facility_type": ftype,
                "fuel": fuel,
            }
            all_rows.append(row_data)

            # Index by terminal name (project-level)
            if country_norm and tname_norm:
                project_idx[f"{country_norm}|{tname_norm}"].append(row_data)

            # Index by (sponsor, country) — split owner string into individual entities
            if country_norm and owner:
                # owner can be comma-separated; index each
                for part in owner.split(","):
                    part = part.strip()
                    if not part:
                        continue
                    # Strip percentage suffix if present
                    if "%" in part:
                        part = part.rsplit("(", 1)[0].rsplit(" ", 1)[0]
                    owner_norm = normalize_entity(part)
                    if owner_norm:
                        sponsor_idx[f"{country_norm}|{owner_norm}"].append(row_data)

            # Index by UnitID
            if uid:
                unit_idx[uid] = row_data

    return dict(project_idx), dict(sponsor_idx), unit_idx, all_rows


def main():
    csv_path = "./gem_export.csv"
    if not Path(csv_path).exists():
        sys.exit(f"ERROR: {csv_path} not found. Run pull_gem_db.py first.")

    project_idx, sponsor_idx, unit_idx, all_rows = build_indexes(csv_path)

    print(f"  Total unit-rows: {len(all_rows)}")
    print(f"  Unique terminals: {len(set(r['terminal_id'] for r in all_rows))}")
    print(f"  Project index keys (country|name): {len(project_idx)}")
    print(f"  Sponsor index keys (country|owner): {len(sponsor_idx)}")
    print(f"  Unit index entries: {len(unit_idx)}")

    # Sanity: project-key collisions (>1 row = multi-unit project, expected)
    multi_unit = {k: v for k, v in project_idx.items() if len(v) > 1}
    print(f"\n  Multi-unit projects (project_idx keys with >1 row): {len(multi_unit)}")

    # Sanity: sponsors with many projects
    top_sponsors = sorted(sponsor_idx.items(), key=lambda x: -len(x[1]))[:10]
    print(f"\n  Top 10 (country|sponsor) by unit-row count:")
    for k, v in top_sponsors:
        print(f"    {k}: {len(v)} rows")

    out = {
        "project_index": project_idx,
        "sponsor_country_index": sponsor_idx,
        # unit_idx is not serialized — it's used in-memory only
        "stats": {
            "total_rows": len(all_rows),
            "unique_terminals": len(set(r["terminal_id"] for r in all_rows)),
            "project_keys": len(project_idx),
            "sponsor_keys": len(sponsor_idx),
            "unit_keys": len(unit_idx),
            "multi_unit_projects": len(multi_unit),
        },
    }
    out_path = "./dedup_index.json"
    Path(out_path).write_text(json.dumps(out, indent=2, default=str))
    print(f"\n  Saved to {out_path}")


if __name__ == "__main__":
    main()
