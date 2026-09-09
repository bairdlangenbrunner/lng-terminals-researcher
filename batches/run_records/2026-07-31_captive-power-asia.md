# 2026-07-31 — captive-power cross-tracker, Asia (19 countries)

## Plan

Fourth regional increment (after us-gulf → americas-complete, europe). Scope: all 19 Asian
countries with LNG terminals — 316 terminals / 458 unit-rows, the largest area yet. Terminal-first
crawl per SOP `docs/sops/captive_power.md` + workflows §9: fresh pull, per-country deterministic
priors, 45 dispatch shards (max 8 terminals each), general-purpose sonnet subagents with the
WebFetch-fallback search block, LNG-side edits only (`CaptiveGasPower` + ref, never
`PowerPlantsSupplied`).

## Status / how it ran

- 45/45 primary shards completed across two sessions (session-limit stoppage mid-run 07-31;
  resumed after the 6pm ET reset — shard 35 proved already complete on disk; 32/37/38
  re-dispatched with hints recovered from the transcript).
- WebSearch quota exhausted early (200/200 shared pool); all shards ran on the
  DuckDuckGo/Bing-RSS WebFetch fallback chain.
- **Recovery pass**: 51 budget-starved terminals re-dispatched in 8 shards (China ×5,
  Bangladesh/India/Japan, misc, BW Batangas solo). Recovery results supersede primary entries by
  terminal_id at assembly. Yield: +4 YES (Summit FSRU, Gopalpur, Karaikal FSRU, West Papua FLNG),
  +12 sourced NO, 1 SCREENED; the rest honest INSUFFICIENTs.
- **QC gate**: both pre-existing-True overturns (Palu, Chana) adversarially re-verified and upheld
  (`qc_overturn_verification.json`); Fukuoka re-graded SCREENED→NO; MCV re-graded
  NO→INSUFFICIENT (fuel gate); Tiga FLNG terminal_id typo fixed; 4 citation repairs (2 bare
  homepages replaced, Map Ta Phut 1 green→yellow, Dahej corroborated); banned-domain/bare-URL
  sweep clean; `fsru_sync_check.py` ran gem-only (graceful skip, no carrier backend).
- Assembly via committed `batches/staging/captive_power/asia/_assemble_asia.py` (reproducible from
  `shard_results/`): 5 canonical staging JSONs incl. a 440-row neighboring_plants tab computed
  from the GOGPT Postgres (nearest-2, whole-country pulls, 30 km cap).

## Outcome

- Verdicts (316): **30 YES / 117 NO / 88 INSUFFICIENT / 81 SCREENED**. Zero YES in 11 countries
  incl. all 32 Vietnam terminals (direction-test dominance).
- Workbook: `batches/lng_terminals_batch_20260801_1136_ET_asia-captive_update.xlsx` — 56 staged
  unit-rows / 32 terminals (54 True incl. 3 re-verified True→True with merged refs; 2 True→False
  overturns Palu + Chana). Build clean (no GUARD/REF-DROP), recalc clean, tests 81 passed.
  (Rebuild 2026-08-01, user-caught defect: the 07-31 build left `gogpt_plant_id` blank on all 35
  rows that name a plant — the assembler only had ids wired for captive-matched records, which is
  wrong; the id identifies the plant regardless of GOGPT's captive flag. Fixed at source:
  `_enrich_neighbor_ids.py` stamps ids onto `neighbors_raw.json` from the GOGPT Postgres
  (fail-loud on unmatched), `_assemble_asia.py` asserts their presence, SOP §3 now states the
  three gogpt_* columns travel together. Verdicts/values unchanged; prune the 07-31 xlsx.)
- Memo: `batches/captive_power_memo_20260731_1933_ET_asia.md` (GOGPT candidates for Natalia:
  9 ADD / 12 MAYBE / 24 REVIEWER CALL; INSUFFICIENT landscape; 155 update-batch flags incl.
  POSCO Dangjin, Haiphong, LMPT2 ownership, Kiyanly scope question).
- Not yet applied to GEM (user reviews and pastes manually). meta.json → status `built`.
- Remaining increments: Middle East/Gulf (recommended next), Africa, Oceania. Queued follow-ons:
  China EIA-retrieval mini-pass for the 40 Chinese INSUFFICIENTs; update-batch flags.
