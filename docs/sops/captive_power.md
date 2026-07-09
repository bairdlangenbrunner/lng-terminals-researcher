# SOP — Captive-power cross-tracker matching

**Type:** on-request cross-tracker analysis (not part of the quarterly cycle).
**Output:** an LNG staging xlsx (`CaptiveGasPower`, `PowerPlantsSupplied`, occasional status/FID
fix) **plus** a markdown memo. **Edit lane is LNG-side only** — GOGPT-side gaps are documented in
the memo, never staged (this repo has no GOGPT write path).

## 1. What this workflow answers

Which LNG terminals have a **captive gas power plant** that is separately tracked in GOGPT (the
Global Oil & Gas Plant Tracker)? A match lets us (a) set the LNG side's `CaptiveGasPower` /
`PowerPlantsSupplied` fields, and (b) surface where the two trackers disagree on status or capacity.

Both trackers live in the same read-only Postgres, so the match is a data join plus web research —
no live-DB writes on either side.

## 2. Definition of "captive" (locked 2026-07-09)

A captive gas power plant is an **on-site / fenceline gas plant, >50 MW** (GOGPT's inclusion
threshold), whose primary function is powering the terminal / liquefaction. Anchored to the
methodology's "Associated Projects and Fuel Sources" section + the GOGPT captive block.

- **Partially-captive counts** (a plant that powers the terminal *and* exports to the grid).
- **Mechanical-drive counts.** On-site gas turbines that **mechanically drive the refrigeration
  compressors** (no electricity generated) are captive power just as much as electricity
  generators are. This is the user's call (2026-07-09) and it is what makes e.g. Woodside
  Louisiana in-scope even though its site *electricity* is grid-fed.
- **Out of scope:** a hydrogen/other-fuel captive plant with no LNG terminal (the Clean Hydrogen
  Works false positive), and any plant that is not on-site or below threshold.

## 3. Phases

1. **Match (deterministic)** — `scripts/captive_power_colocation.py` reads the LNG all-fields CSV,
   pulls GOGPT from Postgres, and pairs them on three signals (geospatial haversine, name
   containment, existing captive flags), resolving each GOGPT plant to ONE primary terminal so
   channel-neighbors don't cross-claim. Emits a tiered candidate CSV (A = real pairs, B = weak/both
   unflagged, C = neighbor-bleed, correctly demoted). Filters by `--subnational` (a state/province
   name); scale to a new area by re-running with a different `--subnational`.
2. **Research (agentic, one subagent per Tier-A/B pair)** — each researcher confirms the pair
   against §2 and finds capacity/status, held to the full hard rules: every cited URL value-checked
   through `url_verifier.py`, **≥2 independent publishers**, **no gem.wiki / no GEM-derivative**.
   Return a structured verdict (captive yes/no, capacity finding + whether it's verified, status).
3. **Reconcile & stage (LNG side)** — for each confirmed pair, stage `CaptiveGasPower = True` +
   `PowerPlantsSupplied` (with paired `[ref]`) on **every unit-row** of the terminal (project-level
   fields propagate to all units — Sabine Pass = 9 rows). Route any confirmed status/FID change
   through the normal staging path. Build with `build_review_package.py --mode update` + `recalc.py`.
4. **Memo (GOGPT-side + findings)** — everything that is *not* an LNG edit goes here: GOGPT
   capacity/tagging issues, the mechanical-vs-electric split, unverified figures, and the
   scale-past-this-area recommendation.

Full command recipe: `docs/workflows.md` §9.

## 4. Recurring findings to expect (from the Louisiana test case)

- **GOGPT is ahead of the LNG tracker on flagging.** Most Tier-A pairs are GOGPT-captive but
  LNG `CaptiveGasPower=False` → the main actionable LNG-side gap is filling those two fields.
- **Mechanical-drive vs electric-generation capacity conflation.** GOGPT's aggregate MW for a
  "power station" record often bundles mechanical compressor-drive turbines with (or instead of)
  a dedicated electric plant. This does not change the captive verdict (mechanical counts) but it
  *does* mean the GOGPT MW figure may not be a power-generation capacity — flag it in the memo,
  don't "fix" the LNG side to match.
- **`captiveIndustryType` tagging is inconsistent** (only some records use id 56 = "LNG
  production/liquefaction") — do NOT gate the match on the type field.
- **Status lead-lag** — GOGPT may show the captive plant in `construction` while the LNG terminal
  is still `proposed` (Delfin). Reconcile per the methodology: a confirmed FID stages `FIDStatus`,
  but FID ≠ construction — only flip lifecycle `Status → construction` with an explicit
  construction-start / NTP source, otherwise leave it and note the follow-up.

## 5. Escalate to the user when

- The mechanical-vs-electric (or any other) scope boundary is genuinely ambiguous on a candidate —
  resolve it before staging, never stage-with-doubt.
- A GOGPT-side capacity looks systematically wrong across many records (schema/definition issue,
  not a per-record finding).
- More than ~5 confirmed new captive pairs surface in one area (worth a conversation before a
  large staging batch), or you're about to scale past the current area.

## 6. Data-access reference

- LNG = `plant."projectType" = 8`; state = the `State/Province` export column. LNG captive handles =
  `CaptiveGasPower` (bool) + `PowerPlantsSupplied`.
- GOGPT = `plant."projectType" = 1` + `powerplant_unit."trackerSearch" = 'GOGPT'`. Captive block =
  `plant.captive` (bool) + `captiveIndustryType` (jsonb array of ids into `captive_industry_type`;
  id 56 = "LNG production / liquefaction") + `captiveIndustryUse` (power/heat/both).
- GOGPT unit status = `powerplant_unit.status_id` → `status` table. (This is NOT the LNG
  `status_timeline` pattern, which returns 0 rows for GOGPT units.)
