# 2026-08-02 — captive-power coverage-gap closure + full-region EVERYTHING rebuild

## Plan

User directive (2026-08-01, `batches/staging/captive_power/_kickoff_coverage-gap.md`):
(1) research the coordinate-first audit's uncrawled set — 156 americas terminals +
1 europe terminal (Port of Vlora FSRU 2); (2) rebuild ALL regional captive-power
workbooks as comprehensive EVERYTHING files (all live increments merged per region);
(3) upload the four workbooks to the shared Drive folder
(`1AW4LOVCF63NBLdo0UAVZ1_fxe60KeOnc`).

## Status / what ran

- Fresh 2026-08-01 pull; `captive_coverage_audit.py --csv` regenerated `worklist.json`
  scopes (terminal_id lists, not country lists) for `americas-gap` + `europe-topup`.
- Neighbors: `_compute_neighbors.py` per dir (whole-country GOGPT pulls, 30 km cap,
  `gogpt_plant_id` on every row). Freeport/Texas LNG re-researched (2026-07-10 TX
  verdicts were memo-only and lost — dispatch carried research_hints, not ports).
- 23 research shards (max 8 terminals each) + orchestrator QC gate:
  - 9 mechanical adjudication patches (NO→INSUFFICIENT ×6 under fuel-gate/Hadera
    FSRU convention; NO→SCREENED ×2 cancelled-never-designed; Neptune
    INSUFFICIENT→YES green on the EPA deepwater-port application).
  - FSRU evidence-standard harmonization (2 agent dispatches): operator fleet
    disclosure = primary for its own vessels → green (Barcarena, Manzanillo DR,
    Bahía Blanca, Escobar); third-party single source → yellow (Old Harbour);
    BW Magna stays INSUFFICIENT (search exhausted).
  - Freeport adjudicated YES green (EPA NPDES TX0134056 + operator page + trade
    press; infrasure.ai and worldpowerplants.com rejected as GEM-derived/uncorroborated).
- Assembly: `_assemble_americas_gap.py` → 45 staged unit-rows / 27 YES terminals,
  179 qa rows, 156 terminal_first, 186 neighbors. `_assemble_europe_topup.py` → 1
  terminal INSUFFICIENT, 0 staged, 2 qa rows.
- Full-region merge: `_merge_full_regions.py` → `_build/<region>/` (americas 148
  staged rows, europe 64, asia 56, middle-east-gulf 26; duplicate assertions clean).
- First build (stamp 20260802_1141_ET) tripped REF-DROP guards (12 URLs, americas 6
  records + europe 6) — stale merges vs the fresh export. Fixed `audit_ref_drops.py`
  glob blind spot (`staged_updates.json` never matched), restored 10 live URLs,
  declared the rest (`dropped_urls_dead`, incl. the Argentina LNG wrong-terminal
  Argent-LNG contamination, flagged in qa_review), re-merged, rebuilt.

## Outcome

- **Deliverables: the four `batches/lng_terminals_batch_20260802_1145_ET_
  {americas,europe,asia,middle-east-gulf}-captive_update.xlsx`** — guard-clean,
  recalc clean, 81 tests pass. They supersede every earlier captive workbook; the
  1141 intermediate set left in `batches/` for pruning.
- New-corpus verdicts (157): **27 YES / 12 NO / 63 INSUFFICIENT / 55 SCREENED**;
  45 staged unit-rows (35 green / 10 yellow), zero overturns, 8 mechanical=True
  terminals (incl. Cameron + Lake Charles).
- Final coverage audit **PASSED**: 739/843 crawled; americas + europe fully closed;
  the 104 uncrawled are exactly the declared pending increments africa (67) +
  oceania (37).
- Memo: `batches/captive_power_memo_20260802_1148_ET_coverage-gap.md` (adjudication
  precedents, Argentina LNG ref contamination, Energos Winter→Damietta, GOGPT
  candidates: 1 ADD Port Pelican / 3 MAYBE / 21 REVIEWER CALL).
- Workbooks uploaded to the shared Drive folder (user-authorized write in the
  kickoff directive).
- Permanent repo fixes this run: `audit_ref_drops.py` glob; (prior session, same
  batch arc) `url_verifier.py` Incapsula-challenge detection.
