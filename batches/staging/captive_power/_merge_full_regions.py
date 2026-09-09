"""Merge live captive-power increments into full-region build inputs.

Run from this directory:  python _merge_full_regions.py

The user's 2026-08-01 directive: every regional deliverable workbook carries
EVERYTHING for its region (all live increments merged), not just the newest
increment. Constituent dirs stay the coverage-ledger unit (meta.json per
increment, applied-tracking per increment); this script only concatenates their
canonical five-file staging sets into derived inputs under ./_build/<region>/
(gitignored via batches/staging/*/_build/) for build_review_package.py.

Region composition (live = meta status not superseded):
  americas          = americas-complete + americas-residue + americas-gap
  europe            = europe + europe-topup
  asia              = asia
  middle-east-gulf  = middle-east-gulf
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

REGIONS = {
    "americas": ["americas-complete", "americas-residue", "americas-gap"],
    "europe": ["europe", "europe-topup"],
    "asia": ["asia"],
    "middle-east-gulf": ["middle-east-gulf"],
    "africa": ["africa"],
    "oceania": ["oceania"],
}

FILES = [
    "staged_updates.json",
    "staged_qa_review.json",
    "captive_terminal_first.json",
    "captive_neighboring_plants.json",
    "captive_gogpt_candidates.json",
]

for region, parts in REGIONS.items():
    out = HERE / "_build" / region
    out.mkdir(parents=True, exist_ok=True)
    for fname in FILES:
        merged, seen = [], set()
        for part in parts:
            fp = HERE / part / fname
            if not fp.exists():
                print(f"  ({part}/{fname} absent — skipped)")
                continue
            rows = json.loads(fp.read_text(encoding="utf-8"))
            if fname == "staged_updates.json":
                for r in rows:
                    key = (r["terminal_id"], r.get("unit_id", ""), r.get("field_name", ""))
                    assert key not in seen, f"{region}: duplicate staged row across increments: {key}"
                    seen.add(key)
            elif fname == "captive_terminal_first.json":
                for r in rows:
                    assert r["terminal_id"] not in seen, \
                        f"{region}: terminal_id in two increments' terminal_first: {r['terminal_id']}"
                    seen.add(r["terminal_id"])
            merged.extend(rows)
        (out / fname).write_text(json.dumps(merged, ensure_ascii=False, indent=1),
                                 encoding="utf-8")
        print(f"{region}/{fname}: {len(merged)} rows from {len(parts)} increment(s)")
    print()
