# Run record — full-tracker sweep: standard update + discovery (2026-06-03)

One md per major run lives in `batches/run_records/` so you can see at a glance what was last done, when, and with what scope. This file is the plan + final outcome for this run; fine-grained per-country state lives in `batches/staging/SWEEP_PROGRESS.md`.

## What this run is

- **Date started:** 2026-06-03 (afternoon ET)
- **Workflows:** standard-tier Update + Discovery, every country in the GEM tracker, organized by the 6 staging regions, one subagent per country per mode, parallel.
- **Supersedes:** the comprehensive sweep completed earlier on 2026-06-03 (workbooks `…1241_ET_*` / `…1258_ET_*`). That sweep predated the standard/exhaustive tier split (commit `0ce5472`); its per-country staging JSONs were archived to `batches/staging/_prior/sweep_20260603_full/` (git history + archive preserve the audit trail).
- **User decisions:** supersede (not top-up); discovery scope = **tracker countries only** (no coverage_gap expansion); standard tier; resumable at per-country granularity.
- **Methodology doc:** fetched into session context from Google Drive (doc `18BvRBWLhXVgj92y5XOv98Co1QtMFj3ny20pmN9XbDko`), "Last updated: Baird and Rob, May 2026".

## Status

| Region | Status | Update workbook | Discovery workbook |
|---|---|---|---|
| europe | **DONE** (upd 24/24, disc 28/28) | `…_1925_ET_europe_update.xlsx` (55 upd / 104 qa / 18 wiki / 2 entity; recalc OK) | `…_1952_ET_europe_discovery.xlsx` (2 new terminals / 1 new unit / 9 entity / 14 monitor / 55 qa; recalc OK) |
| africa | **DONE** (upd 21/21, disc 25/25) | `…_1925_ET_africa_update.xlsx` (54 upd / 68 qa / 5 wiki / 2 entity; recalc OK) | `…_1952_ET_africa_discovery.xlsx` (5 new terminals / 15 entity / 18 monitor / 49 qa; recalc OK) |
| americas | **DONE** (upd 29/29, disc 25/25) | `…_0746_ET_americas_update.xlsx` (137 upd / 118 qa / 17 wiki / 4 entity; recalc OK) | `…_0748_ET_americas_discovery.xlsx` (7 new terminals / 12 entity / 13 monitor / 47 qa; recalc OK) |
| asia | **DONE** (upd 24/24, disc 19/19) | `…_0807_ET_asia_update.xlsx` (141 upd / 149 qa / 13 wiki / 2 entity; recalc OK) | `…_0807_ET_asia_discovery.xlsx` (2 new terminals / 1 new unit / 4 entity / 18 monitor / 32 qa; recalc OK) |
| middleeast | **DONE** (upd 9/9, disc 12/12) | `…_0814_ET_middleeast_update.xlsx` (24 upd / 25 qa / 2 wiki / 2 entity; recalc OK) | `…_0814_ET_middleeast_discovery.xlsx` (3 new terminals / 1 new unit / 5 entity / 3 monitor / 16 qa; recalc OK) |
| oceania | **DONE** (upd 6/6, disc 4/4) | `…_0820_ET_oceania_update.xlsx` (13 upd / 20 qa; recalc OK) | `…_0820_ET_oceania_discovery.xlsx` (1 new terminal / 1 entity / 2 monitor / 6 qa; recalc OK) |

