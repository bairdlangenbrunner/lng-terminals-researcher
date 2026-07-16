# SOP — Captive-power cross-tracker matching

**Type:** on-request cross-tracker analysis (not part of the quarterly cycle).
**Output:** an LNG staging xlsx (`CaptiveGasPower` + occasional status/FID fix — **never
`PowerPlantsSupplied`**, see §2) **plus** a markdown memo. **Edit lane is LNG-side only** —
GOGPT-side gaps are documented in the memo, never staged (this repo has no GOGPT write path).

**Terminal-first** (set 2026-07-10): the unit of work is the LNG terminal, not the GOGPT plant.
Crawl the LNG terminals of an area — a US **state**, or a whole **country** where states aren't
meaningful — one area per batch, and for EACH terminal research whether it has on-site captive gas
power. The deterministic GOGPT match (§3.1) is a PRIOR that flags likely cases; it is NOT the
worklist filter. Many terminals run captive/mechanical-drive turbines that GOGPT never tracks as a
separate "power station," so a plant-first sweep silently misses them (e.g. Corpus Christi / Rio
Grande gas-turbine drives). **Which areas are done lives in the coverage ledger** — each area's
`batches/staging/captive_power/<area>/meta.json` (`scripts/coverage_status.py` reads these), not in
this prose; Louisiana (2026-07-09) and Texas (2026-07-10) are the completed-to-date areas as of this
writing. Process order follows GEM's own cadence — finish a state/country before moving to the next.

## 1. What this workflow answers

Which LNG terminals have a **captive gas power plant** that is separately tracked in GOGPT (the
Global Oil & Gas Plant Tracker)? A match lets us (a) set the LNG side's `CaptiveGasPower` field
(NOT `PowerPlantsSupplied` — §2), and (b) surface where the two trackers disagree on status or capacity.

Both trackers live in the same read-only Postgres, so the match is a data join plus web research —
no live-DB writes on either side.

## 2. Definition of "captive" (locked 2026-07-09; mechanical-drive in scope, flagged — settled 2026-07-10)

A captive gas power plant is an **on-site / fenceline gas plant, >50 MW** (GOGPT's inclusion
threshold), whose primary function is powering the terminal / liquefaction. Anchored to the
methodology's "Associated Projects and Fuel Sources" section + the GOGPT captive block.

- **Partially-captive counts** (a plant that powers the terminal *and* exports to the grid).
- **Mechanical-drive counts — but is flagged.** On-site gas turbines that **mechanically drive the
  refrigeration compressors** (shaft power, no electricity generated) are captive power just as much
  as electricity generators are. This keeps e.g. **Woodside Louisiana** in scope even though its
  site *electricity* is grid-fed (its 8× LM6000PF+ turbines are pure mechanical compressor drives).
  Settled 2026-07-10 (in-scope-but-flagged, per the `mechanical` flag below); see the run record for
  that date if the history matters.
- **`mechanical` flag (required, 2026-07-10).** Any terminal whose captive designation includes
  mechanical-drive turbines is marked `mechanical = True` in a left-most column of the staging
  review sheet — so a reviewer can see at a glance which "captive" verdicts rest on shaft-power
  turbines vs a dedicated electricity generator. In Louisiana: **Woodside** (pure mechanical, no
  generator), **Sabine Pass** and **Commonwealth** (mixed: a real generator *plus* mechanical
  drives) → `True`; the seven pure-generator terminals → `False`. The flag is a review annotation
  only — it is NOT a GEM column and never appears in the paste (`updates_in_database_format`) sheet.
- **Out of scope:** a hydrogen/other-fuel captive plant with no LNG terminal (the Clean Hydrogen
  Works false positive), and any plant that is not on-site or below threshold.
- **`PowerPlantsSupplied` is NEVER filled by this workflow (rule set 2026-07-10).** Captive power
  flows INTO the terminal (the plant powers the liquefaction/compression). `PowerPlantsSupplied`
  describes the OPPOSITE relationship — a terminal piping regasified gas OUT to an external power
  plant (e.g. Vung Ang → Quang Trach). The two are mutually exclusive for a captive relationship,
  so `PowerPlantsSupplied` and its `[ref]` stay blank in every captive-power staged record. The
  ONLY field this workflow stages is `CaptiveGasPower` (+ its `[ref]`), plus the occasional
  status/FID fix.

### 2a. GOGPT-side definitions (from the GOGPT manual, folded in 2026-07-10)

The captive concept above is anchored to BOTH the LNG Terminals Manual and the GOGPT (Global Oil &
Gas Plant Tracker) manual; GOGPT's captive fields are how the match output reads. Per the GOGPT
manual:

- **Captive plant** = a power plant located *within an industrial facility* that primarily supplies
  power to that facility. A CHP (combined heat & power) captive plant also supplies most of its heat
  to the host. A captive plant that sells a significant share of electricity to the grid (or heat to
  neighbours) is still captive — this is our "partially-captive counts."
