# Kept deliverables

Finished batch/analysis workbooks that are **kept long-term** (tracked in git),
as opposed to the routine batch workbooks in `batches/` (gitignored — large,
regenerable, pruned by the user).

Put a file here when the deliverable answers a standing question the team will
revisit — e.g. a one-off data-health analysis tied to a methodology decision —
and you want the exact artifact preserved, not just the staging inputs.

Naming: `<descriptive-slug>_<YYYYMMDD>_<HHMM>_ET.xlsx` (stamp via
`TZ=America/New_York date "+%Y%m%d_%H%M_ET"`). Never overwrite; a rebuild gets a
new stamp.

The regenerable siblings (CSV/JSON) and the raw research inputs stay in the
tracked `batches/staging/<batch>/` tree as the audit trail; this folder holds the
polished workbook.

| File | What it is |
|---|---|
| `missing_year_refsweep_20260630_1146_ET.xlsx` | Missing-year ref-sweep over all LNG status-timeline entries with a status but no year (152 points). For the data-team discussion on how status is stored. Rebuildable via `scripts/refsweep_missing_year.py build` from `batches/staging/ref-sweep-missing-year-20260630_1146_ET/`. See `docs/sops/ref_sweep.md`. |
| `missing_year_refsweep_20260701_1758_ET.xlsx` | Refresh of the 2026-06-30 sweep: re-synced to the live DB (5 stale points pruned, 1 new point added → 148), third research pass on the 12 researchable UNRESOLVED (5 newly filled), and a `fuel_type` column added so oil/NGL/NH3 legacy terminals sort apart. **Supersedes the 20260630 workbook.** Rebuildable via `build --sync-db` from `batches/staging/ref-sweep-missing-year-20260701_1724_ET/`. |
| `missing_year_refsweep_20260714_1505_ET.xlsx` | Global re-check pass: a fresh extract found only 6 remaining missing-year points (down from 148), confirming the 2026-07-01 pass's years were applied. Of the 6: 1 unresolved-structural (Porto Empedocle, no datable event) and 5 legacy crude-oil deepwater ports (`fuel_type=Oil`, out of LNG scope) correctly left unapplied. **Supersedes the 20260701 workbook as the most current ref-sweep pass.** Rebuildable from `batches/staging/ref-sweep-missing-year-20260714_1502_ET/`; see that dir's `meta.json` and `batches/run_records/2026-07-14_missing-year-refsweep-recheck.md`. |
