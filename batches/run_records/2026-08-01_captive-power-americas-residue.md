# 2026-08-01 — captive-power cross-tracker, Americas residue (8 countries)

## Plan

Mandatory cleanup scope from `_kickoff_middle-east-gulf.md`, run alongside the ME/Gulf
increment as a SEPARATE staging dir + workbook: 11 terminals across 8 countries (Antigua &
Barbuda, Aruba, Bahamas ×3, Ecuador ×2, Haiti, Honduras, Nicaragua, Uruguay) that no
americas increment ever crawled. Same SOP/mechanics as the main scope.

## Status / how it ran

- Both residue shards completed; no recovery needed. QC gate: Ocean Cay ref list mirror-
  trimmed (same-document host variants = one source); everything else clean.
- Closes the Americas: with this workbook applied, every Americas LNG terminal has been
  crawled by the captive-power workflow.

## Outcome

- Verdicts (11): **1 YES / 10 NO** (no INSUFFICIENT/SCREENED). The YES is Ocean Cay
  (cancelled AES Bimini project, design-basis 3×15 MW house-load-only generators, yellow,
  single-origin EIA trail). All 10 NOs are documented LNG-to-power direction-test findings
  (co-located plant is the offtaker, not captive generation).
- Workbook: `batches/lng_terminals_batch_20260801_1237_ET_americas-residue-captive_update.xlsx`
  — 1 staged unit-row, qa 10, priors 11, candidates 11 (10 DO NOT ADD / 1 REVIEWER CALL:
  Ocean Cay). Build clean, recalc clean.
- Memo: `batches/captive_power_memo_20260801_1239_ET_americas-residue.md` (qa flags incl.
  Clifton Pier stale status vs July-2026 groundbreaking + $379.2M financing, Puerto Sandino
  vessel discrepancy, Island Power Producers 2026 startups, Jambelí stall, Monteverde/GNL
  Del Plata blank PowerPlantsSupplied).
- Uploaded to the user's shared-Drive folder per instruction (with the ME/Gulf workbook).
  Not yet applied to GEM. meta.json → status `built`.
