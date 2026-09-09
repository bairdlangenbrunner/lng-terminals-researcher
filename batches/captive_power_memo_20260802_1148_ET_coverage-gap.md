# Captive-power memo — coverage-gap closure (americas-gap + europe-topup) + full-region EVERYTHING rebuild

**Stamp:** 2026-08-02 11:48 ET
**Workbooks (the four current deliverables, one per region, ALL live increments merged):**

- `batches/lng_terminals_batch_20260802_1145_ET_americas-captive_update.xlsx` — 148 staged unit-rows (americas-complete + americas-residue + americas-gap)
- `batches/lng_terminals_batch_20260802_1145_ET_europe-captive_update.xlsx` — 64 staged unit-rows (europe + europe-topup)
- `batches/lng_terminals_batch_20260802_1145_ET_asia-captive_update.xlsx` — 56 staged unit-rows
- `batches/lng_terminals_batch_20260802_1145_ET_middle-east-gulf-captive_update.xlsx` — 26 staged unit-rows

These four supersede **every** earlier captive-power workbook (per the user's 2026-08-01
directive each regional workbook now carries EVERYTHING for its region, not just the newest
increment). The `20260802_1141_ET` set of four in `batches/` is a superseded intermediate
(REF-DROP guard triage happened between 1141 and 1145) left for pruning. Merge inputs are
reproducible via `batches/staging/captive_power/_merge_full_regions.py` → gitignored
`_build/<region>/`.

**New-research staging:** `batches/staging/captive_power/americas-gap/` (156 terminals) and
`batches/staging/captive_power/europe-topup/` (1 terminal). All four builds: no `GUARD:`/
`REF-DROP:` warnings, `recalc.py` clean, test suite green (81 passed), `fsru_sync_check.py`
gem-only graceful skip (no carrier backend).

---

## What this closes

The 2026-08-01 coordinate-first audit (`scripts/captive_coverage_audit.py`, universe = all
843 TerminalIDs in the fresh export) found 156 americas terminals never crawled by any
increment — a hand-curated-country-list scope bug; early LA/TX increments recorded only
confirmed subsets — plus 1 post-europe-increment addition (Port of Vlora FSRU 2, Albania).
This batch researched all 157 (23 shards, max 8 terminals each, terminal-first per SOP §2).

