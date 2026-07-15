# Run record — Texas captive-power increment

**Date:** 2026-07-10
**Workflow:** Captive-power cross-tracker (§9), terminal-first, state-by-state cadence.
**Area:** Texas (second area; Louisiana done 2026-07-09).

## Plan

Crawl every Texas LNG terminal in the fresh export; research each for on-site captive gas power
(GOGPT match as prior, not filter). Stage `CaptiveGasPower` only — never `PowerPlantsSupplied`.
Flag mechanical-drive with `mechanical=True`. Screen (no deep research) cancelled/crude-oil terminals.

## Status / method

- Fresh GEM export pulled; 30 Texas LNG rows.
- Deterministic match run (`captive_power_colocation.py --subnational "Texas"`) → GOGPT priors were
  dominated by unrelated data-center gas plants (false priors), confirming plant-first would miss the
  real captive sites.
- 12 terminals deep-researched via parallel Sonnet subagents; 18 cancelled projects screened.
- All cited URLs re-verified through `url_verifier.py` at build time (12/12 PASS).

## Outcome

**Confirmed captive (staged): 5 terminals / 23 unit-rows**
- Corpus Christi LNG (6, mechanical=True, green)
- Golden Pass LNG (4, mechanical=True, green)
- Port Arthur LNG (4, mechanical=True, green — mixed: FERC 240 MW gen + Frame 7 mech drive)
- Rio Grande LNG (8, mechanical=True, green)
- Coastal Bend LNG (1, mechanical=False, yellow — cogeneration; >50 MW inferred from scale)

**NO (not staged):** Freeport (electric-drive on ERCOT grid), Texas LNG (Baker Hughes electric
motor drives / renewable).

**Data-quality find (memo only, not staged):** 5 terminals in the LNG tracker are actually crude-oil
deepwater ports — Bluewater Texas, Blue Marlin, Brownsville Oil, SPOT, Texas GulfLink. Flagged for a
separate LNG-dataset scope cleanup.

**Deliverable:** `batches/lng_terminals_batch_20260714_0903_ET_texas-captive_update.xlsx` (recalc clean).
Paste sheet leads with the same 3 GOGPT annotation columns as Louisiana (`gogpt_plant_id` /
`gogpt_plant` / `gogpt_wiki_url`), here **empty + an honest "no GOGPT record" header note** — no Texas
terminal has a real GOGPT captive power station (verified against all 259 Texas GOGPT gas plants; the
captive power is on-site mechanical-drive turbines internal to each terminal, not a separate GOGPT
plant). See the 2026-07-14 addendum.
**Memo:** `batches/captive_power_memo_20260710_1410_ET_texas.md`.
**Staging JSON:** `batches/staging/captive_power/texas/staged_updates.json` (committed).

## Follow-ups

- Coastal Bend: chase FERC pre-file resource reports for a hard cogeneration MW figure (currently yellow).
- Corpus Christi Stage 3 (T04–T12): re-check drive tech as it commissions (may be Chart motor-driven).
- **Paused for user review** before moving to the next area (state-by-state cadence).

## Addendum — 2026-07-14: GOGPT left columns emptied to match Louisiana

User asked to make the Texas output "the same as the Louisiana one, where you have the relevant gas
plant(s) in the columns on the left." The 2026-07-10 build had filled the left `gogpt_*` columns with
the nearest GOGPT plant *by distance* as RED suggestions — but those plants (SpaceX, Gregory, the
cross-state Sabine Pass plant, an Air Products H₂ plant) are unrelated to the terminals' captive
power. Re-verified against the **full 259-plant Texas GOGPT gas-plant set**: no power station is named
after or colocated with any of the 5 confirmed terminals — their captive power is on-site
mechanical-drive turbines internal to the terminal, which GOGPT doesn't track separately. So the
"relevant plant" is genuinely *none*.

