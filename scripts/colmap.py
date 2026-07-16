"""
Shared colmap.json loader.

`_load_colmap` was copy-pasted with minor drift across 7 scripts (citation_qc,
completeness_sweep, entity_lookup, dedup_index, fsru_sync_check, stale_sweep,
report_diff). This is the single canonical implementation — the shape used by
completeness_sweep.py, which is the most capable of the copies: a helpful
"run pull_gem_db.py first" error message, and BOM-safe re-derivation of
`_header_columns` from the CSV header row when pull_gem_db.py has stripped it
out of the serialized colmap.json.
"""
import csv
import json
from pathlib import Path


def load_colmap(csv_path):
    """Load the .colmap.json sibling of csv_path.

    Raises RuntimeError if the colmap file doesn't exist (with a pointer to
    `pull_gem_db.py`). If `_header_columns` is absent from the colmap (pull_gem_db.py
    strips it before serializing to disk), re-derive it from the CSV's own header
    row (encoding="utf-8-sig" — BOM-safe).
    """
    map_path = Path(csv_path).with_suffix(".colmap.json")
    if not map_path.exists():
        raise RuntimeError(
            f"colmap.json not found at {map_path}. Run pull_gem_db.py first."
        )
    colmap = json.loads(map_path.read_text())
    if "_header_columns" not in colmap:
        with open(csv_path, encoding="utf-8-sig") as f:
            colmap["_header_columns"] = next(csv.reader(f))
    return colmap