- **GOGPT captive fields** (visible in the match CSV): `Captive Industry Type` (the served industry;
  id **56 = "LNG production / liquefaction"** — but tagging is inconsistent, so do NOT gate on it),
  `Captive Industry Use` (**heat / power / both**), `Captive Non-Industry Use` (grid/home sales →
  the partially-captive signal), and an `Emergency/Backup` flag (data-centre-only; irrelevant here).
- **GOGPT unit threshold ≥ 50 MW** (nameplate/installed), same as our on-site captive threshold.
- **GOGPT naming convention:** a captive plant with no standalone name is called "*<Host> power
  station*" — e.g. "XYZ LNG Terminal power station." This is the name-containment signal the matcher
  keys on, and the reason a real captive relationship can hide behind a generic plant name.
- GOGPT tracks *electricity generation*. A pure mechanical-drive turbine set (shaft power to
  compressors, no generator) may therefore be **absent from GOGPT entirely** — the strongest reason
  to research terminal-first rather than plant-first.

## 3. Phases

1. **Match (deterministic)** — `scripts/captive_power_colocation.py` reads the LNG all-fields CSV,
   pulls GOGPT from Postgres, and pairs them on three signals (geospatial haversine, name
   containment, existing captive flags), resolving each GOGPT plant to ONE primary terminal so
   channel-neighbors don't cross-claim. Emits a tiered candidate CSV (A = real pairs, B = weak/both
   unflagged, C = neighbor-bleed, correctly demoted). Filters by `--subnational` (a state/province
   name); scale to a new area by re-running with a different `--subnational`.
