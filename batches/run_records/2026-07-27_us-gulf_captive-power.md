# Run record — US Gulf remainder captive-power increment

**Date:** 2026-07-27
**Workflow:** Captive-power cross-tracker (§9), terminal-first, state-by-state cadence.
**Area:** Third increment — Mississippi, Alabama, Florida, plus the blank-`State/Province` residue
(Louisiana done 2026-07-09, Texas 2026-07-10).

## Plan

Finish the US Gulf. Crawl every LNG terminal in MS/AL/FL for on-site captive gas power (GOGPT match as
prior, not filter). Stage `CaptiveGasPower` only — never `PowerPlantsSupplied`. Flag mechanical-drive
with `mechanical=True`. Screen (no deep research) cancelled/crude-oil terminals.

Scope was widened mid-plan after finding that terminals with a blank `State/Province` were invisible to
the state-filtered LA and TX runs; those were folded in here.

## Status / method

- Fresh GEM export pulled (1,273 unit rows); column map re-derived. Confirmed LA (30 terminals) and TX
  (29) have gained no new terminals since their batches, so no back-fill was needed there.
- Deterministic match run for MS/AL/FL: **A=0, B=0, C=1**. The single Tier-C hit (Calypso ↔ FPL's
  1,352 MW Port Everglades station, 1.00 km, `gogpt_captive=False`) is a false geographic prior against
  a deepwater port cancelled in 2009. A plant-first sweep of this area would have produced one
  candidate and it would have been wrong.
- **17 terminals in scope: 5 deep-researched via parallel subagents, 12 screened** (10
  cancelled-and-never-built, 2 crude-oil terminals mis-filed in the LNG dataset).
- Orchestrator QC gate: all **26 cited URLs re-verified** through `url_verifier.py` with the specific
  claimed value as token — **26/26 PASS**. Log at
  `batches/staging/captive_power/us-gulf/url_verifier.jsonl`.
- One researcher-returned **bare domain** (`https://www.big-hill.com`) was rejected and sent back;
  replaced with the interior `/faq` page. Same round-trip corrected a county error (Big Hill Energy is
  in Matagorda County; the Jefferson County "Big Hill" is the unrelated DOE SPR salt dome).
- One follow-up dispatch materially improved a result: the ST LNG researcher was sent back to the MARAD
  docket for a regulatory primary source instead of trade press. See below.

## Outcome

**Confirmed captive (staged): 2 terminals / 6 unit-rows**

- **ST LNG FLNG (4 rows, mechanical=True, green)** — off-grid offshore FLNG, **270.4 MW** installed
  nameplate (16 × Baker Hughes NovaLT16 @ 16.9 MW, 4/phase × 4 phases), plus 8 × Siemens SGT-750 as MR
  compressor drivers (shaft power, excluded from the MW). Both facts from the MARAD deepwater-port
  docket: the applicant's licence application ("no connection to the electric power grid") and the
  April-2026 Draft EIS stationary-source list, explicitly "inclusive of all phases".
- **Gulf LNG (2 rows, mechanical=True, yellow)** — gas-turbine mechanical drive on the MR/PR
  compressors of the FERC-authorized but never-built export project; no MW rating in any verified
  source (left undisclosed, not inferred).

**Confirmed NO:** Eagle LNG (green — JEA grid-fed, motor-driven compressor, three dedicated JEA
interconnection projects in JEA's own capital plan), American LNG Hialeah (yellow — 0.06 mtpa modular
skid plant, two orders of magnitude below turbine scale).

**No verdict:** AGP LNG (red — no site, state, or docket establishable from any citable source; the
only citable item is one LNG Prime piece).

**GOGPT candidates:** exactly one **ADD** — ST LNG FLNG (270.4 MW). The other three are DO NOT ADD.
This is the first clean LNG-captive *generating* addition from the US Gulf outside Port Arthur (TX).

**Deliverable:** `batches/lng_terminals_batch_20260727_1131_ET_us-gulf-captive_update.xlsx` (7 sheets;
recalc clean). Note: a `_1130_ET` file with identical content also exists — a same-minute rebuild
collision on my side; prune it.
**Memo:** `batches/captive_power_memo_20260727_1131_ET_us-gulf.md`.
**Staging JSON:** `batches/staging/captive_power/us-gulf/` (committed) — `staged_updates.json`,
`staged_qa_review.json`, `captive_terminal_first.json`, `captive_neighboring_plants.json`,
`captive_gogpt_candidates.json`, `_screened_terminals.json`.

## The finding that matters beyond this batch — blank-area records are invisible to `--subnational`

**Both sides of the match silently drop records with a blank area field.**

- **LNG side:** 5 terminals have a blank `State/Province` (AGP LNG, American Coast LNG, **ST LNG
  FLNG**, Phillips 66 Beamont Oil, IMTT St. Rose Oil). The state-filtered LA and TX runs could never
  see them. **This caused a real miss** — ST LNG FLNG, this batch's one green confirmed-captive
  terminal with 270.4 MW behind it, sits off the Texas coast.
- **GOGPT side:** 96 US GOGPT plants have a blank `subnational`, including **Big Hill Energy Power
  Plant**, the nearest GOGPT plant to ST LNG at 38.07 km. `load_gogpt_plants(engine, "Texas")` returns
  362 plants and misses it; `by_country=True` returns 1,724 and finds it.

Any future area increment run purely on a state filter inherits both holes. Recorded in the Captive-power
SOP and as a high-severity `qa_review` item (populate the five LNG rows from their coordinates; have
area runs fall back to a coordinate-bounded selection or explicitly sweep the blank-area residue).

## Judgment call: Gulf LNG's project-level field

One TerminalID, two facilities, opposite answers — an operating import terminal that is grid-fed (24 MW
of sub-threshold backup gensets, a clean NO) and a never-built proposed export project designed with
mechanical-drive captive power (a YES). `CaptiveGasPower` is project-level, so one DB value serves both.

Resolved rather than hedged: **staged True on both rows**, yellow, with each row's `source_notes`
naming which facility the captive power belongs to; the import row is explicitly labelled a propagation
row. Precedent from Texas settles the "unbuilt" half — Coastal Bend (proposed) and Rio Grande (under
construction) were both staged True on as-designed captive power, because GEM records proposed projects
by their design. A reviewer who wants the field to describe only built infrastructure can decline this
one edit; the finding survives in the note. Logged in `qa_review` as a data-model observation, since the
same import/export split under one TerminalID will recur.

## Follow-ups

- **ST LNG:** re-check the compressor-driver vendor (application + Draft EIS say Siemens SGT-750; the
  March-2026 Baker Hughes release was read as LM6000PF) and confirm against the **Final** EIS when it
  becomes retrievable — regulations.gov docket entries 403 without a session, so engineering facts
  currently rest on the April-2026 Draft.
- **Update workflow inbox:** Gulf LNG `Status`/`ShelvedYear` inconsistency; Eagle LNG shelved →
  cancelled trend; Hialeah operator rebrand to Sawgrass LNG & Power; AGP LNG status + inclusion
  threshold.
- **Separate scope cleanup:** at least 7 crude-oil/petroleum terminals are carried in the LNG dataset
  (5 flagged in TX + Phillips 66 Beamont + IMTT St. Rose).
- **US Gulf is now complete** (LA + TX + MS/AL/FL + blank-state residue). Next area is a user call —
  the remaining US coasts (East, West, Alaska) or a non-US region.
- **Paused for user review** before moving to the next area, per the state-by-state cadence.