(Updated live as regions complete. DONE = workbook built + recalc'd + ledger checkpointed.)
**23:30-ET limit note (2026-06-03 19:25):** both UPDATE workbooks above are FINAL (every update agent finished). Outstanding work — discovery remainder (europe 16, africa 8) + all of americas/asia/middleeast/oceania — needs subagent dispatch, which is throttled by the session limit until 23:30 ET. Exact missing-slug lists live in the RE-SWEEP region table of `batches/staging/SWEEP_PROGRESS.md`; dispatch args are staged at `/tmp/sweep_args_{americas,asia,middleeast,oceania}.json` and `/tmp/sweep_args_{europe,africa}_discremainder.json`.

## Mechanics (for resume / future reference)

1. **Pre-flight:** fresh export (cwd=`scripts/`: `python gem_query.py --all-fields lng -o gem_export.csv && python pull_gem_db.py --map-only` — NB the bare `gem_all_fields.py -o` is a silent no-op); `dedup_index.py`, `stale_sweep.py`, `completeness_sweep.py`; per-country worklists split to `scripts/work/sweep/<region>/<slug>.worklist.json`; prior staging archived; briefs updated with done-marker + `.disc` slug conventions.
2. **Dispatch:** one Workflow invocation per region (update agents for countries with non-empty worklists + discovery agents for all tracker countries, ≤8 concurrent). Update agents use `batches/staging/_country_agent_brief.md` ({{TIER}}=standard); discovery agents use `_discovery_brief.md` with output slug `<slug>.disc`. Every agent writes its done marker (`<slug>.done.json` / `<slug>.disc.done.json`) LAST.
3. **Per-region build:** `python batches/staging/_assemble.py <region>` → `build_review_package.py --mode update` (+ `--mode discovery` iff `discovery_mode_needed: True`) → `recalc.py` → FSRU grep gate → `fsru_sync_check.py` if hits → ledger checkpoint.
4. **Resume recipe** (fresh session, tokens ran out): read the RE-SWEEP section of `batches/staging/SWEEP_PROGRESS.md`; reuse `scripts/gem_export.csv` + `scripts/work/` if dated this run; archive step already done iff `_prior/sweep_20260603_full/` exists; for the first non-DONE region dispatch ONLY countries missing their done marker; post-process when all markers present; continue down the table.

## Outcome

**COMPLETE 2026-06-04 ~08:20 ET.** All 6 regions swept (standard-tier update + tracker-only discovery), ~240 country/shard agents. The sweep spanned three session-usage-limit windows (resets 6:30pm, 11:30pm, 12:20am) plus one server-side rate-limit incident — every interruption was resumed cleanly off the done-markers + ledger, with zero lost research.

**12 workbooks** (each region × update + discovery; all recalc-clean, all under `batches/`):
- europe: `…_1925_ET_europe_update.xlsx` · `…_1952_ET_europe_discovery.xlsx`
- africa: `…_1925_ET_africa_update.xlsx` · `…_1952_ET_africa_discovery.xlsx`
- americas: `…_0746_ET_americas_update.xlsx` · `…_0748_ET_americas_discovery.xlsx`
- asia: `…_0807_ET_asia_update.xlsx` · `…_0807_ET_asia_discovery.xlsx`
- middleeast: `…_0814_ET_middleeast_update.xlsx` · `…_0814_ET_middleeast_discovery.xlsx`
- oceania: `…_0820_ET_oceania_update.xlsx` · `…_0820_ET_oceania_discovery.xlsx`

**Totals:** 424 update edits · 55 wiki updates · 484 update-side QA notes · 23 new terminals/units (discovery) · 46 entity additions · 68 monitor items · 205 discovery-side QA notes.

**Escalations (4)** — all small-scale / modular-LNG clusters raising the same methodology-scope question (does GEM track sub-MTPA modular/receiving LNG?); each handled per protocol as monitor + `escalation=true` and the agent CONTINUED — none auto-added, all await a human scope decision:
- **Norway** — Ålesund/Bingsa + ~30 Gasnor coast-wide small-scale receiving terminals
- **Nigeria** — 5-plant Ajaokuta mini-LNG liquefaction cluster (~97.5 mmscfd)
- **Indonesia** — 6 monitor items
- **Japan** — 3 monitor items

**Entity-dup leads:** 46 entity additions staged, every one with `entity_lookup` RUN; many returned inconclusive (e.g. XRG/ADNOC, SNPC, Knutsen, Excelerate, HELLENiQ, DEPA/AKTOR) — flagged in the `entity_additions` sheets for the reviewer to confirm against existing GEM entities before creating, per the no-duplicate-entities rule.

**Routed to follow-up (recurring patterns the reviewer should action):**
- **Status transitions deferred to QA** because `fetch_timeline` is DOWN (404) — many real proposed→construction / construction→operating moves are status_timeline QA notes, not staged Status edits (e.g. Manzanillo DR now operating, Dahej P2 commissioned, Ravenna operating, Iraq Khor Al-Zubair advancing, Mozambique LNG restart + Coral North FID). Each needs a manual Status + timeline apply.
- **Stale FIDYear anchors** flagged (Etinde, GTA Phase 2 — record FIDs that never happened).
- **Inferred-status blank `[ref]` cells** (the bulk of the 1,158 blank-ref worklist) were largely left blank by design — GEM editorial inferences with no citable external source; filling would create orphan/circular refs. Surfaced in QA, not fabricated.

**FSRU sync:** short-circuited on every build (no carrier backend connected) — expected per CLAUDE.md; no `fsru_sync` mismatches to action.

**Repo improvement this run:** fixed a latent `_assemble.py` bug (never cleared stale `staged_*.json`, leaking update-side wiki into discovery-mode builds); it now purges on each run. Two contaminated africa/europe discovery workbooks were rebuilt and the bad files deleted.

**Note:** ~580 staged per-country JSONs (this sweep's audit trail) + the prior sweep archived under `_prior/sweep_20260603_full/` are uncommitted — left for the user to commit.
