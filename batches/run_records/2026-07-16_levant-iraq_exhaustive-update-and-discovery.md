# 2026-07-16 — Cyprus / Iraq / Israel / Jordan / Lebanon exhaustive update + discovery

## Plan

User request: "run the same research process that you did for vietnam, philippines, and thailand, but for THESE countries: Cyprus, Iraq, Israel, Jordan, Lebanon."

- **Exhaustive-tier Update** (Update SOP §2.2) + **Discovery** per country, as a scoped multi-country sweep (`docs/workflows.md` §5) under scope slug `levant-iraq`.
- One research subagent per country on Sonnet, each writing `batches/staging/levant-iraq/<slug>.<type>.json` (+ `.disc.` variants per the two-book non-overlap rule).
- Merge via `_assemble.py levant-iraq` → `build_review_package.py`; discovery build with `--checked-roster` and bracketed by `monitor_store.py seed`/`update`.

## Environment / setup

- Fresh GEM pull at batch start (2026-07-16 10:13): 1,268 unit rows, colmap re-derived (115 cols).
- Tool health verified live: `fetch_timeline.py` (readonly_postgres), `entity_lookup.py --remote`, `url_verifier.py` all healthy. Subagents instructed to STAGE confirmed status changes (never punt).
- A fresh scope dir (`levant-iraq/`) was used rather than reusing `middleeast/` — the June full-tracker sweep files there are already applied and must not re-merge.

## Scope

15 terminals / 15 unit-rows: Cyprus 3 (Cyprus FSRU construction; Cyprus LNG Terminal, Hoegh Cyprus FSRU both cancelled), Iraq 2 (Al-Faw FSRU, Khor Al-Zubair FSRU — both proposed), Israel 4 (Hadera FSRU idle; NewMed FLNG proposed; Eilat + Tamar FLNG cancelled), Jordan 2 (Aqaba Jordan FSRU operating; Sheikh Sabah LNG Terminal), Lebanon 4 (Deir Ammar proposed; Beddawi + Selaata cancelled; Zahrani shelved).

## Per-country outcomes

- **Cyprus** — 29 updates (10 green / 4 yellow / 15 blue), 5 qa, 2 wiki, 1 monitor (Energean FLNG-at-Vasilikos concept), 0 new. Cyprus FSRU (Vasilikos/ETYFA, Prometheas) blank-ref backfills + re-verification of the long-troubled construction status.
- **Iraq** — 23 updates (7 green / 16 blue), 5 qa + 3 disc.qa, 2 wiki, 1 entity (South Gas Company — new; Al-Faw owner). Khor Al-Zubair: FloatingVesselName filled with Excelerate Acadia (named 2026-03-31, ex-Hull 3407); project delayed by Iraqi payment failures — vessel meanwhile chartered to Jordan (see conflict adjudication below).
- **Israel** — 38 updates (11 green / 1 yellow / 26 blue), 4 qa, 1 wiki, 0 new. NewMed FLNG capacity corrected 7.00 bcm/y → 4.6 mtpa (paired CapacityUnits change; 2019 range superseded by settled figure). Hadera StopYear 2022 filled (Excelsior departure). Jan-2026 Leviathan Phase 1B FID clarified as pipeline expansion, NOT the FLNG (ResearcherNotesUnit).
- **Jordan** — 21 updates + 2 timeline, 5 qa, 2 wiki, 1 entity (Aqaba Development Corporation — new; Sheikh Sabah owner). Aqaba FSRU vessel chain updated Eskimo→Force→**Excelerate Acadia** (arrived ~22 Jun 2026, 9-month NEPCO charter), Operator → Excelerate Energy, PlannedStopYear 2025→2026 (+ timeline retired/planned re-anchor). Sheikh Sabah proposed→construction (yellow; Aug-2024 EPCIC award + Oct-2025 site-visit evidence; timeline appended) with capacity re-expressed 0.72 bcf/d → 5.52 mtpa.
- **Lebanon** — 25 updates (2 green / 12 yellow / 11 blue) + 1 timeline, 5 qa, 1 wiki, 1 monitor (Block 8/9 upstream watch), 0 new. Zahrani shelved→cancelled (inferred 4y; last activity 2022) staged with timeline + anchor year.

Zero new terminals anywhere; discovery sweeps (regulator, trade press, Arabic-language, gem.wiki cross-check, dormant-revival) all resolved to existing GEM records.

## Cross-country conflict adjudicated — Excelerate Acadia (kept BOTH)

Jordan and Iraq agents each staged "Excelerate Acadia" as their terminal's FloatingVesselName. Not a contradiction: the vessel was built for Iraq's Khor Al-Zubair (definitive agreement Oct-2025, named 2026-03-31), but Iraq-side payment delays led NEPCO to charter it for 9 months (executed 2026-05-05); it arrived at Aqaba ~2026-06-22. Current deployment (Aqaba) and contracted designation (Khor Al-Zubair, proposed) are both true, green-sourced from independent outlets, with qa notes on both sides documenting the shared vessel; no IMO fields staged, so no sync collision. Reviewer sees both qa notes.

## Guardrails / QC (merge-time gate)

- Marker completeness: all 10 done markers present (5 update + 5 discovery).
- gem.wiki / globalenergymonitor.org: zero citations (7 grep hits were disc.qa prose describing the mandated coverage cross-check).
- Entity dedup vs read-only Postgres `entity_history`: South Gas Company and Aqaba Development Corporation both genuinely absent (LIKE scans incl. `%aqaba%`, `%south gas%`) → both stand as new.
- Field-name validation: all 136 update records' `field_name`/`ref_field` match the fresh CSV header row exactly.
- URL routing: zero URLs staged into non-ref columns.
- URL spot-check (8 verifier runs, actual claimed values as tokens): 6/6 core citations PASS. **Caught: both NewMed FLNG Capacity refs were 404** (truncated mees.com date-index URL + garbled enerdata slug). Fixed at orchestrator level: replaced with two verified independent sources (enerdata correct slug + LNG Prime 67243, both PASS on "4.6") across the 4 affected Israel records; green retained.
- Timelines (3): all pulled the Postgres timeline first with legal-transition checks (Sheikh Sabah construction/2024; Aqaba retired-planned re-anchor 2026; Zahrani cancelled inferred-4y/2026 — shelved→cancelled legal per lifecycle_rules).
- FSRU sync: `fsru_sync_check.py` gem_only mode (337 GEM FSRUs), carrier backend absent → graceful short-circuit.

## Assembled totals & deliverables

- Assembled: **136 updates, 3 timeline, 24 qa (+17 disc.qa), 8 wiki, 2 entity, 2 monitor, 0 new terminals/units**, 15 scope terminals.
- Workbooks (recalc OK, zero formula errors):
  - `batches/lng_terminals_batch_20260716_1049_ET_levant-iraq_exhaustive_update.xlsx`
  - `batches/lng_terminals_batch_20260716_1049_ET_levant-iraq_discovery.xlsx` (monitor store: 31 prior + 2 new = 33 total, 0 promoted; prior entries filtered out of the sheet by checked-roster — none were in these 5 countries)
- Staging committed under `batches/staging/levant-iraq/`; done markers pruned now the run is recorded here.
