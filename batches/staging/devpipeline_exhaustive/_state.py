#!/usr/bin/env python3
"""Resume ledger for the EXHAUSTIVE dev-pipeline update — fresh-session-safe.

  python batches/staging/devpipeline_exhaustive/_state.py            # status of every region
  python batches/staging/devpipeline_exhaustive/_state.py middleeast # + which countries remain in one region

Authoritative resume signal = `<slug>.done.json` markers in each region dir (written LAST by each country
subagent). A country in WORKLIST.json without a done-marker is unfinished and gets re-dispatched. Recomputed
from the committed tree, so it gives the same answer in any new session after a compaction / rate-limit.
"""
import json, sys, glob
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKLIST = HERE / "WORKLIST.json"


def done_slugs(region):
    return {Path(p).name.replace(".done.json", "")
            for p in glob.glob(str(HERE / region / "*.done.json"))}


def main():
    if not WORKLIST.exists():
        sys.exit("WORKLIST.json missing — run _build_worklist.py first")
    wl = json.loads(WORKLIST.read_text())
    region_arg = sys.argv[1] if len(sys.argv) > 1 else None
    by_region = wl["by_region"]
    overall_done = overall_total = 0
    print(f"EXHAUSTIVE dev-pipeline scope: {wl['total_units']} units "
          f"({wl['by_status']}) — tier={wl['tier']}")
    for region in sorted(by_region):
        countries = by_region[region]["countries"]
        done = done_slugs(region)
        c_done = sorted(s for c, d in countries.items() if (s := d["slug"]) in done)
        c_left = sorted(d["slug"] for d in countries.values() if d["slug"] not in done)
        units_done = sum(d["count"] for d in countries.values() if d["slug"] in done)
        overall_done += units_done
        overall_total += by_region[region]["count"]
        flag = "  <-- in progress / next" if c_left and not c_done else (
            "  DONE" if not c_left else "  partial")
        print(f"  {region:11s} countries {len(c_done)}/{len(countries)}  "
              f"units {units_done}/{by_region[region]['count']}{flag}")
        if region_arg == region:
            print(f"    done:      {c_done or '(none)'}")
            print(f"    remaining: {c_left or '(none)'}")
    print(f"  {'TOTAL':11s} units {overall_done}/{overall_total} "
          f"({100*overall_done//max(overall_total,1)}%)")
    nxt = next((r for r in sorted(by_region)
                if any(d["slug"] not in done_slugs(r) for d in by_region[r]["countries"].values())), None)
    print("NEXT_REGION_WITH_WORK:", nxt or "ALL-DONE")


if __name__ == "__main__":
    main()
