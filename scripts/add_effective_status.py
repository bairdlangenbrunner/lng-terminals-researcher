#!/usr/bin/env python3
"""Append an EffectiveStatus column to a GEM LNG export CSV.

The live GEM export carries Status + Substatus per unit-row. A non-`proposed`
advancing status (proposed -> construction -> operating) only counts as the unit's
official status when its substatus is `actual`; a `planned` substatus means the
milestone is merely PROJECTED, so the unit is effectively still `proposed`
(Tilbury Phase 1b, LNG Canada Phase 2 T3-T4). See normalize.effective_status and
docs/reference/lifecycle_rules.md.

This writes a COPY of the input with two columns appended at the end — the raw
115-column schema (read by position elsewhere) is left byte-for-byte intact:

  EffectiveStatus    the rule-applied status (the "backup proposed" fallback)
  StatusRuleApplied  "planned->proposed" when the rule changed the status, else ""

Use it to produce handoff / archive snapshots; report_diff.py already applies the
rule internally, so the working ./gem_export.csv does NOT need this column.

Snapshot retention: when --output is a timestamped archive snapshot
(`gem_export_<YYYYMMDD>_<HHMM>_ET.csv`, the convention for the local `data/`
archive), the script keeps only the --keep most recent such snapshots in that
directory and prunes older ones (default 2). It only ever deletes siblings that
match the same archive-name pattern, and only when --output is itself such a
snapshot — the working ./gem_export.csv and any other output name are untouched.

Usage:
    python add_effective_status.py [-i gem_export.csv] -o <out.csv>
    python add_effective_status.py -o data/gem_export_20260607_1857_ET.csv   # prunes to 2 newest
    python add_effective_status.py -o data/gem_export_20260607_1857_ET.csv --keep 0  # no pruning
"""
import argparse
import csv
import os
import re
import sys

from normalize import effective_status

# The timestamped local-archive snapshot naming convention (see scripts/README.md
# and docs/reference/lifecycle_rules.md). Date + time are fixed-width zero-padded,
# so a reverse lexical sort of these names is also reverse-chronological.
ARCHIVE_RE = re.compile(r"^gem_export_\d{8}_\d{4}_ET\.csv$")


def prune_snapshots(output_path, keep):
    """Keep only the `keep` most recent timestamped GEM snapshots in output's dir.

    Self-scoping and safe: returns [] (deletes nothing) unless --output is itself
    a `gem_export_<stamp>_ET.csv` archive snapshot, and only ever removes siblings
    matching that same pattern. Returns the list of pruned filenames.
    """
    if keep < 0:
        return []
    out_dir = os.path.dirname(os.path.abspath(output_path))
    if not ARCHIVE_RE.match(os.path.basename(output_path)):
        return []  # not an archive snapshot -> never prune
    snaps = sorted((f for f in os.listdir(out_dir) if ARCHIVE_RE.match(f)),
                   reverse=True)  # newest first
    removed = []
    for name in snaps[keep:]:
        try:
            os.remove(os.path.join(out_dir, name))
            removed.append(name)
        except OSError as e:
            print(f"WARN: could not prune {name}: {e}", file=sys.stderr)
    return removed


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-i", "--input", default="./gem_export.csv",
                    help="input export CSV (default ./gem_export.csv)")
    ap.add_argument("-o", "--output", required=True, help="output CSV path")
    ap.add_argument("--keep", type=int, default=2,
                    help="when --output is a timestamped data/gem_export_<stamp>_ET.csv "
                         "snapshot, keep only the N most recent such snapshots in its "
                         "directory and prune older ones (default 2; 0 deletes all but "
                         "the one just written; -1 disables pruning)")
    args = ap.parse_args()

    with open(args.input, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        sys.exit(f"ERROR: {args.input} is empty")

    header = rows[0]
    try:
        i_status = header.index("Status")
        i_sub = header.index("Substatus")
    except ValueError:
        sys.exit("ERROR: input CSV missing Status / Substatus columns")

    out_header = header + ["EffectiveStatus", "StatusRuleApplied"]
    out_rows = [out_header]
    changed = 0
    for row in rows[1:]:
        if len(row) <= max(i_status, i_sub):
            out_rows.append(row + ["", ""])
            continue
        raw = row[i_status]
        eff = effective_status(raw, row[i_sub])
        flag = "planned->proposed" if eff != raw else ""
        if flag:
            changed += 1
        out_rows.append(row + [eff, flag])

    with open(args.output, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(out_rows)
    print(f"Wrote {len(out_rows) - 1:,} rows to {args.output} "
          f"({changed} status(es) downgraded planned->proposed)")

    pruned = prune_snapshots(args.output, args.keep)
    if pruned:
        print(f"Pruned {len(pruned)} older snapshot(s), keeping the {args.keep} most "
              f"recent: {', '.join(pruned)}")


if __name__ == "__main__":
    main()
