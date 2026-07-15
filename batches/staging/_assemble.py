"""Merge per-country sweep JSON into build_review_package input files for a region.

Usage:  python batches/staging/_assemble.py <region>      (e.g. southamerica)
Reads   batches/staging/<region>/<slug>.<type>.json  (type in updates/qa/wiki/entity/monitor/newterminals/newunits)
Writes  batches/staging/<region>/_build/staged_*.json  + staged_scope.json
Prints  per-type counts and whether a discovery-mode build is needed.
"""
import json, sys, glob, os
from pathlib import Path

REGION = sys.argv[1]
BASE = Path(__file__).parent / REGION
OUT = BASE / "_build"
OUT.mkdir(parents=True, exist_ok=True)

# Clear stale staged_*.json from any prior assemble of this region. _assemble only
# WRITES a type's file when that type is non-empty (see `if items:` below), so without
# this purge a type that is empty THIS run would silently inherit the previous run's file
# (e.g. an update-only assemble leaking its wiki into a following discovery-only assemble).
for _old in OUT.glob("staged_*.json"):
    _old.unlink()

# type-suffix -> build_review_package input filename
TYPES = {
    "updates": "staged_updates.json",
    "timeline": "staged_status_timeline.json",
    "qa": "staged_qa_review.json",
    "wiki": "staged_wiki_updates.json",
    "entity": "staged_entity_additions.json",
    "monitor": "staged_monitor_list.json",
    "newterminals": "staged_new_terminals.json",
    "newunits": "staged_new_units.json",
}

def _load_list(fp):
    try:
        data = json.loads(Path(fp).read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception as e:
        print(f"  WARN: {fp}: {e}")
        return []

# qa and entity are the two types that legitimately arise on BOTH passes and appear
# in BOTH workbooks, so their discovery-pass files (`*.disc.qa.json` /
# `*.disc.entity.json`) are split into their own build inputs below — the update
# workbook shows only the update-pass rows, the discovery workbook only its own, and
# no row is duplicated across the two books. Every other type is inherently one-sided
# (updates/timeline/wiki/stale = update; monitor/newterminals/newunits = discovery),
# so their `.disc.*` variants correctly merge into the single per-type file here.
DISC_SPLIT = {
    "qa": "staged_qa_review_discovery.json",
    "entity": "staged_entity_additions_discovery.json",
}

counts = {}
merged_updates = []
for suffix, outname in TYPES.items():
    items = []
    for fp in sorted(glob.glob(str(BASE / f"*.{suffix}.json"))):
        if suffix in DISC_SPLIT and ".disc." in os.path.basename(fp):
            continue
        items.extend(_load_list(fp))
    counts[suffix] = len(items)
    if suffix == "updates":
        merged_updates = items
    if items:
        (OUT / outname).write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

for suffix, outname in DISC_SPLIT.items():
    items = []
    for fp in sorted(glob.glob(str(BASE / f"*.disc.{suffix}.json"))):
        items.extend(_load_list(fp))
    counts[f"disc.{suffix}"] = len(items)
    if items:
        (OUT / outname).write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

# scope = unique terminal_ids touched by updates (so all_fields shows their unit rows)
tids = sorted({u.get("terminal_id") for u in merged_updates if u.get("terminal_id")})
(OUT / "staged_scope.json").write_text(
    json.dumps({"_comment": f"{REGION} sweep — terminals with staged updates", "terminal_ids": tids},
               ensure_ascii=False, indent=2), encoding="utf-8")

print(f"region={REGION}  build_dir={OUT}")
for k, v in counts.items():
    print(f"  {k}: {v}")
print(f"  scope_terminals: {len(tids)}")
needs_discovery = counts.get("newterminals", 0) or counts.get("newunits", 0) or counts.get("monitor", 0)
print(f"  discovery_mode_needed: {bool(needs_discovery)}")