2. **Research (agentic, terminal-first — one subagent per candidate LNG terminal)** — dispatch a
   researcher for each LNG terminal in the area that could plausibly have captive power (live
   liquefaction/export terminals, any terminal with a GOGPT captive-plant prior; quick-screen and
   document — without deep web research — the obvious non-candidates: cancelled-and-never-built
   projects, crude-oil loading terminals, and small import/FSRU regas terminals). Each researcher
   confirms against §2 and finds capacity/status, held to the full hard rules: every cited URL
   value-checked through `url_verifier.py`, **≥2 independent publishers**, **no gem.wiki / no
   GEM-derivative**. Return a structured verdict (captive yes/no, **whether captive power is
   mechanical-drive**, capacity finding + whether it's verified, status). Choose a cost-appropriate
   model at dispatch time (Model selection block at the top of `docs/workflows.md`).
3. **Reconcile & stage (LNG side)** — for each confirmed terminal, stage `CaptiveGasPower = True`
   with a paired `[ref]` on **every unit-row** of the terminal (project-level fields propagate to
   all units — Sabine Pass = 9 rows). **Do NOT stage `PowerPlantsSupplied`** (§2 — captive power
   flows into the terminal, not out). Set the per-record **`mechanical`** field (`"True"`/`"False"`)
   on every record of a terminal whose captive power involves mechanical-drive turbines (§2); the
   build renders it as the left-most column of `updates_summary`. Stamp each record with the related
   GOGPT plant's `gogpt_plant_id` / `gogpt_plant` / `gogpt_wiki_url` (from the matcher deliverable) —
   the build renders these as the three left-most, **review-only** columns of the paste sheet
   (`updates_in_database_format`), italicized "do NOT paste"; the gem.wiki URL is a navigation
   pointer to the GOGPT record, never a citation. **When no GOGPT captive record exists for a
   confirmed terminal** (the terminal-first case — GOGPT doesn't track its captive/mechanical-drive
   power, e.g. all of Texas): either leave the annotation cols empty (the build emits them on key
   *presence* now, with an explanatory header note) OR, if useful, stamp the **nearest GOGPT plant by
   distance** plus `gogpt_suggested="True"` and a `gogpt_match_note` — the build fills those cells
   **RED** so a reviewer reads them as *suggestions to verify*, never confirmed matches. Route any
   confirmed status/FID change through the normal staging path. Build with
   `build_review_package.py --mode update` + `recalc.py`.
4. **Memo (GOGPT-side + findings)** — everything that is *not* an LNG edit goes here: GOGPT
   capacity/tagging issues, the mechanical-vs-electric split, unverified figures, and the
   scale-past-this-area recommendation.

Full command recipe: `docs/workflows.md` §9.

## 3a. Deliverable workbook structure (standing layout — build every area this way)

Beyond the two staging sheets (`updates_summary`, `updates_in_database_format`), a captive-power
batch's workbook carries **three review-context tabs** that capture the research reasoning, not just
the staged edits. They are built by dedicated `build_review_package.py` builders, each **gated on the
presence of its own staging JSON** in `--inputs-dir`, so a normal Update batch (which lacks those
files) is unaffected. Author the three JSONs alongside `staged_updates.json` and commit them (audit
trail). All URLs in these tabs pass `url_verifier.py` the same as any staged cell — no exceptions.

1. **`terminal_first_priors`** ← `captive_terminal_first.json` (one row per crawled terminal).
   Columns: `terminal`, `terminal_id`, `mechanical`, `confidence`, `gogpt_captive_prior`
   (what the deterministic matcher's prior was — usually "none" or a *false* C-tier neighbor),
   `confirmed_how` (how the captive verdict was reached by researching the terminal's OWN drive tech),
   **`confirmed_how [ref]`** (the verifying URLs). This tab is the terminal-first audit: it shows, per
   terminal, that the confirmation came from the terminal's own tech, not from a GOGPT plant match —
   the direct answer to "did you cover terminals with no captive-flagged GOGPT plant nearby?"
2. **`neighboring_plants`** ← `captive_neighboring_plants.json` (nearest ~2 GOGPT gas plants per
   terminal by haversine). Columns: `terminal`, `terminal_id`, `rank`, `neighboring_plant`, `dist_km`,
   `gogpt_mw`, `gogpt_units`, `gogpt_captive`, `gogpt_status`, `subnational`, `relation` (WHY this
   plant is / isn't the terminal's captive power — usually "unrelated merchant/industrial plant"),
   **`info_url`** (an independent, non-gem.wiki source on the plant), and `gogpt_record (nav only)`
   (the plant's gem.wiki URL, rendered italic/gray — a navigation pointer to the GOGPT record, NEVER a
   citation). This tab makes the terminal-first point concrete: the physically-nearest GOGPT plants
   are typically NOT the terminal's captive power. Compute the nearest-neighbor set with
   `captive_power_colocation.py`'s `load_gogpt_plants(...)` + `haversine_km(...)` over the whole
   country (uncapped radius) — the default matcher radius returns 0 for terminals whose real captive
   power isn't a separate GOGPT record.
3. **`gogpt_candidates`** ← `captive_gogpt_candidates.json` (one row per confirmed-captive terminal).
   Columns: `terminal`, `terminal_id`, `gogpt_candidate` (verdict: `ADD` / `MAYBE` / `REVIEWER CALL` /
   `DO NOT ADD`, color-coded green/yellow), `electric_mw` (the *generating* MW only — leave undisclosed
   blank, never invent), `confidence`, `basis`, **`basis [ref]`**, and `mechanical_drive_note` (the
   shaft-power figure kept explicitly SEPARATE from `electric_mw`). This tab answers "which of these
   terminals should become NEW GOGPT power-station records" — see §4a.

## 4a. GOGPT-candidate research (on-request follow-on — GOGPT-side, memo + `gogpt_candidates` tab)

When the user asks which confirmed-captive terminals should become **new GOGPT power-station
records**, run one researcher per terminal and produce a companion memo
(`batches/captive_power_gogpt_candidates_<stamp>_ET_<area>.md`) plus the `gogpt_candidates` tab above.
This is **GOGPT-side proposal only — nothing is staged** (the LNG edit lane never creates a GOGPT
record). Governing principle, proven in Texas:

- **"Confirmed captive" ≠ "GOGPT power station."** A GOGPT record tracks *electricity generation*
  with a nameplate MW. Most captive LNG terminals generate little or no on-site gas-fired electricity —
  their captive power is **gas-turbine mechanical drive** (shaft power, zero MWe) or **grid-imported**,
  with only diesel emergency gensets on site. Only a terminal with a genuine, sourced, gas-fired
  *generating* plant (e.g. Port Arthur's FERC-certified 240 MW) is a clean candidate.
- **Never let mechanical-drive shaft power populate a GOGPT generating-MW.** The biggest gas MW at a
  liquefaction site is usually the Frame 7 / LM2500-class compressor drives (hundreds of MW aggregate
  shaft). Record it in `mechanical_drive_note`, never in `electric_mw` — doing otherwise fabricates
  nonexistent power supply (the same conflation flagged LNG-side per §4).
- Verdict scale: **ADD** (green — real, sourced generating plant) / **MAYBE** (yellow — cogeneration
  exists but MW undisclosed or pre-file) / **REVIEWER CALL** (generation exists but no citable
  nameplate) / **DO NOT ADD** (grid-fed or mechanical-drive-only; a green *negative* determination).

## 4. Recurring findings to expect (from the Louisiana test case)

- **GOGPT is ahead of the LNG tracker on flagging.** Most Tier-A pairs are GOGPT-captive but
  LNG `CaptiveGasPower=False` → the main actionable LNG-side gap is filling that field (+ its `[ref]`).
- **Mechanical-drive vs electric-generation capacity conflation.** GOGPT's aggregate MW for a
  "power station" record often bundles mechanical compressor-drive turbines with (or instead of)
  a dedicated electric plant. This does **not** change the captive verdict (mechanical-drive counts
  per §2), but it has two consequences: (a) mark the terminal `mechanical = True` so the review sheet
  shows the verdict rests on shaft-power turbines (fully so for a no-generator site like Woodside,
  partly for a mixed site like Sabine Pass / Commonwealth); (b) the GOGPT MW figure may not be a
  power-generation capacity — flag it in the memo, don't "fix" the LNG side to match.
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
