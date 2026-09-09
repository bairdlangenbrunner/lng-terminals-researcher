# Kickoff — captive-power cross-tracker: Middle East/Gulf (+ Americas residue)

Stage directions for the session that runs the fifth captive-power regional increment.
Written 2026-08-01 at the close of the Asia batch. Read this whole file before dispatching.

## Scope

**Primary: Middle East/Gulf — 11 countries, 34 terminals** (counts from the 2026-07-31 pull;
re-derive from the fresh pull at session start):
Bahrain 1, Iran 7, Iraq 2, Israel 4, Jordan 2, Kuwait 2, Lebanon 4, Oman 2, Qatar 3,
United Arab Emirates 6, Yemen 1. (Türkiye was covered in europe; Turkmenistan in asia;
Egypt belongs to the future africa increment.)

**Mandatory second scope: Americas residue — 8 countries, 11 terminals.** Coverage audit
2026-08-01 found these were NEVER crawled by any americas increment (absent from
`americas-complete/captive_terminal_first.json` and from every meta.json `countries` list):
Antigua and Barbuda (Antigua Power), Aruba, Bahamas (Clifton Pier, Island Power Producers,
Ocean Cay), Ecuador (Jambelí FSRU, Monteverde Pacific), Haiti (Maurice Bonnefil), Honduras
(Puerto Cortés), Nicaragua (Puerto Sandino FSRU), Uruguay (GNL Del Plata FSRU). Run them in
this session but as a SEPARATE staging dir + workbook (`captive_power/americas-residue`) so
scope slugs and applied-tracking stay clean. Expect the Caribbean direction-test pattern
(terminal feeds a power station → `PowerPlantsSupplied` territory, NOT captive), but research
each — Antigua Power/Clifton Pier-style plants colocated with their own import jetty are
exactly where onboard/on-site gas gensets show up.

## Read first (in this order)

