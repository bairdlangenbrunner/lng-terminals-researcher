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

# type-suffix -> build_review_package input filename
TYPES = {
    "updates": "staged_updates.json",
    "qa": "staged_qa_review.json",
    "wiki": "staged_wiki_updates.json",
    "entity": "staged_entity_additions.json",
    "monitor": "staged_monitor_list.json",
    "newterminals": "staged_new_terminals.json",
    "newunits": "staged_new_units.json",
}

counts = {}
merged_updates = []
for suffix, outname in TYPES.items():
    items = []
    for fp in sorted(glob.glob(str(BASE / f"*.{suffix}.json"))):
        try:
            data = json.loads(Path(fp).read_text(encoding="utf-8"))
            if isinstance(data, list):
                items.extend(data)
        except Exception as e:
            print(f"  WARN: {fp}: {e}")
    counts[suffix] = len(items)
    if suffix == "updates":
        merged_updates = items
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
