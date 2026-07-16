# 2026-07-16 — repo audit: workflows, output redundancy, information loss

## Plan

User asked for a critical review of the research processes/workflows (redundancy
across sweeps/updates/discoveries; open to changing workflows or storage; use the
pipelines-researcher audit as a guide) plus a check that no collected information
goes missing from the outputs — then approved implementing all recommendations
("go for it all").

Findings + rationale: `docs/repo_audit_2026-07-16.md`. Executed as 5 parallel
audit subagents (workflows/SOPs, scripts, storage, pipelines baseline, info-loss),
then implementation: correctness-critical code edits inline, plus three
implementation subagents (coverage ledger backfill, docs sweep, shared-helper
refactor + tests).

## Changes

Code (inline):
- `scripts/build_review_package.py` — updates_summary `ref_url`→`ref_urls` fix
  (citation column was blank in every batch ever built) + `_validate_records`
  GUARD validator for staged JSON key drift.
- `scripts/refsweep_missing_year.py` — `refs_overflow` + `verified` columns;
  JSON output now lossless (full proposed_refs/verifications arrays).
- `batches/staging/_build_region.py` — done-marker summaries persisted to
  `_build/_roster_summaries.json`; `escalation: true` now prints a loud banner.
- `scripts/completeness_sweep.py` — `WORKFLOW_OWNED_REFS` suppresses
  `CaptiveGasPower [ref]` blank-ref flags (captive-power SOP owns the pair).
- `scripts/url_verifier.py` — JSONL audit log via `URL_VERIFIER_LOG` / `--log`.
- `scripts/fetch_timeline.py` — legacy `--web` scraper removed (host retired);
  Postgres-only, DB-unreachable → escalate.
- `.gitignore` — dead `_build_disc/` pattern removed.
- `CLAUDE.md` — captive-power rule text deduplicated to pointer; timeline text
  aligned with `--web` removal; coverage-ledger dispatch rule added.

Subagents:
- Coverage ledger: `meta.json` backfilled into every `batches/staging/` dir +
  new `scripts/coverage_status.py`; Asia sweep formally closed in
  SWEEP_PROGRESS.md (remaining scope visible via the ledger).
- Docs sweep: sop_pointers.md, scripts/README.md dependency diagram, QC SOP
  structured-findings sidecar, ref-sweep SOP columns, workflows.md, captive/
  update/discovery/reconciliation/triage SOP touch-ups, staging + deliverables
  READMEs.
- Refactor: `scripts/colmap.py` (shared `_load_colmap`, 7 call sites),
  `scripts/schema_constants.py` (read-only/out-of-scope column lists, 3 copies),
  `_validate_records` extended to other staged types, tests for monitor_store /
  validator / colmap.

Cleanup: pruned already-built sweep done-markers, `_reverify_state.py`, orphaned
`_prior/` dirs, stale export snapshot.

## Outcome

All 69 tests pass (49 pre-existing + 20 new). Smoke build against the
south-asia-iran staging dir confirmed the headline fix on real data: 104/110
`updates_summary` rows now carry `ref_urls` (previously 0 — the column was
blank in every batch ever built); update and discovery modes both build clean
with zero GUARD warnings after one validator calibration (wiki_updates requires
`terminal_name`, not `terminal_id` — country-wide notes legitimately blank the
id). Coverage ledger verified: `coverage_status.py` runs clean over 24 meta.json
files (23 backfilled + one added for `asia/_archive_pre20260708/` so the June
Asia vintage is credited — without it 9 countries wrongly read "never touched");
its stalest-first sort was fixed (was ascending). Workflow set unchanged — the
8 workflows are genuinely distinct; the fix was cross-batch coverage memory
(the ledger), not consolidation.
