# Captive-power cross-tracker matching — Louisiana test case

**Date:** 2026-07-09 (ET)
**Workflow:** NEW — LNG terminals ↔ GOGPT captive gas power plants colocation.
**Scope this run:** Louisiana only (test case). Phases 1–2 only (no web research; no live-DB writes).
**Approved through:** Phase 2 (build matcher + bring back candidates). Phase 3 (web research) is gated pending user review.

## Goal

Identify which LNG terminals have a captive gas power plant that is separately
tracked in GOGPT. Per the methodology (May 2026): a captive gas power plant "functions
to power the terminal", >50 MW (GOGPT inclusion threshold), partially-captive still
counts, more common at export terminals (import possible).

## Decisions locked

- **Edit lane:** LNG staging xlsx + memo (this repo's normal lane). GOGPT-side gaps
  are noted in the memo only — no GOGPT staging path here.
- **Definition (strict):** on-site/fenceline gas plant >50 MW whose primary function
  is powering the terminal / liquefaction; partially-captive included. Anchored to the
  methodology "Associated Projects and Fuel Sources" section + GOGPT captive block.

## Data access (established this run)

- Both trackers live in the same read-only Postgres (`GEM_READONLY_DB_URL`).
- LNG: `gem_query.py --all-fields lng` → `State/Province` col holds the US state;
  `CaptiveGasPower` (bool) + `PowerPlantsSupplied` are the LNG-side captive handles.
- GOGPT: `plant.projectType=1` + `powerplant_unit.trackerSearch='GOGPT'`. Captive block =
  `plant.captive` (bool) + `captiveIndustryType` (jsonb array of ids into
  `captive_industry_type`; **id 56 = "LNG production / liquefaction"**) + `captiveIndustryUse`
  (power/heat/both). GOGPT unit status = `powerplant_unit.status_id` → `status` table
  (NOT `status_timeline`, which is the LNG pattern and returns 0 rows for GOGPT units).

## Tool built

`scripts/captive_power_colocation.py` — reads the LNG all-fields CSV, pulls GOGPT from
Postgres, rolls both to project/plant level, matches on three signals (geospatial haversine,
name containment, existing captive flags), resolves each plant to ONE primary terminal
(exact-coord <150 m, else name within `--name-max-km`) so channel-neighbors don't cross-claim,
assigns confidence tiers A/B/C, and emits a candidate-pairs CSV. Coarse provisional status
comparison included (full reconciliation is Phase 4).

## Louisiana result

32 LNG terminals, 64 GOGPT oil&gas plants (10 captive-flagged). Candidate pairs (radius 2 km):
**A=9, B=1, C=5**. A and B are stable at radius 1/2/5 km; only C (weak geo / neighbor bleed) grows.

- **Tier A (9):** the real captive pairs. 7 sit at identical coords named "`<Terminal> power station`";
  Argent (2.19 km) + Gulfstream (4.15 km) matched by name (approximate LNG coords).
- **Tier B (1):** G2 LNG ↔ "G2 Net-Zero power plant" (~0.4 km, both cancelled) — neither side flagged.
- **Tier C (5):** neighbor-bleed cross-links in the Calcasieu Pass / CP2 / Commonwealth / Delta /
  Plaquemines cluster; correctly demoted + annotated `primary-claim:<other>`.
- **Screened out:** "Clean Hydrogen Works LA-2 Facility" — captive-flagged but type=hydrogen, no LNG
  terminal → the false positive the strict definition rejects.

## Key findings for the write-up

- **GOGPT is ahead of the LNG tracker on flagging: 10 captive plants vs 2 LNG `CaptiveGasPower=True`
  (CP2, Calcasieu Pass).** So the main actionable LNG-side gap = 7 Tier-A pairs where GOGPT flags a
  captive plant but LNG `CaptiveGasPower` is blank (candidate LNG edits, pending Phase 3 research).
- **`captiveIndustryType` tagging is inconsistent** — only Argent uses the new id 56; 7 use "other",
  Delfin uses "oil & refining". Do NOT gate on type=56.
- **Status divergence to reconcile:** Delfin LNG=proposed vs GOGPT power plant=construction (lead-lag).
  Terminal-level status needs proper rollup in Phase 4 (multi-unit terminals show mixed status sets).
- **Data quirk (flag to user):** several crude-*oil* terminals (NOLA Oil, NuStar/Plains St. James,
  Plaquemines Oil, Louisiana Offshore Oil Port) sit in the LNG export tracker — unrelated to this task.

## Deliverable

`batches/deliverables/captive_power_colocation_<stamp>_louisiana.csv`

## Phase 3 — web research (done 2026-07-09)

One researcher per pair (9 Tier-A + 1 Tier-B), each held to the strict rules: every cited
URL value-checked through `url_verifier.py`, ≥2 independent publishers, no gem.wiki / no
GEM-derivative. Verdicts against the strict definition (on-site, >50 MW, powers the
terminal/liquefaction; partial counts):

| Terminal | Captive? | Capacity finding | Confidence | Status note |
|---|---|---|---|---|
| Calcasieu Pass | **yes** | 720 MW CCGT verified (FERC DEIS + DOE FEIS + sponsor) | green | operating |
| Plaquemines | **yes** | 2×720 MW CCGT/phase; 2,860 = 4-unit rollup, per-unit 720 verified (sponsor + FERC FEIS + trade) | green | op/constr/pre-constr (matches phased build) |
| CP2 | **yes** | 2,190 = 1,470 MW FERC-approved (constr) + 720 MW Phase-3 (proposed); DOE FEIS + 2 indep news | green (base) | base construction; Phase-3 720 MW proposed |
| Gulfstream | **yes** | 275 MW CCGT (FERC application primary; purpose corroborated by 2 indep news; 275 figure single-primary) | green (purpose) / yellow (275 MW) | pre-construction/proposed |
| Commonwealth | **yes** | dedicated ELECTRIC plant ~120 MW (DOE FEIS + trade); GEM 438.6 rolls in 348 MW of mechanical compressor drives | green (existence) | construction |
| Sabine Pass | **yes** | on-site GTGs verified (DOE EA + EPA petition); 1,665.6 MW / 8 units NOT in primaries, likely conflates mechanical compressor turbines | green (existence) / unverified (MW) | operating + Stage-5 pre-constr |
| Argent | **yes** (by design) | Baker Hughes LM9000 e-drive gensets confirmed; 675 MW / 5 units NOT public (all cites = one Baker Hughes announcement) | yellow (single-origin) | pre-construction/proposed |
| Delfin FLNG | **yes** (onboard) | onboard self-gen confirmed (DOE 2016 FEIS + 2022 design update); 168.8 MW is SUPERSEDED FEED design — current design ~30 MW waste-heat CCGT | green (existence) / stale (MW) | **FID June 2026 → construction**; LNG "proposed" is stale |
| G2 Net-Zero | **partial** (cancelled) | integrated NET Power Allam-Fetvedt power island; design >1,000 MW, GEM 300 = one module (risks conflation w/ NET Power TX) | green (purpose) | both cancelled 2023 |
| Woodside (fka Driftwood) | **NO** | grid-supplied via Entergy 230 kV (FERC FEIS); 430.4 MW = 8× LM6000PF+ MECHANICAL compressor drives, no electricity generator | green (verdict) | construction |

### Cross-cutting findings
- **9/10 confirmed captive; Woodside is the one NO** (grid-fed, no generating plant). G2 is partial + cancelled.
- **Systematic capacity issue — mechanical-drive vs electric generation.** GOGPT MW figures
  for several records appear to aggregate mechanical-drive refrigeration-compressor turbines
  (which power liquefaction mechanically, not by making electricity) rather than the dedicated
  electric power plant: Commonwealth (438.6 vs ~120 MW electric), Sabine Pass (1,665.6 unverified),
  Woodside (430.4 = purely compressor drives → verdict NO). **Definitional question for GOGPT/
  methodology: do mechanical-drive liquefaction turbines count as "captive power," or only
  electricity generators?** This decides whether Woodside is in-scope and whether several
  capacities should be revised. RAISED TO USER before Phase 5.
- **LNG-side `CaptiveGasPower` gaps (confirmed captive but currently False):** Argent, Commonwealth,
  Delfin, Gulfstream, Plaquemines, Sabine Pass. Only CP2 + Calcasieu Pass are True today.
- **Status divergences to route to Update:** Delfin (LNG proposed → construction post-FID
  June 2026); CP2 (Phase-3 720 MW proposed vs approved 1,470 MW in construction).
- **Capacity unverified against primaries (leave blank + qa_review, or document as GEM estimate):**
  Argent 675 MW, Sabine 1,665.6 MW, G2 300 MW.

All verified source URLs (each a `url_verifier.py` PASS) are captured per-pair in the agent
returns; to be transcribed into the Phase-5 staging JSON `[ref]` cells.

## Phase 5 — staging xlsx + memo (done 2026-07-09; SUPERSEDED by the 2026-07-10 addendum below)

**Definitional call resolved (user):** mechanical-drive liquefaction turbines count as captive
power (not only electricity generators). → all 10 pairs in scope; **Woodside included** (GOGPT
aggregate MW kept as-is). This flips the Phase-3 Woodside "NO" to a scoped-in YES with a
mechanical-drive caveat in the memo. **↳ FINAL STATE 2026-07-10 (after a same-day flip-flop; see
addenda): mechanical-drive is in scope but flagged `mechanical=True`; Woodside is back IN;
`PowerPlantsSupplied` is NOT staged (26 `CaptiveGasPower` edits + 1 FID fix across 10 terminals).**

**Deliverable:** `batches/lng_terminals_batch_20260709_1532_ET_louisiana-captive_update.xlsx`
(53 update records; `recalc.py` clean). Staging JSON committed at
`batches/staging/captive_power/louisiana/staged_updates.json`.
**Memo:** `batches/captive_power_memo_20260709_1532_ET_louisiana.md`.

Staged, one record per unit-row (project-level fields propagate to all units; Sabine Pass = 9 rows):
- `CaptiveGasPower = True` + paired `CaptiveGasPower [ref]` on all 10 terminals (CP2 + Calcasieu
  Pass were already True but had a blank ref — now filled).
- `PowerPlantsSupplied` description + paired `[ref]` on all 10.
- **Delfin FLNG T1 only:** `FIDStatus Pre-FID → FID` (`FIDYear [ref]` carries the FID sources).
  Lifecycle `Status` deliberately left `proposed` — FID ≠ construction and no NTP/construction-start
  source; flagged in memo as an Update follow-on.
- Confidence: green on 8 terminals; **yellow on Argent (675 MW single-origin) and G2 (cancelled,
  historical)**. All 26 cited URLs re-verified through `url_verifier.py` at build time (PASS).

Note: the only "URL in a value column" hits in the paste sheet are the export's own native `Wiki`
column (each terminal's gem.wiki pointer, excepted by the URL guard) — no gem.wiki added as a ref.

## Next (gated)

Decide whether to scale past Louisiana (memo recommends US Gulf, Texas first — Corpus Christi,
Freeport, Golden Pass, Rio Grande, Port Arthur). Before a wide sweep, resolve the
mechanical-drive-vs-electric capacity semantics with GOGPT (memo point 2). Delfin `Status`
proposed → construction remains an open Update item pending a construction-start source.

## Addendum — 2026-07-10: mechanical-drive carve-out reversed; Woodside excluded

**Decision reversed (user, 2026-07-10):** the 2026-07-09 call that mechanical-drive liquefaction
turbines count as captive power is **withdrawn**. New rule (now in SOP §2, CLAUDE.md, workflows §9):
**captive requires a real on-site electricity-generating plant** (partial/grid-exporting still
counts); **pure mechanical compressor-drive with no generator does NOT count.**

Effect on the LA batch:
- **Woodside Louisiana — excluded.** It is the one pure mechanical-drive site (8× LM6000PF+ turbines
  spinning the refrigeration compressors; site electricity grid-fed via Entergy 230 kV, no generator).
  Its 4 staged records (`CaptiveGasPower`/`PowerPlantsSupplied` × 2 unit-rows) are removed.
- **Sabine Pass and Commonwealth stay IN** — both have genuine on-site electricity generation (Sabine
  GTGs; Commonwealth ~120 MW electric plant), so their captive verdict is unchanged. Their GOGPT MW
  figures still carry the mechanical-conflation caveat in the memo (that's a capacity note, not a
  scope call).
- **Batch is now 49 records / 9 terminals** (was 53 / 10). Staging JSON re-trimmed; workbook rebuilt
  with a fresh timestamp + `recalc.py` (see below); memo updated.

**Matcher deliverable — GOGPT plant id/name/wiki now left-most (2026-07-10).** Per user request,
`captive_power_colocation.py` now pulls the GOGPT plant's `wikiUrl` and outputs the related oil &
gas plant's **`gogpt_plant_id` / `gogpt_plant` / `gogpt_wiki_url` as the three left-most columns**
of both the candidates CSV/xlsx and the `unmatched_captive` sheet. The wiki URL is a navigation
pointer to the GOGPT record for review only — NOT a citation/`[ref]` (never enters a staging sheet
as a source). Regenerated deliverable:
`batches/deliverables/captive_power_colocation_20260710_1331_ET_louisiana.{csv,xlsx}` (15 candidate
pairs; A=9/B=1/C=5, unchanged). NB the matcher is deterministic geo/name/flag matching, so it still
lists Woodside as a colocated pair — the captive-definition exclusion is applied downstream at the
staging step, not in the candidate list.

## Addendum — 2026-07-10 (later, FINAL): mechanical-drive back IN scope, but flagged `mechanical`

**The exclusion above is reversed again (user, 2026-07-10, same day) — this is the settled state.**
New rule (now in SOP §2, CLAUDE.md router, workflows §9): **mechanical-drive turbines DO count as
captive power** (so any on-site gas turbine doing liquefaction shaft-work is captive, generator or
not), **but any terminal whose captive verdict rests on mechanical drive is flagged `mechanical =
True`** in a left-most, review-only column of `updates_summary`.

Effect on the LA batch:
- **Woodside Louisiana — back IN** (`mechanical = True`; pure mechanical drive, no generator). Its 4
  records are restored.
- **`mechanical` flag stamped on every staged record.** `True` for **Woodside** (pure mechanical),
  **Sabine Pass** and **Commonwealth** (mixed: real generator *plus* mechanical drives) = 24 records;
  `False` for the seven pure-generator terminals = 29 records.
- **Batch is 53 records / 10 terminals again.** The `mechanical` column is review-only — NOT a GEM
  field, and it never appears in the `updates_in_database_format` paste sheet.

**Implementation:** `mechanical` added as the first key of each staged record; `build_review_package.py`
`build_updates_sheet` emits it as the first `updates_summary` header (not in `READ_ONLY_COLUMNS`, so
it's written; absent from the paste sheet by construction). Workbook rebuilt fresh +
`recalc.py` clean: `batches/lng_terminals_batch_20260710_1335_ET_louisiana-captive_update.xlsx`
(53 records; `mechanical` verified as col 1 = 24 True / 29 False). Memo + SOP §2/§3/§4 updated.

## Addendum — 2026-07-10 (final): `PowerPlantsSupplied` dropped + GOGPT plant id/name/wiki on the paste tab

Two changes bring the batch to its settled state:

1. **`PowerPlantsSupplied` is no longer staged.** Per the CLAUDE.md hard rule (and workflows §9 /
   SOP §2), captive power flows INTO the terminal, whereas `PowerPlantsSupplied` describes the
   opposite (terminal → external plant, e.g. Vung Ang → Quang Trach). The 26 `PowerPlantsSupplied`
   records were removed; the batch is now **26 `CaptiveGasPower` edits + 1 FID fix (Delfin) across 10
   terminals** = 27 staged records / 26 paste rows. `CaptiveGasPower` (+ `[ref]`) is the only captive
   field staged.

2. **GOGPT plant id/name/wiki added to the paste tab (user request).** `build_review_package.py`'s
   `build_update_csv_shaped_sheet` now prepends `gogpt_plant_id` / `gogpt_plant` / `gogpt_wiki_url`
   as the three left-most, **review-only** columns of `updates_in_database_format` (italic + "do NOT
   paste" comment; freeze-panes offset by `n_left`). Emitted only when the staged records carry those
   keys, so normal Update batches are unaffected. The records were stamped from the matcher
   deliverable's Tier-A/B primary pair per terminal. The gem.wiki URL is a navigation pointer to the
   GOGPT record — NOT a citation (same status as the export's native `Wiki` column; no URL-guard trip).

Rebuilt fresh + `recalc.py` clean:
`batches/lng_terminals_batch_20260710_1408_ET_louisiana-captive_update.xlsx` (26 paste rows;
`updates_summary` leads with `mechanical`, `updates_in_database_format` leads with the 3 GOGPT
columns; `mechanical` absent from the paste sheet, verified). Memo + SOP §1/§3/§4 reconciled to
drop the stale `PowerPlantsSupplied`-staged language. `tests/test_build_guard.py` green (6 passed).

## Addendum — 2026-07-14: three review-context tabs added (matching Texas)

User asked to add the same three review tabs to Louisiana. Unlike Texas (no real GOGPT captive
records), every LA terminal has a matched GOGPT captive plant, so the tabs document those matches:

- **`terminal_first_priors`** (10 rows) — each terminal's Tier-A GOGPT captive prior, how captive was
  confirmed, and `confirmed_how [ref]`.
- **`neighboring_plants`** (10 rows) — the matched captive plant per terminal (dist_km ≈ 0 for most;
  Argent 2.19, Gulfstream 4.15, G2 0.38), its GOGPT MW/units/status, a `relation` note, an
  independent `info_url`, and a gem.wiki `gogpt_record (nav only)` pointer. The nearest GOGPT plant
  here genuinely IS the terminal's own captive power — the inverse of Texas.
- **`gogpt_candidates`** (10 rows) — since the records already exist, verdicts are `IN GOGPT — OK`
  for clean CCGTs vs `IN GOGPT — REVIEW MW (mechanical conflation)` for Woodside (430.4 MW all
  mechanical, grid-fed), Commonwealth (~120 MW electric vs 438.6 GOGPT), Sabine Pass (1,665.6
  unverified); G2 flagged `status/name + MW review` (record renamed 'G2 Net-Zero power plant' →
  'G2 LNG Terminal power station'; 300 MW vs >1,000 MW design). `mechanical_drive_note` keeps shaft
  MW out of `electric_mw`.

Staging JSON: `captive_terminal_first.json` / `captive_neighboring_plants.json` /
`captive_gogpt_candidates.json` (committed). All 25 URLs re-verified via `url_verifier.py` — one fix:
the Woodside FERC FEIS predates the Woodside rename (it's the Driftwood-era FEIS), so it's verified
under `Driftwood`/`Entergy` for the grid-fed claim while the LM6000PF+ compressor-drive detail is
sourced to the Baker Hughes order. Rebuilt fresh + recalc clean:
`batches/lng_terminals_batch_20260714_1107_ET_louisiana-captive_update.xlsx` (6 sheets).
Standing layout now documented in SOP §3a/§4a + workflows §9.
