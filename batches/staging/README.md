# Batch staging — the working area for ALL batch inputs

This directory holds the **staging inputs** for batch builds: the per-batch JSON that
`build_review_package.py` assembles into the reviewable `.xlsx` deliverables one level up in `batches/`.
Three shapes live here — the multi-country sweep tree (the scaled form of the **Update workflow** in the
repo `CLAUDE.md`: one research subagent per country, fanned out, then merged per region), the per-edition
reconciliation tree, and ad-hoc single-scope batch dirs. **Nothing batch-related lives loose in the repo
root or `scripts/`.**

> Formerly `chatgpt_audit_batch/sweep/` — renamed to a workflow-neutral name. The original ChatGPT-audit
> import was just the first batch run through this machinery; the structure is reused every cycle.

## Layout

```
batches/staging/
  SWEEP_PROGRESS.md          live ledger while a sweep is in flight (read first to resume); a stub
                             between sweeps — finished ledgers archive to batches/run_records/
  _country_agent_brief.md    the brief each per-country UPDATE subagent reads (tier-parameterized)
  _discovery_brief.md        the brief for discovery-sweep subagents
  _assemble.py               merges <region>/*.<type>.json → <region>/_build/staged_*.json
  <region>/                  per-region sweep dir (southamerica, europe, africa, asia, americas, ...)
    <slug>.<type>.json       one file per country per finding-type (updates|qa|wiki|entity|monitor|newterminals|newunits)
    <slug>.*.done.json       resume markers — checkpoints only, see lifecycle note below
    _build/                  assembled staged_*.json that build_review_package.py consumes (derived — gitignored)
  recon/<report><year>/      per-edition reconciliation dir (e.g. recon/giignl2026/)
    giignl_extracted.csv     ┐ derived from the data/ PDF + scripts — gitignored, re-derivable
    giignl_diff.json         │
    giignl_fsru_fleet.json   ┘
    giignl_prose_corrections.json   ┐ agent-authored — COMMITTED (audit trail; the build silently
    staged_match_overrides.json     │ drops sheets if these go missing at rebuild time). prose_corrections
    giignl_narrative_findings.json  │ + match_overrides feed report_diff.py (re-pin/reclassify the diff —
    staged_*.json                   ┘ regen the diff first); staged_* feed the build's --inputs-dir
                                      (recon verdicts, report-only resolutions, match overrides, entity adds, qa, ...)
  <scope-slug>/              ad-hoc single-scope update/discovery batch (e.g. japan/, qatar/)
    staged_*.json            agent-authored staging written directly — COMMITTED; the build's --inputs-dir
```

(Pre-sweep one-off batches — the ChatGPT-audit import and the 2026-06-02 Egypt batch — lived in a
`_prior/` dir here; it was removed from HEAD on 2026-06-09 and remains recoverable from git history.)

**Done-marker lifecycle:** `<slug>.done.json` / `<slug>.disc.done.json` / `<slug>.reverify.done.json`
are resume checkpoints only — the dispatch tooling (`_reverify_state.py`, `_build_region.py`) treats
marker-present as "country done" while a sweep is in flight. Once a sweep is confirmed complete
(`SWEEP_PROGRESS.md` is the durable record), delete its markers — don't let them accumulate. The
substantive `<slug>.<type>.json` research files are the audit trail and stay committed.

Principle: **commit what can't be re-derived (agent-authored research), gitignore what can (derived
extracts/diffs/assemblies).** The `.gitignore` re-include rules encode exactly this split.

## Run a region (sweep)

```bash
# 1. (subagents write batches/staging/<region>/<slug>.<type>.json per _country_agent_brief.md;
#     the dispatch prompt states the tier — standard default, exhaustive for full re-verification)
python batches/staging/_assemble.py <region>
python scripts/build_review_package.py --mode update \
    --inputs-dir batches/staging/<region>/_build --gem-csv scripts/gem_export.csv \
    --output batches/lng_terminals_batch_$(TZ=America/New_York date "+%Y%m%d_%H%M_ET")_<region>_update.xlsx
python scripts/recalc.py <the output xlsx>
# if the region produced monitor/new candidates (per _assemble.py's discovery_mode_needed line),
# ALSO run a --mode discovery build BRACKETED by the monitor roll-forward (workflows.md §5 step 4):
python scripts/monitor_store.py seed batches/staging/<region>/_build
python scripts/build_review_package.py --mode discovery \
    --inputs-dir batches/staging/<region>/_build --gem-csv scripts/gem_export.csv \
    --output batches/lng_terminals_batch_$(TZ=America/New_York date "+%Y%m%d_%H%M_ET")_<region>_discovery.xlsx
python scripts/recalc.py <the discovery xlsx>
python scripts/monitor_store.py update batches/staging/<region>/_build --batch <stamp>
```

## Run a reconciliation (per edition)

```bash
# extract / diff / fsru-fleet / prose-corrections all into batches/staging/recon/giignl<YEAR>/
# (full recipe: docs/workflows.md §1), then:
python scripts/build_review_package.py --mode reconciliation --report giignl --year <YEAR> \
    --inputs-dir batches/staging/recon/giignl<YEAR> --gem-csv scripts/gem_export.csv \
    --extracted-csv batches/staging/recon/giignl<YEAR>/giignl_extracted.csv \
    --output batches/lng_terminals_batch_$(TZ=America/New_York date "+%Y%m%d_%H%M_ET")_giignl<YEAR>_reconciliation.xlsx
```

## xlsx naming

Every deliverable: `batches/lng_terminals_batch_<YYYYMMDD>_<HHMM>_ET[_<scope>]_<mode>.xlsx` — the
`<mode>` token (`update` / `exhaustive_update` / `discovery` / `reconciliation`; an exhaustive-tier
Update batch uses `exhaustive_update` even though it still builds with `--mode update`) is always
present; the `<scope>` slug (country, region, or report edition) whenever the batch is scoped. Pre-2026-06 files used `[_<region>]`
without the mode token for update builds — they are not renamed.

## Git note

The staging tree (`batches/staging/**`) **is committed** — it's the diffable audit trail of each batch
(per-country research JSON, per-edition recon staging, ad-hoc staged_*.json, the `SWEEP_PROGRESS.md`
ledger, the briefs, this README). `.gitignore` ignores only the large regenerable `*.xlsx` deliverables
one level up, the derived recon artifacts (extracted CSV / diff / FSRU fleet), and the derived `_build/`
`staged_*.json` — with re-include rules for the agent-authored `recon/**` and `<scope-slug>/`
staging. Durable knowledge still graduates elsewhere: country findings → `docs/country_notes/`, tooling
fixes → `scripts/`. Cross-batch monitor state lives in `monitor_list/` (committed, not here).
