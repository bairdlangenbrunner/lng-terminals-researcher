"""
Derive the column-index map for a GEM all-fields export CSV from its header row.

This script never fetches anything, and since 2026-08-11 it no longer keeps its
own copy of the expected-column list or the derivation logic either — both live
in the sibling **gem-db-ops** repo (`gem_colmap.py`), the single source of truth
for GEM pulls. This module is now just the local entry point plus the
repo-specific READ_ONLY_* sets below.

Pull the CSV first via gem-db-ops, then derive the map (from scripts/):

    python ../../gem-db-ops/gem_query.py --all-fields lng -o gem_export.csv
    python pull_gem_db.py --map-only

Or do both in one step with gem-db-ops' own LNG pull, which writes the CSV and
the identical .colmap.json together:

    python ../../gem-db-ops/lng/pull.py --output scripts/gem_export.csv

Running this without `--map-only` exits with a pointer — the old cookie-based
fetch path was decommissioned 2026-07-21 and this repo keeps no engine copies.

Why re-derive the column map every batch:
  - GEM's all-fields export is 115 columns (Q2 2026) but the schema can
    drift between releases (columns added, renamed, reordered)
  - Hard-coding column offsets means batch breakage on any schema change
  - The derived map is saved next to the CSV so other scripts use the same one

Usage:
    python pull_gem_db.py --map-only                 # derive map from ./gem_export.csv
    python pull_gem_db.py --map-only --output x.csv  # custom CSV path
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import paths  # noqa: E402  — resolves the sibling gem-db-ops checkout
from schema_constants import COMPUTED_COLUMNS, OUT_OF_SCOPE_COLUMNS  # noqa: E402

sys.path.insert(0, str(paths.db_ops_repo()))
import gem_colmap  # noqa: E402  — canonical expected columns + derive/report/save


DEFAULT_OUT = "./gem_export.csv"

# Canonical short name -> expected header text. Maintained in
# gem-db-ops/gem_colmap.py (LNG_EXPECTED_COLUMNS) so this repo, gogpt-researcher
# and the pulls themselves can never disagree about the schema. Add new GEM
# columns THERE, not here.
EXPECTED_COLUMNS = gem_colmap.LNG_EXPECTED_COLUMNS

# Read-only columns (build_review_package.py must NEVER write these). Derived
# from the canonical header-string sets in schema_constants.py, translated into
# this script's short/canonical column-name keys via EXPECTED_COLUMNS (this
# module keys everything by the short name, not the raw CSV header string).
# These stay local: they encode THIS repo's editing policy, not GEM's schema.
READ_ONLY_COMPUTED = {k for k, v in EXPECTED_COLUMNS.items() if v in COMPUTED_COLUMNS}

READ_ONLY_OUT_OF_SCOPE = {k for k, v in EXPECTED_COLUMNS.items() if v in OUT_OF_SCOPE_COLUMNS}


def derive_column_map(csv_path):
    """Read header row, return {canonical_name: 0-indexed-column} dict.
    Missing expected columns get None (so the caller can detect schema drift).
    Thin wrapper over gem-db-ops' gem_colmap.derive_from_csv."""
    return gem_colmap.derive_from_csv(csv_path, EXPECTED_COLUMNS)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", "--out", dest="out", default=DEFAULT_OUT)
    p.add_argument("--map-only", action="store_true",
                   help="Derive the map from an existing CSV (the only mode)")
    args = p.parse_args()

    if not args.map_only:
        sys.exit(
            "ERROR: this script never fetches the export — pull via the sibling\n"
            "  gem-db-ops repo's engine, then derive the map (from scripts/):\n\n"
            "    python ../../gem-db-ops/gem_query.py --all-fields lng -o gem_export.csv\n"
            "    python pull_gem_db.py --map-only\n\n"
            "  or in one step: python ../../gem-db-ops/lng/pull.py --output gem_export.csv\n"
        )

    gem_colmap.derive_report_save(args.out, EXPECTED_COLUMNS)


if __name__ == "__main__":
    main()
