#!/usr/bin/env python3
"""Re-verify sweep state + auto-resume scheduling helper (self-contained, fresh-session-safe).

  python batches/staging/_reverify_state.py
      -> per-region remaining (marker-less) reverify slugs; writes /tmp/reverify_args_<region>_remaining.json
         for every region with work left; prints NEXT_REGION.
  python batches/staging/_reverify_state.py --reset "12:40pm"
      -> additionally parse a session-limit reset time and emit a ONE-SHOT cron expression (reset + 3 min
         buffer, America/New_York) for CronCreate to autonomously restart the sweep.

Recomputes file groups from the committed staging tree, so it gives the same answer in a fresh session.
Done-markers (`<slug>.reverify.done.json`) are authoritative; a slug without one is re-dispatched.
"""
import sys, re, glob, os, json
from datetime import datetime, timedelta
from pathlib import Path
try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

ROOT = Path(__file__).resolve().parents[2]
STAGING = ROOT / "batches" / "staging"
REGIONS = ["europe", "africa", "americas", "asia", "middleeast", "oceania"]
REF_TYPES = {"updates", "wiki", "newterminals", "newunits", "monitor"}


def base_slug(fn):
    m = re.match(r"^(.*)\.(updates|wiki|newterminals|newunits|monitor|qa|entity)\.json$", fn)
    stem = m.group(1) if m else fn
    return stem[:-5] if stem.endswith(".disc") else stem


def has_gemwiki(p):
    try:
        t = Path(p).read_text(encoding="utf-8")
    except Exception:
        return False
    return "gem.wiki" in t or "globalenergymonitor.org" in t


def groups_for(region):
    rdir = STAGING / region
    groups = {}
    if not rdir.is_dir():
        return groups
    for p in sorted(rdir.glob("*.json")):
        m = re.match(r"^.*\.(updates|wiki|newterminals|newunits|monitor|qa|entity)\.json$", p.name)
        if not m:
            continue
        typ = m.group(1)
        if not (typ in REF_TYPES or (typ == "qa" and has_gemwiki(p))):
            continue
        groups.setdefault(base_slug(p.name), []).append(str(p.resolve()))
    return groups


def done_slugs(region):
    return {os.path.basename(p).replace(".reverify.done.json", "")
            for p in glob.glob(str(STAGING / region / "*.reverify.done.json"))}


state = {}
for region in REGIONS:
    g = groups_for(region)
    done = done_slugs(region)
    remaining = {s: fs for s, fs in g.items() if s not in done}
    state[region] = {"total": len(g), "done": len(done & set(g)), "remaining": sorted(remaining)}
    if remaining:
        args = {"region": region, "groups": [{"slug": s, "files": sorted(fs)} for s, fs in sorted(remaining.items())]}
        Path(f"/tmp/reverify_args_{region}_remaining.json").write_text(json.dumps(args, indent=2))

print(json.dumps(state, indent=2))
first = next((r for r in REGIONS if state[r]["remaining"]), None)
print("NEXT_REGION:", first or "ALL-REVERIFY-DONE")

if "--reset" in sys.argv:
    val = sys.argv[sys.argv.index("--reset") + 1].strip().lower()
    val = val.replace("(america/new_york)", "").replace("america/new_york", "").replace(" ", "").strip()
    dt = None
    for fmt in ("%I:%M%p", "%I%p", "%H:%M"):
        try:
            dt = datetime.strptime(val, fmt); break
        except ValueError:
            continue
    if dt is None:
        print("CRON_PARSE_ERROR:", val); sys.exit(0)
    tz = ZoneInfo("America/New_York") if ZoneInfo else None
    now = datetime.now(tz)
    target = now.replace(hour=dt.hour, minute=dt.minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    target += timedelta(minutes=3)  # fire just past the reset
    print(f"RESET_LOCAL: {target.isoformat()}")
    print(f"CRON: {target.minute} {target.hour} {target.day} {target.month} *")
