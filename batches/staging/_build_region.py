"""Build a region's UPDATE + DISCOVERY workbooks from staged JSON, with disc-isolation.

Usage:  python batches/staging/_build_region.py <region> <STAMP>
  STAMP e.g. 20260604_2030_ET (caller stamps via `TZ=America/New_York date +%Y%m%d_%H%M_ET`).

Disc-isolation: _assemble.py globs ALL <slug>.<type>.json (both update-side and `.disc.` discovery-side)
into one staged set, so a naive build would duplicate qa/wiki/entity across both workbooks. We instead:
  - UPDATE build  -> hide every `*.disc.*` file, assemble, build --mode update
  - DISCOVERY build -> hide every NON-`.disc` finding file, assemble, build --mode discovery
restoring the hidden files (even on error) between phases. Each finding lands in exactly one workbook.
"""
import subprocess, sys, shutil, glob, os, tempfile
from pathlib import Path

REGION = sys.argv[1]
STAMP = sys.argv[2]
ROOT = Path(__file__).resolve().parents[2]
RDIR = ROOT / "batches" / "staging" / REGION
FIND_TYPES = ("updates", "qa", "wiki", "entity", "monitor", "newterminals", "newunits")

def finding_files():
    out = []
    for t in FIND_TYPES:
        out += glob.glob(str(RDIR / f"*.{t}.json"))
    return out

def is_disc(p):
    return ".disc." in os.path.basename(p)

def run(cmd):
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)

def assemble():
    run([sys.executable, str(ROOT / "batches/staging/_assemble.py"), REGION])

def write_roster(marker_glob, exclude_substr, out_path):
    """Read the per-country done-markers and write a JSON list of the `country`
    values actually swept. This is the authoritative 'countries checked' roster
    for the README — it includes countries whose only output was a country-less
    qa note or a clean no-findings run (which records alone would omit).
    Returns (out_path, summaries): the full marker dicts (+ their filename) so
    the caller can persist per-country summary counts and the escalation flag —
    previously only `country` survived and everything else was discarded."""
    import json as _json
    countries = set()
    summaries = []
    for p in glob.glob(str(RDIR / marker_glob)):
        if any(x in os.path.basename(p) for x in exclude_substr):
            continue
        try:
            d = _json.loads(Path(p).read_text(encoding="utf-8"))
        except Exception:
            continue
        d["marker"] = os.path.basename(p)
        summaries.append(d)
        c = (d.get("country") or "").strip()
        if c:
            countries.add(c)
    Path(out_path).write_text(_json.dumps(sorted(countries), ensure_ascii=False, indent=2), encoding="utf-8")
    summaries.sort(key=lambda d: d["marker"])
    return out_path, summaries

def build(mode, outfile, roster_path=None):
    cmd = [sys.executable, str(ROOT / "scripts/build_review_package.py"),
           "--mode", mode, "--inputs-dir", str(RDIR / "_build"),
           "--gem-csv", str(ROOT / "scripts/gem_export.csv"), "--output", str(outfile)]
    if roster_path:
        cmd += ["--checked-roster", str(roster_path)]
    run(cmd)
    run([sys.executable, str(ROOT / "scripts/recalc.py"), str(outfile)])

def with_hidden(predicate, fn):
    """Temporarily move files matching predicate to a hold dir, run fn(), restore."""
    hold = Path(tempfile.mkdtemp(prefix=f"hold_{REGION}_"))
    moved = []
    try:
        for p in finding_files():
            if predicate(p):
                dst = hold / os.path.basename(p)
                shutil.move(p, dst)
                moved.append((dst, p))
        return fn()
    finally:
        for dst, orig in moved:
            shutil.move(str(dst), orig)
        shutil.rmtree(hold, ignore_errors=True)

results = {}
# Rosters from the per-country done-markers (authoritative "countries checked").
# Update markers = <slug>.done.json EXCLUDING <slug>.disc.done.json and <slug>.reverify.done.json.
# Discovery markers = <slug>.disc.done.json.
(RDIR / "_build").mkdir(exist_ok=True)
upd_roster, upd_sums = write_roster("*.done.json", (".disc.done.json", ".reverify.done.json"), RDIR / "_build" / "_roster_update.json")
disc_roster, disc_sums = write_roster("*.disc.done.json", (), RDIR / "_build" / "_roster_discovery.json")

# Persist the full marker summaries (counts, notes, escalation flag) alongside the
# rosters — the workbook doesn't carry them, and the markers get pruned post-batch.
import json as _json
(RDIR / "_build" / "_roster_summaries.json").write_text(
    _json.dumps({"update": upd_sums, "discovery": disc_sums}, ensure_ascii=False, indent=2),
    encoding="utf-8")

# Done-markers may carry `escalation: true` (a subagent hit a pause-and-ask trigger).
# That flag used to be silently discarded here — surface it loudly instead.
escalated = [d["marker"] for d in upd_sums + disc_sums if d.get("escalation")]
if escalated:
    print("=" * 72)
    print("ESCALATION flagged in done-marker(s) — review before shipping the batch:")
    for m in escalated:
        print(f"  - {m}")
    print("=" * 72)

# UPDATE: hide discovery-side files
upd_out = ROOT / "batches" / f"lng_terminals_batch_{STAMP}_{REGION}_update.xlsx"
def do_update():
    assemble(); build("update", upd_out, roster_path=upd_roster); return upd_out
with_hidden(is_disc, do_update)
results["update"] = upd_out.name

# DISCOVERY: hide update-side (non-.disc) files. Only build if discovery content exists.
disc_present = any(is_disc(p) for p in finding_files())
if disc_present:
    disc_out = ROOT / "batches" / f"lng_terminals_batch_{STAMP}_{REGION}_discovery.xlsx"
    def do_disc():
        assemble(); build("discovery", disc_out, roster_path=disc_roster); return disc_out
    with_hidden(lambda p: not is_disc(p), do_disc)
    results["discovery"] = disc_out.name
else:
    results["discovery"] = None

print("BUILT:", results)
