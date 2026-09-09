# Kickoff + RESUME STATE MACHINE — captive-power africa + oceania (final two increments)

User directive (2026-08-02): "go ahead and do africa and then oceania … if you run into any
token limits going forward, build in automation that picks up the research where it leaves
off. I want both africa and oceania to be completely finished before you stop." Finishing
includes uploading the two workbooks to the shared Drive folder
`1AW4LOVCF63NBLdo0UAVZ1_fxe60KeOnc` (same delivery pattern as the four-region rebuild).

**This file is the durable resume plan.** A recurring session cron re-prompts an idle session
to read this file and continue. Any session (this one after a usage-limit pause, or a fresh
one) resumes by walking the state checks below IN ORDER and continuing from the first
incomplete step. All research state is on disk — shard results are per-file checkpoints, so
nothing is lost mid-run.

## Scope

- **africa**: 67 terminals — the coordinate-first audit's `africa` pending set, PLUS the
  missing-coords New Fortress Angola (T100000130823). Includes Egypt (Ain Sokhna/Sumed FSRUs
  sit in ME-gulf coords but are tagged Egypt → they belong to whichever increment their
  worklist assigns; the audit's pending listing is authoritative).
- **oceania**: 37 terminals (Australia's LNG majors — expect heavy mechanical-drive YES
  verdicts — plus PNG, NZ, Fiji etc., and Tanjung Benoa-class coordinate strays if the audit
  assigns them here).
- Worklists are ALWAYS regenerated from the audit against a fresh export — never hand-typed.

## Method (identical to americas-gap; scripts to copy/adapt live there)

Follow `docs/workflows.md` §9 + `docs/sops/captive_power.md`. Per region:
`worklist.json` (from audit) → `_compute_neighbors.py` (whole-country GOGPT, `gogpt_plant_id`
on every row) → `_build_dispatch.py` (max 8 terminals/shard, by country) → research shards
(subagents write `shard_results/shard_*.json`, one file per shard = checkpoint) → QC gate →
`_assemble_<region>.py` → add region to `_merge_full_regions.py` REGIONS → build + recalc →
memo/run-record/meta/memory → upload. Verdict rules: no MW floor, no duty floor, fuel gate
(unstated = INSUFFICIENT never NO), FSRU-onboard convention (fleet-level operator disclosure
= primary → green), SCREENED needs evidence, NO needs enumeration or explicit supply
statement. Every URL through `scripts/url_verifier.py`; no gem.wiki/GEM-derived/abarrelfull/
bare-domain citations; mirror URLs = one source.

## RESUME STATE MACHINE — run these checks in order, continue at the first that fails

1. **Fresh export?** `scripts/gem_export.csv` newer than this run's start (2026-08-02)?
   If resuming within the same day, reuse it; a NEW session pulls fresh
   (`cd scripts && python ../../gem-db-ops/gem_query.py --all-fields lng -o gem_export.csv
   && python pull_gem_db.py --map-only`).
2. **Worklists?** `batches/staging/captive_power/{africa,oceania}/worklist.json` exist?
   If not: `cd scripts && python captive_coverage_audit.py --pending africa,oceania` and
   write each region's uncrawled list (terminal_id/terminal/country) as worklist.json
   (use `--csv`/json output if available — read the script header).
3. **Staging dirs?** meta.json present in both dirs (schema: batches/staging/README.md)?
4. **Neighbors?** `<dir>/neighbors_raw.json` present (from `_compute_neighbors.py`, needs
   `GEM_READONLY_DB_URL`)?
5. **Dispatch?** `<dir>/dispatch/shard_*.json` present and their terminal union == worklist?
6. **Research complete?** For each dispatch shard, a matching
   `<dir>/shard_results/shard_*.json` exists and covers all its terminal_ids? **Dispatch
   ONLY the missing/incomplete shards** — completed shard files are finished checkpoints,
   never re-research them. Shard agents must write their output file as their final act;
   an interrupted shard = missing file = redispatch that shard only.
7. **QC gate done?** Marker file `<dir>/_qc_gate_done.json` exists (written by the
   orchestrator after adjudications, listing overrides applied)? If not, run the QC gate
   (checklist in the americas-gap run record + SOP §2b/2c/2d).
8. **Assembled?** `<dir>/staged_updates.json` + the other four canonical JSONs exist and
   are newer than the newest shard result?
9. **Built?** `batches/lng_terminals_batch_<stamp>_ET_<region>-captive_update.xlsx` exists,
   guard-clean, recalc clean, for BOTH regions? (Fresh stamp per rebuild; never overwrite.)
10. **Audit passes with NO pending?** `python captive_coverage_audit.py` (no --pending) exits
    OK → the tracker is 100% crawled.
11. **Memo + run record + meta built + memory updated?** (memo `batches/captive_power_memo_
    <stamp>_ET_africa-oceania.md`; run record `batches/run_records/2026-08-02_captive-power-
    africa-oceania.md`; both metas status=built; memory files per task #19.)
12. **Uploaded?** Both workbooks in Drive folder `1AW4LOVCF63NBLdo0UAVZ1_fxe60KeOnc`
    (gws-gem-write `gws drive files create --params '{"supportsAllDrives": true}'
    --json '{"name": …, "parents": […]}' --upload <file>`). Verify by listing the folder
    (read-only profile).
13. **Done →** delete the resume cron job (CronList → CronDelete), update this file's
    STATUS line below, report.

## STATUS (update as steps complete)

- run started: 2026-08-02, session b8716ad0 continuation
- **RUN COMPLETE (2026-08-02 evening) — all 13 steps done.** All 4 recovery files landed
  (Hilli→YES green, Pluto→YES green via Wayback save-page-now, Crib Point→YES yellow,
  Angola/Nguya/NWS/Prelude→green; Tango + Pasca stayed INSUFFICIENT → live-DB Trues KEPT).
  Gate records: `{africa,oceania}/_qc_gate_done.json`. Assembled + merged
  (`_merge_full_regions.py`) + built: `batches/lng_terminals_batch_20260802_1650_ET_
  {africa,oceania}-captive_update.xlsx` — guard-clean, recalc clean, 81 tests pass.
  **Final no-pending coverage audit PASSES: 843/843 — the tracker is 100% crawled.**
  Memo `batches/captive_power_memo_20260802_1652_ET_africa-oceania.md`; run record
  `batches/run_records/2026-08-02_captive-power-africa-oceania.md`; both metas
  status=built; memories updated. Workbooks uploaded to Drive folder
  1AW4LOVCF63NBLdo0UAVZ1_fxe60KeOnc; resume cron d6a893fa deleted.
