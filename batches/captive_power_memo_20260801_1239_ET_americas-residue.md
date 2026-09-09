# Captive-power memo — Americas residue (8 countries)

**Stamp:** 2026-08-01 12:39 ET
**Workbook:** `batches/lng_terminals_batch_20260801_1237_ET_americas-residue-captive_update.xlsx`
**Staging:** `batches/staging/captive_power/americas-residue/`
**Cleanup scope**, built the same session as middle-east-gulf: 11 terminals across 8
countries (Antigua & Barbuda, Aruba, Bahamas ×3, Ecuador ×2, Haiti, Honduras, Nicaragua,
Uruguay) that no americas increment ever crawled — the kickoff's mandatory residue sweep.
With this workbook applied, the Americas are fully covered by the captive-power workflow.

---

## Results

| | count |
|---|---|
| terminals crawled | **11** (verdicts: **1 YES / 10 NO** — no INSUFFICIENT, no SCREENED) |
| staged unit-rows | **1** (Ocean Cay `CaptiveGasPower=True`, yellow) |
| `terminal_first_priors` | 11 |
| `gogpt_candidates` | 11 (10 DO NOT ADD / 1 REVIEWER CALL) |
| `neighboring_plants` | 14 |
| `qa_review` | 10 |
| `PowerPlantsSupplied` | 0 (never staged by this workflow) |

Build emitted no `GUARD:`/`REF-DROP:` warnings; `recalc.py` clean; shared with the ME/Gulf
build: 81 tests pass, `fsru_sync_check.py` gem_only short-circuit.

## The one YES — Ocean Cay (Bahamas, cancelled)

AES's never-built Bimini import terminal was **designed** with 3×15 MW house-load-only
generators (aggregate 45 MW, no grid tie) — a design-basis `contingency_design`-family
captive finding on a project abandoned by 2009. Single-origin sourcing (the EIA record
trail), hence **yellow**; `mechanical=False`. The gogpt_candidate is the scope's one
REVIEWER CALL (never-built, no nameplate beyond the design docs — GOGPT manual's own
cancelled-project screen likely excludes it; Natalia's call).

## Why the rest are NO — the LNG-to-power direction test

This residue population is dominated by Caribbean/Latin-American **LNG-to-power** projects,
where the co-located plant is the *offtaker* the terminal supplies (the
`PowerPlantsSupplied` direction), not the terminal's own auxiliary generation: Antigua Power
(46 MW Wärtsilä W34DF plant), Clifton Pier (BPL's 296 MW station), Island Power Producers
(70 MW SGT-800 selling to cruise ships/BPL), Aruba (WEB Balashi), Jambelí (Thermo Gas
Machala I), Puerto Sandino (NFE's 300 MW plant via dedicated pipeline), Maurice Bonnefil
(never-built 40 MW plant, separately sited), GNL Del Plata (UTE's 530 MW CCGT), Monteverde
(unnamed "thermoelectric plants"), Puerto Cortés (FSU-only truck-loading, supplies
Brassavola). All 10 NOs point at documented plant/offtake evidence — none rests on absence
of a spec.

## qa_review highlights (route to Update batches, NOT this one)

- **Clifton Pier**: GEM status looks stale — groundbreaking occurred July 2026 (Tribune242)
  and FOCOL closed $379.2M project financing; status/ConstructionYear re-check needed.
- **Puerto Sandino**: vessel discrepancy — GEM lists "Energos Princess" but 2024–2025 NFE
  reporting names a different vessel; verify and stage in an Update batch.
- **Island Power Producers**: EIA (Oct–Nov 2025) targets open-cycle July 2026 / combined-
  cycle November 2026 — startup fields worth a re-check; also a two-site (terminal vs plant)
  location question.
- **Antigua Power**: Crabbs Peninsula dredging ~98% complete as of March 2026, LNG vessel
  transits imminent — status watch.
- **Jambelí**: stalled (Sycar site unchanged as of Aug 2024 per LNG Prime) — shelved-
  inference candidate for a future Update batch.
- **Monteverde**: ARCH authorization Oct 2024 with a 5-year completion window; blank
  `PowerPlantsSupplied` despite documented thermoelectric offtake intent (as with GNL Del
  Plata) — Update-batch fill candidates.
- **Ocean Cay / Maurice Bonnefil / GNL Del Plata**: dead-project statuses re-confirmed; no
  edits needed beyond the Ocean Cay captive row.
