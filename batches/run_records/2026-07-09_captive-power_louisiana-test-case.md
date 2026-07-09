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

## Phase 5 — staging xlsx + memo (done 2026-07-09)

**Definitional call resolved (user):** mechanical-drive liquefaction turbines count as captive
power (not only electricity generators). → all 10 pairs in scope; **Woodside included** (GOGPT
aggregate MW kept as-is). This flips the Phase-3 Woodside "NO" to a scoped-in YES with a
mechanical-drive caveat in the memo.

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
