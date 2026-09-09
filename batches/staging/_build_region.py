"""QC, assemble, build, and recalculate a region's isolated workbook lanes."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from atomic_io import atomic_write_json  # noqa: E402

FIND_TYPES = ("updates", "timeline", "qa", "wiki", "entity", "monitor", "newterminals", "newunits")


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True)


def write_roster(rdir: Path, pattern: str, excluded: tuple[str, ...], output: Path):
    countries, summaries = set(), []
    for path in sorted(rdir.glob(pattern)):
        if any(token in path.name for token in excluded):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid done marker {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError(f"done marker must be an object: {path}")
        data = {**data, "marker": path.name}
        summaries.append(data)
        country = str(data.get("country") or "").strip()
        if country:
            countries.add(country)
    atomic_write_json(output, sorted(countries))
    return summaries


def build_lane(rdir: Path, region: str, stamp: str, lane: str, roster: Path, force: bool) -> Path:
    run([sys.executable, str(ROOT / "batches/staging/_assemble.py"), region, "--lane", lane])
    output = ROOT / "batches" / f"lng_terminals_batch_{stamp}_{region}_{lane}.xlsx"
    command = [
        sys.executable, str(ROOT / "scripts/build_review_package.py"),
        "--mode", lane, "--inputs-dir", str(rdir / "_build"),
        "--gem-csv", str(ROOT / "scripts/gem_export.csv"),
        "--checked-roster", str(roster), "--output", str(output),
    ]
    if force:
        command.append("--force")
    run(command)
    run([sys.executable, str(ROOT / "scripts/recalc.py"), str(output)])
    return output


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("region")
    ap.add_argument("stamp", help="YYYYMMDD_HHMM_ET")
    ap.add_argument("--force", action="store_true", help="replace same-stamp derived outputs")
    ap.add_argument("--skip-qc", action="store_true", help="skip staging_qc (diagnostic use only)")
    args = ap.parse_args(argv)

    rdir = ROOT / "batches" / "staging" / args.region
    if not rdir.is_dir():
        ap.error(f"no such staging directory: {rdir}")
    if not args.skip_qc:
        run([sys.executable, str(ROOT / "scripts/staging_qc.py"), args.region])

    build_dir = rdir / "_build"
    build_dir.mkdir(exist_ok=True)
    update_roster = build_dir / "_roster_update.json"
    discovery_roster = build_dir / "_roster_discovery.json"
    update_summaries = write_roster(rdir, "*.done.json", (".disc.done.json", ".reverify.done.json"), update_roster)
    discovery_summaries = write_roster(rdir, "*.disc.done.json", (), discovery_roster)
    atomic_write_json(build_dir / "_roster_summaries.json", {
        "update": update_summaries, "discovery": discovery_summaries,
    })
    escalated = [d["marker"] for d in update_summaries + discovery_summaries if d.get("escalation")]
    if escalated:
        raise SystemExit("ERROR: unresolved escalation in done marker(s): " + ", ".join(escalated))

    results = {"update": build_lane(rdir, args.region, args.stamp, "update", update_roster, args.force).name}
    discovery_present = any(rdir.glob("*.monitor.json")) or any(rdir.glob("*.newterminals.json")) or any(
        rdir.glob("*.newunits.json")) or any(rdir.glob("*.disc.qa.json")) or any(rdir.glob("*.disc.entity.json"))
    results["discovery"] = (
        build_lane(rdir, args.region, args.stamp, "discovery", discovery_roster, args.force).name
        if discovery_present else None
    )
    print("BUILT:", results)
    return 0


if __name__ == "__main__":
    sys.exit(main())
