"""Merge per-country sweep JSON into build inputs without moving source files.

Usage:
    python batches/staging/_assemble.py <region> [--lane all|update|discovery]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from atomic_io import atomic_write_json  # noqa: E402

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
UPDATE_TYPES = {"updates", "timeline", "qa", "wiki", "entity"}
DISCOVERY_TYPES = {"monitor", "newterminals", "newunits", "qa", "entity"}
DISC_SPLIT = {
    "qa": "staged_qa_review_discovery.json",
    "entity": "staged_entity_additions_discovery.json",
}


def _load_list(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(data).__name__}")
    return data


def _selected(path: Path, suffix: str, lane: str) -> bool:
    is_disc = ".disc." in path.name
    if lane == "all":
        return not (suffix in DISC_SPLIT and is_disc)
    if lane == "update":
        return suffix in UPDATE_TYPES and not is_disc
    return suffix in DISCOVERY_TYPES and (suffix not in DISC_SPLIT or is_disc)


def assemble(region: str, lane: str = "all") -> tuple[Path, dict[str, int]]:
    base = Path(__file__).parent / region
    if not base.is_dir():
        raise ValueError(f"no such staging directory: {base}")
    out = base / "_build"
    out.mkdir(parents=True, exist_ok=True)

    # Clear only outputs owned by this assembler, never arbitrary staging files.
    owned = set(TYPES.values()) | set(DISC_SPLIT.values()) | {"staged_scope.json"}
    for name in owned:
        path = out / name
        if path.exists():
            path.unlink()

    counts: dict[str, int] = {}
    merged_updates: list[dict] = []
    for suffix, outname in TYPES.items():
        items: list[dict] = []
        for path in sorted(base.glob(f"*.{suffix}.json")):
            if _selected(path, suffix, lane):
                items.extend(_load_list(path))
        counts[suffix] = len(items)
        if suffix == "updates":
            merged_updates = items
        if items:
            target = DISC_SPLIT.get(suffix, outname) if lane == "discovery" and suffix in DISC_SPLIT else outname
            atomic_write_json(out / target, items)

    # In all-lane compatibility mode, discovery QA/entity retain separate files.
    if lane == "all":
        for suffix, outname in DISC_SPLIT.items():
            items: list[dict] = []
            for path in sorted(base.glob(f"*.disc.{suffix}.json")):
                items.extend(_load_list(path))
            counts[f"disc.{suffix}"] = len(items)
            if items:
                atomic_write_json(out / outname, items)

    tids = sorted({u.get("terminal_id") for u in merged_updates if isinstance(u, dict) and u.get("terminal_id")})
    atomic_write_json(out / "staged_scope.json", {
        "_comment": f"{region} {lane} lane — terminals with staged updates",
        "terminal_ids": tids,
    })
    return out, counts


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("region")
    ap.add_argument("--lane", choices=("all", "update", "discovery"), default="all")
    args = ap.parse_args(argv)
    try:
        out, counts = assemble(args.region, args.lane)
    except ValueError as exc:
        ap.error(str(exc))
    print(f"region={args.region}  lane={args.lane}  build_dir={out}")
    for key, value in counts.items():
        print(f"  {key}: {value}")
    print(f"  discovery_mode_needed: {bool(counts.get('newterminals') or counts.get('newunits') or counts.get('monitor'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
