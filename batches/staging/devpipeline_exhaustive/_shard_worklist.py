#!/usr/bin/env python3
"""Shard one country's exhaustive worklist into per-agent sub-worklists.

  python batches/staging/devpipeline_exhaustive/_shard_worklist.py <region> <slug> [target_single_units]

A country worklist (`<region>/<slug>.worklist.json`, built by `_build_worklist.py`) can be too big for one
subagent to re-verify well (e.g. Australia = 9 distinct terminals, Papua New Guinea = a 12-site shelved
project + 2 proposed terminals). This splits it into shards that the workflow dispatches one-agent-each,
following the "shard big countries" rule — WITHOUT ever splitting a multi-unit terminal/project across agents
(project-level research must stay with one agent so its shared fields can't diverge).

Sharding rule:
- Every terminal with >1 in-scope unit becomes its OWN shard (one project = one agent; rows replicate).
- Single-unit terminals are packed into shards of at most `target_single_units` (default 3 — the heaviest
  Middle East per-agent load).

Outputs `<region>/<slug>-1.worklist.json`, `-2`, … (same payload schema as the unsharded file, with
`country` preserved and `slug` = `<slug>-N`), and DELETES the original `<slug>.worklist.json` so there is
exactly one worklist per dispatched slug. Re-running `_build_worklist.py <region>` regenerates the unsharded
file (idempotent), after which this can be re-run. The assembler (`_merge_recheck.py`) globs `*.updates.json`,
so shard outputs merge transparently; `_state.py` keys off the canonical `<slug>` so write a combined
`<slug>.done.json` after the shards finish (the workflow driver does this).

Prints the shard groups as a JSON line (`SHARDS: [...]`) for pasting into the workflow `args.groups`.
"""
import json, sys
from collections import OrderedDict
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: _shard_worklist.py <region> <slug> [target_single_units]")
    region, slug = sys.argv[1], sys.argv[2]
    target = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    src = HERE / region / f"{slug}.worklist.json"
    if not src.exists():
        sys.exit(f"{src} not found — run _build_worklist.py {region} first")
    wl = json.loads(src.read_text())
    country = wl["country"]

    # group units by terminal, preserving first-seen order
    byterm = OrderedDict()
    for u in wl["units"]:
        byterm.setdefault(u["terminal_id"], []).append(u)

    multi = [(tid, us) for tid, us in byterm.items() if len(us) > 1]
    single = [(tid, us) for tid, us in byterm.items() if len(us) == 1]

    shards = []  # list of (list-of-units, list-of-terminal-names)
    for tid, us in multi:
        shards.append((list(us), [us[0]["terminal_name"]]))
    # pack single-unit terminals up to `target` per shard
    cur, curnames = [], []
    for tid, us in single:
        if len(cur) >= target:
            shards.append((cur, curnames))
            cur, curnames = [], []
        cur.append(us[0])
        curnames.append(us[0]["terminal_name"])
    if cur:
        shards.append((cur, curnames))

    if len(shards) <= 1:
        print(f"{slug}: {len(wl['units'])} units / {len(byterm)} terminals -> 1 shard; no split needed.")
        return

    groups = []
    for i, (units, tnames) in enumerate(shards, start=1):
        sslug = f"{slug}-{i}"
        payload = {"region": region, "country": country, "slug": sslug, "tier": "exhaustive",
                   "parent_slug": slug, "n_units": len(units), "units": units}
        (HERE / region / f"{sslug}.worklist.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2))
        cells = sum(len(u.get("cells_to_reverify", [])) for u in units)
        print(f"  {sslug:24s} units={len(units):2d} cells={cells:3d} terminals={tnames}")
        groups.append({"country": country, "slug": sslug})

    src.unlink()  # remove the unsharded source so there's one worklist per dispatched slug
    print(f"removed {src.name} (superseded by {len(shards)} shards)")
    print("SHARDS:", json.dumps(groups, ensure_ascii=False))


if __name__ == "__main__":
    main()
