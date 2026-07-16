# Repo audit — research workflows, output redundancy, and information loss (2026-07-16)

A critical review of the repo's research processes, requested with three questions:
(1) is any output redundant across sweeps/updates/discoveries, (2) should the set of
workflows or the staging/storage layout change, and (3) is any collected information
going missing from the outputs. Modeled loosely on the 2026-07 pipelines-researcher
audit. This doc records the findings and what was changed; the run record for the
implementation is `batches/run_records/2026-07-16_repo-audit_workflow-and-output-review.md`.

## Verdict on the workflow set

**Keep all 8 workflows.** Unlike the pipelines repo (where several near-duplicate
workflows were consolidated), the 8 here are genuinely distinct in trigger, scope
rules, output shape, and staging contract: reconciliation (external-report diff),
update (standard/exhaustive), discovery, triage (memo), QC (memo, "QC detects,
Update fixes"), regional sweep (a dispatch wrapper over update+discovery, not a
ninth research mode), missing-year ref-sweep (Postgres-driven backfill), and
captive-power (cross-tracker, single-field edit lane). Consolidating any pair would
blur a scope rule that exists for a reason.

The real redundancy problem was not the workflow set but **cross-batch memory**:
nothing machine-readable recorded which countries were covered when, at what tier,
by which batch. Coverage state lived in prose (SWEEP_PROGRESS.md, run records) that
dispatch never consulted, so a new batch could silently re-research a country a
recent batch had just covered (observed live: the levant-iraq batch re-researched
countries swept 2026-06-03/04 with zero reference to the prior staged JSON).

## Findings

### Information loss (question 3) — defects fixed in code

1. **`updates_summary` citation column blank in every batch ever built.**
   `build_review_package.py`'s sheet header said `ref_url`; staged records say
   `ref_urls`. The paste sheet was unaffected (different code path), but the
   human-review sheet never showed the citations. Fixed, with a legacy-key
   fallback, plus a general `_validate_records` GUARD pass that warns on unknown
   keys (the silently-blank-cell class) and missing identity keys in staged JSON.
2. **Ref-sweep output dropped data.** `refsweep_missing_year.py` truncated
   `proposed_refs` to 3 (a 4th ref was confirmed dropped in shard_05) and discarded
   the per-URL `verifications` array entirely. Now: `refs_overflow` + `verified`
   columns in the CSV/xlsx, and the JSON output carries the full
   `proposed_refs`/`verifications` arrays (lossless).
3. **Sweep done-marker summaries discarded.** `_build_region.py` read only
   `country` from each done-marker; per-country counts, notes, and the
   `escalation` flag (never once surfaced to the user) were thrown away. Now the
   full summaries persist to `_build/_roster_summaries.json` and any
   `escalation: true` prints a loud banner at build time.
4. **URL verification evidence lived only in scrollback.** `url_verifier.py` now
   supports `URL_VERIFIER_LOG` / `--log <path>` writing one JSONL line per check
   ({ts, url, expected, ok, reason}) — the durable record of what was verified
   with which tokens.
5. **QC findings had no structured form.** QC memos are prose; the fix batch
   re-derived targets by hand. `citation_qc.py` already supported `--output`;
   the QC SOP now routes structured findings to
   `batches/staging/qc-<stamp>/staged_qc_findings.json` (tracked via the existing
   gitignore re-include).

### Redundancy / coverage (questions 1–2) — the coverage ledger

- Every staging dir under `batches/staging/` now carries a **`meta.json`**
  (scope_slug, workflow, tier, countries, status: in_progress/built/applied/
  abandoned/superseded, run_record pointer). Backfilled for all existing dirs from
  run-record/SWEEP_PROGRESS evidence.
- **`scripts/coverage_status.py`** reads the ledger and prints per-country
  freshness (last covered date, tier, workflow, staleness vs a threshold) plus
  in-flight dirs. Triage and sweep dispatch now consult it (CLAUDE.md router +
  workflows.md updated); it replaces prose ledgers as the source of "what was last
  done where". The stalled Asia sweep (4/22 groups, dormant since 2026-07-08) was
  formally closed in SWEEP_PROGRESS.md — its remaining scope is visible in the
  ledger rather than in an open-ended progress file.

### Smaller correctness/hygiene items fixed

- `completeness_sweep.py`: `CaptiveGasPower [ref]` blank-ref flags suppressed via
  `WORKFLOW_OWNED_REFS` — the captive-power SOP owns that pair (>50 MW /
  mechanical-drive rules); a standard Update must not half-apply them. Orphan-ref
  (Rule F) still applies.
- `fetch_timeline.py`: dead legacy `--web` scraper (retired Heroku host) removed
  outright; read-only Postgres is the only path, DB-unreachable → escalate.
- `.gitignore`: dead `_build_disc/` pattern removed (discovery split shipped as
  filename infixes, the dir never existed).
- Stale docs corrected (docs sweep): `sop_pointers.md` (recon SOP rev drift,
  obsolete sheet names, captive-power SOP absent), `scripts/README.md` dependency
  diagram (claimed build_review_package imports url_verifier/capacity_normalize/
  status_timeline — they're agent-run CLI gates, not imports), deliverables README
  missing row, and rule text deduplicated to pointer-style (CLAUDE.md captive
  block now points at the SOP instead of restating it).
- Shared-helper consolidation: `_load_colmap` (copy-pasted in 7 scripts) →
  `scripts/colmap.py`; read-only/out-of-scope column lists (3 copies) →
  `scripts/schema_constants.py`; tests added for monitor_store, the staged-JSON
  validator, and colmap.

## Not changed, deliberately

- The one pre-existing automated cross-batch dedup — `monitor_list/current.json`
  via `monitor_store.py` — already works; the ledger complements it at country
  granularity rather than replacing it.
- The blue re-verified-unchanged convention is well-instrumented (majority of
  staged cells in recent exhaustive batches) and needed no change.
- Workbook/staging shapes per workflow (diff-record vs full-record vs
  verdict-keyed vs shard-record) stay distinct — they mirror genuinely different
  review actions, and unifying them would only add translation layers.