**Final audit state: americas and europe are now FULLY crawled.** 739 of 843 terminals
crawled; the 104 uncrawled are exactly the two declared pending increments — **africa (67)
and oceania (37)**, the recommended next scopes. (The audit also prints 29 country-tag vs
coordinate-region mismatches — Russia/Spain/Egypt etc. — informational only; every one is
crawled under its country's increment.)

## Verdicts over the 157 new terminals

| | count |
|---|---|
| YES | **27** (all americas) |
| NO | 12 |
| INSUFFICIENT | 63 (incl. Vlora FSRU 2) |
| SCREENED | 55 (crude-oil deepwater ports + cancelled-never-designed concepts, each with recorded evidence) |
| staged unit-rows | **45** (all `CaptiveGasPower=True`; zero overturns — nothing in scope carried a pre-existing True) |
| staged confidence | 35 green / 10 yellow |
| `mechanical=True` terminals | 8 (Cameron, Lake Charles, Magnolia, Jordan Cove, Aurora, Bear Head, Pacific NorthWest, Prince Rupert) |

The YES set splits into the two familiar structural families: **liquefaction mechanical-drive/
power-island projects** (the 8 above, incl. the operating majors Cameron and — site-power
island — Lake Charles) and **FSRU/FSU onboard generation** (Bahia, Guanabara Bay, Sergipe,
Barcarena, Cosan, Bahía Blanca, Escobar, Cartagena, Manzanillo DR, Old Harbour, Sinolam,
Barbers-Point-class exceptions aside), plus the US offshore deepwater-port trio Neptune /
Northeast Gateway / Port Pelican and Freeport's documented on-site gas turbine.

## Adjudications made at the orchestrator QC gate (now precedent)

1. **FSRU fleet-level evidence is sufficient for YES** (harmonization ruling). Applied
   asia/ME increments already granted YES on fleet/class-level disclosures (Golar fleet,
   DFDE hull class). The gap shards were graded to the same standard: an operator's own
   fleet disclosure is **primary for its own vessels → green permissible** (Energos Celsius
   at Barcarena, Energos Freeze at Manzanillo DR, Excelsior/Expedient via Excelerate's
   sustainability report + fleet pages); a lone third-party source stays yellow (Höegh
   Gallant at Old Harbour). **BW Magna (Açu) stays INSUFFICIENT** — search genuinely
   exhausted, no fleet-level machinery disclosure found; honest residual.
2. **Six FSRU/absence-based NOs → INSUFFICIENT** under the fuel gate + Hadera convention:
   Barbers Point, Aguirre, Penco Lirquén (direction-test NOs that never address vessel
   machinery), Manzanillo MX, Pichilingue, Mejillones (absence-of-spec NOs). The
   **Altamira and Quintero NOs stand** — they rest on positive vaporizer enumeration
   (ORV/SCV; an SCV burns gas for heat, not power).
3. **Colbún and Gas Atacama NO→SCREENED** — cancelled-never-designed proposals with no
   engineering content to evaluate.
4. **Neptune INSUFFICIENT→YES green** — the EPA deepwater-port application documents
   2×11,400 kW dual-fuel gas-mode engines per vessel; mirrors the Northeast Gateway record
   (`power_generation`, `electric_mw` 22.8).
5. **Freeport re-verified as YES green**, reversing the lost memo-only 2026-07-10 "NO
   (electric-drive)" hint: electric-drive trains are real, but the **pretreatment facility
   has a documented on-site gas turbine generator** (EPA NPDES TX0134056 Statement of
   Basis) and Freeport exported ~50 MW to ERCOT during a 2022 outage → `hybrid_basis:
   grid_export`. Two candidate corroborators were **rejected on anti-circularity**:
   infrasure.ai states it is generated from GEM data; worldpowerplants.com's 87 MW exactly
   matches GOGPT with no independent origin. The YES stands on EPA primary + operator page
   + trade press.

## Findings routed elsewhere (NOT this batch's edit lane)

- **Argentina LNG (T100000130832) live-DB ref contamination:** the current
  `CaptiveGasPower [ref]` cells hold two articles about **Argent LNG (Bass Energy, Port
  Fourchon, Louisiana)** — a wrong-terminal paste slip. Flagged in `qa_review`
  (`live_db_ref_contamination`); applying this batch's rows overwrites with correct Hilli
  Episeyo / MK II FLNG citations and the drops are declared in `dropped_urls_dead`.
- **Energos Winter is now at Damietta, Egypt** — affects Terminal Gás Sul and Pecém vessel
  histories (FSRU-reassignment candidates for an Update batch; also feeds the future africa
  increment).
- 60 `update_batch_flag` qa rows carry status/vessel/schedule findings with sources for the
  next Update batches (per region; qa_review totals: americas-gap 179 rows incl. 62
  INSUFFICIENT; europe-topup 2).

## GOGPT side — for Natalia (SOP §4a)

`captive_gogpt_candidates.json` (americas-gap): **1 ADD** — Port Pelican's confirmed
on-site generation (three LM2000 gas turbines; no existing GOGPT record at the site).
**3 MAYBE** — Bear Head (CHP design-confirmed, no nameplate; project pivoted to
hydrogen/ammonia 2021), Prince Rupert (plant-scale GTG design but cancelled
pre-construction), Delta LNG (cogen confirmed but withdrawn from FERC review). **21
REVIEWER CALL** — mostly FSRU onboard gensets with no standalone nameplate (the Brazil
fleet, Grand Isle, Northeast Gateway, Barbers Point) and Freeport's turbine (nameplate
unconfirmed). 131 DO NOT ADD.

## Workflow hardening landed this batch (permanent)

- **`scripts/audit_ref_drops.py` glob fix:** it only matched `*.updates.json` and silently
  skipped canonical-layout `staged_updates.json` dirs — reporting 0 drops where the build's
  REF-DROP guard found 12. Now scans both patterns; used to triage all 12 (restore-live vs
  declared-drop) before the 1145 rebuild.
- Stale-merge lesson: rebuilding old increments against a **fresh export** surfaces ref
  drift (the user applied edits between builds) — the REF-DROP guard caught 12 URLs across
  americas/europe; 10 were restored live, the rest declared dead/wrong with reasons.

## Recommended next

1. **Africa increment (67 terminals)** — largest remaining gap; includes the Egypt FSRUs
   (Energos Eskimo + Energos Winter reassignments make it timely).
2. **Oceania increment (37 terminals)** — closes the tracker to 100% crawled.
3. Follow-on Update batch for the qa_review flags (Argentina LNG ref contamination first).
