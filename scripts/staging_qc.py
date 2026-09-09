"""Merge-time QC gate for a sweep staging dir (docs/workflows.md §5 step 3a).

Usage:
    python scripts/staging_qc.py <region-slug> [--csv data/gem_export.csv] [--no-pg]

Runs the orchestrator's mandatory pre-assembly checks over
`batches/staging/<region>/*.json`. Subagent output is NEVER pre-trusted, and the
build's own guards only fire AFTER `_assemble.py` — by which point a defect is
merged and harder to attribute to a shard. This runs the same guards per shard
file (so the offender is named) plus the three things the build cannot do:

  1. `entity_lookup.py --pg` re-check of every staged new entity. Two would-be
     duplicates reached staging on 2026-08-11 (XRG, BNECL/BNOCL) because agents
     read an environmental `--remote` SKIP as a not-found. A skip is not a
     negative, and entities get RENAMED — check the old name too.
  2. Done-marker completeness: a missing `<slug>.done.json` means that shard's
     agent never finished, and assembling anyway silently ships a partial region.
  3. Empty-`[ref]` records not flagged `delete` — a deliberate ref blanking is a
     staged deletion (green+empty), not an orphan.

Key-schema drift counts as a finding, not just a printed note: on 2026-08-11 a whole
shard (`argentina.qa.json`, 13 records) reached the build with `description`/
`field_name` instead of `issue`/`gem_field` — every one of them would have rendered
as a blank qa row — because this gate echoed `_validate_records`' warnings without
counting them, and printed GATE CLEAN anyway.

Read-only and fail-closed: findings exit non-zero. Use `--allow-warnings` only
for an explicitly exceptional diagnostic run; it never edits staged research.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_review_package as brp  # noqa: E402  (guards + STAGED_KEYS live there)

REPO = Path(__file__).resolve().parent.parent

# strings agents reach for instead of a blank id on a multi-terminal / country-level note
PLACEHOLDER_IDS = {"multiple", "n/a", "na", "none", "various", "all", "-", "--", ""}

# staging type-suffix -> STAGED_KEYS label (mirrors batches/staging/_assemble.py's TYPES)
SUFFIX_LABEL = {
    "updates": "updates",
    "timeline": "status_timeline",
    "qa": "qa_review",
    "wiki": "wiki_updates",
    "entity": "entity_additions",
    "monitor": "monitor_list",
    "newunits": "new_units",
    "newterminals": None,   # known-key set is CSV-header-derived; skip key validation
}


def _shards(base):
    """{(slug, suffix): path} for every staged list file, `.disc.` infix included."""
    out = {}
    for fp in sorted(glob.glob(str(base / "*.json"))):
        name = os.path.basename(fp)[:-len(".json")]
        parts = name.split(".")
        if len(parts) < 2:
            continue                      # meta.json etc.
        suffix = parts[-1]
        if suffix not in SUFFIX_LABEL and suffix != "done":
            continue
        out[(".".join(parts[:-1]), suffix)] = fp
    return out


def _load(fp):
    try:
        data = json.loads(Path(fp).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"  UNPARSEABLE: {os.path.basename(fp)}: {e}")
        return None
    if not isinstance(data, list):
        print(f"  NOT-A-LIST: {os.path.basename(fp)} (type {type(data).__name__})")
        return None
    return data


def check_records(base, csv_path):
    """Per-shard: key validation + banned/bare-domain/GIIGNL-mirror/ref-drop guards."""
    findings = 0
    for (slug, suffix), fp in sorted(_shards(base).items()):
        if suffix == "done":
            continue
        recs = _load(fp)
        if recs is None:
            findings += 1
            continue
        label = SUFFIX_LABEL.get(suffix)
        tag = f"{slug}.{suffix}"
        print(f"  {tag}: {len(recs)} record(s)")
        if label:
            findings += brp._validate_records(f"{label}({tag})", recs) or 0
        findings += len(brp.warn_banned_domain_urls(tag, recs))
        findings += len(brp.warn_bare_domain_urls(tag, recs))
        if suffix == "updates":
            findings += len(brp.warn_duplicate_giignl_refs(recs))
            findings += len(brp.warn_ref_url_drops(recs, str(csv_path)))
            findings += check_blank_refs(tag, recs)
    return findings


def check_blank_refs(tag, recs):
    """A `<field> [ref]` record with an empty new_value blanks the cell. That is a
    legitimate staged DELETION (proven-dead URLs, or a Rule F orphan ref with no
    paired value) — but only when it says so: `delete: true` makes the paste view
    render it as a deletion instead of an ambiguous blank cell."""
    hits = [(i, r.get("field_name")) for i, r in enumerate(recs)
            if isinstance(r, dict)
            and str(r.get("field_name", "")).endswith("[ref]")
            and not str(r.get("new_value") or "").strip()
            and not r.get("delete")]
    for i, fld in hits:
        print(f"  GUARD: {tag}[{i}] {fld}: blanks the ref cell but is not flagged "
              "delete:true (staged deletion = green + empty + delete:true)")
    return len(hits)


def _export_index(csv_path):
    """{terminal_id: name}, {unit_id: terminal_id}, {(tid, col): cell} from the fresh export."""
    import csv as _csv
    tids, uids, cells = {}, {}, {}
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        for row in _csv.DictReader(f):
            tid, uid = row.get("TerminalID"), row.get("UnitID")
            if tid:
                tids[tid] = row.get("TerminalName") or ""
                for col, val in row.items():
                    if col and col.endswith("[ref]"):
                        cells.setdefault((tid, col), val or "")
            if uid:
                uids[uid] = tid
    return tids, uids, cells


def check_ids(base, csv_path):
    """Every staged terminal_id / unit_id must exist in the FRESH export, and a
    `[ref]` record's `old_value` must be what the live cell actually holds.

    An agent can research the right facility and still key the record to a stale or
    invented id: on 2026-08-11 the whole Uruguay shard was staged against
    `T100000058656` / "Gas Sayago LNG Terminal (Montevideo)" — no such row exists
    (it is `T100000130580` / "GNL Del Plata FSRU"; only the unit_id matched) — and
    its quoted `old_value` ref cells named URLs the database has never held,
    including a 404. Both merges were therefore computed from fiction. The build
    matches on id, so nothing downstream notices.
    """
    if not Path(csv_path).is_file():
        print(f"  export not found ({csv_path}) — id/old_value check SKIPPED, which is "
              "not a pass")
        return 1
    tids, uids, cells = _export_index(csv_path)
    findings = 0
    for (slug, suffix), fp in sorted(_shards(base).items()):
        if suffix in ("done", "newterminals", "monitor", "entity"):
            continue          # new/candidate records have no export row yet, by design
        for i, r in enumerate(_load(fp) or []):
            if not isinstance(r, dict):
                continue
            tag = f"{slug}.{suffix}[{i}]"
            tid, uid = r.get("terminal_id"), r.get("unit_id")
            # a prose sheet may legitimately span terminals or a whole country; agents
            # write a placeholder there. Blank is the convention — accept the placeholder
            # with a note, but never on `updates`, where the id IS the paste target.
            if suffix != "updates" and tid and str(tid).strip().lower() in PLACEHOLDER_IDS:
                print(f"  NOTE: {tag} terminal_id {tid!r} is a placeholder on a prose sheet "
                      "— leave it BLANK instead (multi-terminal/country-level note)")
                continue
            if tid and tid not in tids:
                print(f"  GUARD: {tag} terminal_id {tid} is NOT in the fresh export"
                      + (f" (its unit_id {uid} belongs to {uids[uid]})" if uid in uids else "")
                      + " — re-key against the export before building")
                findings += 1
                continue
            if uid and uid in uids and tid and uids[uid] != tid:
                print(f"  GUARD: {tag} unit_id {uid} belongs to terminal {uids[uid]}, "
                      f"not the staged {tid}")
                findings += 1
            name = str(r.get("terminal_name") or "").strip()
            if tid and name and tids.get(tid) and name != tids[tid]:
                print(f"  NOTE: {tag} terminal_name {name!r} != export {tids[tid]!r} "
                      "(renamed record, or the wrong facility — confirm which)")
            fld = str(r.get("field_name") or "")
            if suffix == "updates" and fld.endswith("[ref]") and tid in tids:
                live = cells.get((tid, fld), "")
                claimed = str(r.get("old_value") or "")
                lost = [u for u in re.findall(r"https?://\S+", claimed)
                        if u.rstrip(",;") not in live]
                if lost:
                    print(f"  GUARD: {tag} {fld}: old_value cites {len(lost)} URL(s) the live "
                          f"cell does not contain (first: {lost[0][:90]}) — the merge was "
                          "computed against the wrong baseline")
                    findings += 1
    return findings


def check_entities(base, run_pg=True):
    """Every staged new entity re-checked against the read-only Postgres. A `--pg`
    SKIP (no DB URL / no engine available) is NOT a not-found — it means the check did not
    run, which is exactly the failure that produced two duplicates on 2026-08-11."""
    names = []
    for (slug, suffix), fp in sorted(_shards(base).items()):
        if suffix != "entity":
            continue
        for r in (_load(fp) or []):
            nm = str(r.get("entity_name") or "").strip()
            if nm:
                names.append((f"{slug}.{suffix}", nm))
    if not names:
        print("  no staged new entities")
        return 0
    findings = 0
    for where, nm in names:
        if not run_pg:
            print(f"  {where}: {nm!r} — NOT CHECKED (--no-pg)")
            findings += 1
            continue
        try:
            p = subprocess.run(
                [sys.executable, str(REPO / "scripts" / "entity_lookup.py"), nm, "--pg"],
                capture_output=True, text=True, timeout=120, cwd=str(REPO / "scripts"))
            res = json.loads(re.search(r"\{.*\}", p.stdout, re.S).group(0))
        except Exception as e:                                  # noqa: BLE001
            print(f"  {where}: {nm!r} — lookup FAILED to run ({e}); re-check by hand")
            findings += 1
            continue
        verdict = str(res.get("result") or res.get("pg", {}).get("result") or "?")
        if verdict.startswith("skipped") or verdict.endswith("failed"):
            print(f"  {where}: {nm!r} — {verdict}: the check DID NOT RUN. "
                  "This is not a not-found; resolve before building.")
            findings += 1
        elif verdict == "no_pg_match":
            print(f"  {where}: {nm!r} — no_pg_match (genuinely new; also try the "
                  "entity's FORMER name — GEM entities get renamed, not replaced)")
        else:
            print(f"  {where}: {nm!r} — {verdict}: ALREADY EXISTS → reuse the existing "
                  "entity id, drop this record, and file a qa note")
            findings += 1
    return findings


def check_done_markers(base):
    """Compare `<slug>.done.json` against the dispatched packets. A shard with no
    marker means its agent never reported; assembling anyway ships a partial region.

    Skipped once `meta.json` says the sweep is `built`/`applied`: closeout prunes the
    markers (the completed-slug list moves into `meta.json`'s `completed_slugs`), so
    demanding them back would make the gate un-rerunnable on a finished batch."""
    meta = base / "meta.json"
    if meta.is_file():
        status = json.loads(meta.read_text()).get("status")
        if status in ("built", "applied"):
            print(f"  sweep status={status} — markers pruned at closeout, check skipped")
            return 0
    packets = sorted(Path(p).name[:-len(".packet.json")]
                     for p in glob.glob(str(base / "packets" / "*.packet.json")))
    if not packets:
        print("  no packets/ dir — cannot verify dispatch completeness")
        return 0
    done = {slug for (slug, suffix) in _shards(base) if suffix == "done"}
    # a discovery agent may write `<slug>.disc.done.json`
    done |= {s[:-len(".disc")] for s in done if s.endswith(".disc")}
    missing = [s for s in packets if s not in done]
    print(f"  packets: {len(packets)}   done markers: {len(done)}")
    for s in missing:
        print(f"  MISSING done marker: {s}")
    return len(missing)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("region", help="staging region slug, e.g. gregor-lac")
    ap.add_argument("--csv", default="scripts/gem_export.csv",
                    help="fresh GEM export, for id and ref-cell baseline checks")
    ap.add_argument("--no-pg", action="store_true",
                    help="skip the Postgres entity re-check (reports it as unchecked, not clean)")
    ap.add_argument("--allow-warnings", action="store_true",
                    help="exit zero despite findings (diagnostic/emergency use only)")
    args = ap.parse_args(argv)

    base = REPO / "batches" / "staging" / args.region
    if not base.is_dir():
        ap.error(f"no such staging dir: {base}")
    csv_path = Path(args.csv)
    if not csv_path.is_absolute():
        csv_path = REPO / csv_path
    print(f"staging QC gate — {base.relative_to(REPO)}\n")
    print("== records ==")
    n_rec = check_records(base, csv_path)
    print("\n== ids + old_value vs the fresh export ==")
    n_rec += check_ids(base, str(csv_path))
    print("\n== staged new entities (Postgres re-check) ==")
    n_ent = check_entities(base, run_pg=not args.no_pg)
    print("\n== done markers ==")
    n_done = check_done_markers(base)
    print(f"\ntotals: record findings={n_rec}  entity findings={n_ent}  missing done={n_done}")
    if not (n_rec or n_ent or n_done):
        print("GATE CLEAN — safe to run _assemble.py")
        return 0
    else:
        print("GATE NOT CLEAN — resolve the findings above before assembling/building")
        return 0 if args.allow_warnings else 1


if __name__ == "__main__":
    sys.exit(main())
