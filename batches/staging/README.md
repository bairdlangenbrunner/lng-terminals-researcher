# Batch staging — country-sweep working area

This directory holds the **staging inputs** for batch builds: the per-country research JSON that
`build_review_package.py` assembles into the reviewable `.xlsx` deliverables one level up in `batches/`.
It is the scaled, multi-country form of the **Update workflow** in the repo `CLAUDE.md` (one research
subagent per country, fanned out, then merged per region into one staging workbook).

> Formerly `chatgpt_audit_batch/sweep/` — renamed to a workflow-neutral name. The original ChatGPT-audit
> import was just the first batch run through this machinery; the structure is reused every cycle.

## Layout

```
batches/staging/
  SWEEP_PROGRESS.md          ledger / checkpoint — read this first to resume a sweep
  _country_agent_brief.md    the brief each per-country UPDATE subagent reads
  _discovery_brief.md        the brief for discovery-sweep subagents
  _assemble.py               merges <region>/*.<type>.json → <region>/_build/staged_*.json
  <region>/                  per-region working dir (southamerica, europe, africa, asia, americas, ...)
    <slug>.<type>.json       one file per country per finding-type (updates|qa|wiki|entity|monitor|newterminals|newunits)
    _build/                  assembled staged_*.json that build_review_package.py consumes
  _prior/                    pre-sweep one-off batches, kept for provenance
    audit_import/            the original ChatGPT-audit import (US/Algeria/Australia → batch 0030)
    egypt/                   the one-off Egypt batch (→ batch 1833 on 2026-06-02)
```

## Run a region

```bash
# 1. (subagents write batches/staging/<region>/<slug>.<type>.json per _country_agent_brief.md)
python batches/staging/_assemble.py <region>
python scripts/build_review_package.py --mode update \
    --inputs-dir batches/staging/<region>/_build --gem-csv scripts/gem_export.csv \
    --output batches/lng_terminals_batch_$(TZ=America/New_York date "+%Y%m%d_%H%M_ET")_<region>.xlsx
python scripts/recalc.py <the output xlsx>
# if the region produced monitor/new candidates, also build --mode discovery into a _<region>_discovery.xlsx
```

## Git note

The staging tree (`batches/staging/**`) **is committed** — it's the diffable audit trail of each sweep
(per-country research JSON, the `SWEEP_PROGRESS.md` ledger, the briefs, this README). `.gitignore` tracks it
and ignores only the large regenerable `*.xlsx` deliverables one level up, plus the derived `_build/` /
`_prior/` `staged_*.json` (via the `staged_*.json` rule). Durable knowledge still graduates elsewhere:
country findings → `docs/country_notes/`, tooling fixes → `scripts/`. Cross-batch monitor state lives in
`monitor_list/` (committed, not here).