1. Project CLAUDE.md router entry + `docs/workflows.md` §9 (command recipe).
2. `docs/sops/captive_power.md` — especially §2/§2a/§2b (no MW floor, no duty floor, fuel
   gate, STANDBY = YES), §2c (`hybrid_basis`), §2d (`captive_category` + `hardware_summary`,
   per-unit-row), §3/§3a (staging + the three review tabs), §4a (Natalia's GOGPT screen).
3. `batches/staging/_captive_power_brief.md` (the dispatch brief agents receive).
4. The asia increment as the working template: `batches/staging/captive_power/asia/`
   (`_assemble_asia.py`, `_enrich_neighbor_ids.py`, `dispatch/`, `shard_results/`, meta.json)
   and its run record `batches/run_records/2026-07-31_captive-power-asia.md`.

## Standing rules that have bitten before (do not relearn these)

- **The three staged-row `gogpt_*` columns TRAVEL TOGETHER** (SOP §3, user directive
  2026-08-01 after the Asia build shipped 35 named-but-id-blank rows): any record naming a
  plant in `gogpt_plant` MUST carry its `gogpt_plant_id`. GOGPT's own `captive` flag is
  irrelevant to filling the id. Keep `GogptPlant.plant_id` in the neighbors computation FROM
  THE START (asia dropped it and needed a backfill script); make the assembler assert it.
- **Edit lane: `CaptiveGasPower` (+ ref) ONLY — never `PowerPlantsSupplied`.** Direction
  test on every terminal.
- **Ref MERGE, never replace** — pre-existing True re-verifications carry existing ref URLs
  forward (asia: Hatsukaichi, MLNG Tiga). Check the fresh CSV for terminals already True.
- **No MW floor, no duty floor; only the fuel gate screens** (gas/dual-fuel/BOG = counts,
  diesel-only = NO, fuel unstated = INSUFFICIENT — FSRU onboard gensets with no published
  fuel spec stay INSUFFICIENT, the BW Batangas class). A documented positive never loses to
  an inferred figure; absence of a spec is INSUFFICIENT, never NO.
- **A NO must point at a source** (equipment enumeration meant to be complete for the
  question, or an explicit power-supply statement); SCREENED must be evidenced (never-built
  = the only legitimate screen basis); no class-precedent inference (an EPC's own published
  design for a confirmed project is allowed — West Papua FLNG precedent).
- **Single-source green only on primary/regulatory** — expect this to carry the region:
  Gulf-state environment agencies, FSRU class records (this region should behave like
  India, where EIA filings enumerate power systems verbatim).
- Banned everywhere: gem.wiki / globalenergymonitor.org citations (nav-only columns
  excepted), abarrelfull, bare homepages, mirror-padding. Every URL through
  `scripts/url_verifier.py` with the claimed value as token.
- **Not `--subnational`** — country-scope pulls (`Country/Area` on the LNG side,
  `by_country=True` on GOGPT) so blank-area records can't drop out.

## Session shape (mirror asia; recipe details in workflows §9)

1. `python scripts/coverage_status.py`; fresh pull (`gem_query.py --all-fields lng` +
   `pull_gem_db.py --map-only` from `scripts/`).
2. Create `batches/staging/captive_power/middle-east-gulf/` and `…/americas-residue/` each
   with meta.json at creation (schema: `batches/staging/README.md`).
3. Deterministic priors per country: `captive_power_colocation.py --country` worklists +
   colocation CSVs to `batches/deliverables/`.
4. Neighbors: nearest-2 GOGPT per terminal, 30 km cap, whole-country pulls — WITH plant_id.
5. Shard dispatch: max ~8 terminals/shard (ME/Gulf ≈ 5–6 shards, residue ≈ 2), cheapest
   good-enough model (sonnet), brief = `_captive_power_brief.md` + per-shard worklist.
   Expect the shared WebSearch pool to exhaust; the WebFetch/DDG fallback chain is normal.
   Plan a recovery pass for budget-starved terminals as a standard phase, superseding by
   terminal_id.
6. Orchestrator QC gate: adversarial re-verify of any overturn, citation/banned-domain/
   bare-URL sweeps, fuel-gate audit of every NO, screened-evidence audit, terminal_id
   validation against the fresh CSV (asia caught an agent typo).
7. Assemble via a committed `_assemble_<scope>.py` per dir (copy asia's, keep the
   plant_id assertion); build each workbook with a fresh stamp:
   `batches/lng_terminals_batch_<stamp>_middle-east-gulf-captive_update.xlsx` and
   `…_americas-residue-captive_update.xlsx`; `recalc.py`; run tests.
8. Memo(s) + run record(s) + meta.json updates + update the
   `captive_power_colocation_workflow` memory (per-region progress lives there).
9. `fsru_sync_check.py` for any FSRU touched (graceful gem-only skip is fine).

## Context for the GOGPT side (Natalia)

She applied the EU+Americas GOGPT additions 2026-07-31 and plans "the rest of the world"
from Monday 2026-08-03 — so this increment's `gogpt_candidates` tab is time-relevant.
Carry per-unit tech (aeroderivative/frame/genset), per-unit MW, plant total, and status so
her screen (no cancelled; sub-20 MW units only when plant ≥20 MW EU / ≥50 MW Russia — her
thresholds, hers to apply) runs without re-research. A post-2026-07-31 GOGPT pull already
contains her additions: an existing record = `DO NOT ADD`. The dominant open class from
asia — vessel-mounted FSRU/FSU generation — will recur heavily here (Gulf FSRUs);
keep it REVIEWER CALL, the floating-plant ontology decision is tracker-side.

## After this increment

Remaining: **Africa** (~60 terminals incl. Egypt — the upstream-oil-operator FLNG sweep
rule applies, see [[oil_operator_flng_sweep]]), then **Oceania** (Australia 28 + PNG 7 +
NZ 1 + Timor-Leste 1 — liquefaction-heavy, expect the mechanical-drive family). Queued
follow-ons from asia, NOT this session's scope: China 环评-retrieval mini-pass (40
INSUFFICIENTs), the 155 update-batch flags (POSCO Dangjin, Haiphong, LMPT2, Kiyanly…).