Change: blanked `gogpt_plant_id`/`gogpt_plant`/`gogpt_wiki_url` (kept as columns) and removed
`gogpt_suggested`/`gogpt_match_note` from every staged record → the build's existing "empty + honest
header note" path renders the 3 columns present-but-empty, no red fill, matching Louisiana's
convention (real matched plant where one exists, blank when none does). Rebuilt fresh +
`recalc.py` clean: `batches/lng_terminals_batch_20260714_0903_ET_texas-captive_update.xlsx` (23 rows /
5 terminals; verified 0 non-blank + 0 red-filled left cells; `updates_summary` still led by
`mechanical`). No research/verdicts changed — this is a presentation fix only.

## Addendum — 2026-07-14: GOGPT candidate power-station research (companion memo)

User asked to research and suggest power plants that would be **candidate additions to GOGPT** for the
5 confirmed-captive terminals. One researcher per terminal (parallel), each holding to url_verifier +
≥2-independent-publisher + no-gem.wiki rules. Result (companion memo
`batches/captive_power_gogpt_candidates_20260714_0935_ET_texas.md`):

- **Only 1 clean GOGPT generating candidate — Port Arthur LNG** (240 MW on-site gas-turbine generators,
  8+1, FERC-certified 167 FERC ¶ 61,052; GREEN). ADD.
- **Coastal Bend** — proposed cogeneration, MW undisclosed (YELLOW); create only if tracking proposed +
  unknown-capacity plants, else await TCEQ/FERC MW.
- **Golden Pass** — only continuous generation is waste-heat steam-turbine cogen (no citable nameplate)
  + emergency gensets; the ~515 MW Frame 7EA is mechanical drive, not electricity → reviewer call.
- **Rio Grande** & **Corpus Christi** — DO NOT ADD: grid-fed (AEP / ERCOT), on-site generation is diesel
  emergency only; captive power is mechanical-drive shaft power GOGPT doesn't track as a generating plant.

Key correction to the naive assumption: "confirmed captive" ≠ "GOGPT power station." 4 of 5 generate no
on-site gas-fired electricity — the biggest gas MW at each site is mechanical-drive compressor shaft
power, which must never populate a GOGPT generating-MW field. Memo is GOGPT-side only; nothing staged.

## Addendum — 2026-07-14: three review-context tabs added to the workbook

User asked to fold the three research tables into the xlsx. Added three new sheet builders to
`build_review_package.py` (loaded only when their staging JSON exists, so other workflows are
untouched) + `SHEET_DESCRIPTIONS` entries:

- **`terminal_first_priors`** — the terminal-first coverage table, with a `confirmed_how [ref]`
  column (the URLs proving each terminal's own drive tech).
- **`neighboring_plants`** — the nearest-2 GOGPT gas plants per terminal (distance, GOGPT MW/status,
  a `relation` note explaining why each is NOT the terminal's captive power) with an independent
  `info_url` per plant and a `gogpt_record (nav only)` gem.wiki pointer (italic/gray, do-not-cite).
- **`gogpt_candidates`** — the GOGPT-candidate table with a `basis [ref]` column, verdict-colored
  `gogpt_candidate`, and a `mechanical_drive_note` keeping shaft MW out of the electric figure.

Staging JSON: `captive_terminal_first.json` / `captive_neighboring_plants.json` /
`captive_gogpt_candidates.json` (committed). Every URL re-verified via `url_verifier.py` (9 new
neighboring-plant info URLs + 13 priors/candidate refs, all PASS). Rebuilt fresh + recalc clean:
`batches/lng_terminals_batch_20260714_1052_ET_texas-captive_update.xlsx` (6 sheets).

## Terminal-first coverage (Q2 answer)

**Re: "did you look at the terminals not near a captive-flagged plant?"** — yes. The crawl was
terminal-first, not GOGPT-filtered: all 4 green terminals (Corpus Christi, Golden Pass, Rio Grande,
Port Arthur) carried **no** correct GOGPT captive prior (worklist `gogpt_prior=no` or a false C-tier
data-center/refinery plant) yet were confirmed captive purely by researching each terminal's own
drive technology. That is exactly the blind spot the terminal-first method exists to cover.
