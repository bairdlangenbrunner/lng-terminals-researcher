# 2026-06-08 — Exhaustive update: development pipeline (proposed / construction / shelved)

## Request
"Do an exhaustive update but focusing on only terminals/units that are proposed, under construction, or
shelved. Keep track of this somewhere so that when I come back to do other units/terminals, I can pick up
where I left off." Then: run **Middle East first**, mark unchanged cells **blue** (standard convention, not
gray), add **all** verified supporting URLs to each cell's `[ref]` list ("the more the merrier"), and
**stop after Middle East** to hand over the xlsx and iterate.

## Scope & tier
- **Tier:** exhaustive (Update SOP §2.2) — every populated field + every existing `[ref]` re-verified;
  blank refs filled where findable; unchanged-but-reconfirmed cells = **blue**; pile on all verified URLs.
- **Filter:** Status ∈ {proposed, construction, shelved} — the `dev_pipeline` block of `stale_sweep.py`.
- **Total scope:** 473 units (proposed 270 / construction 104 / shelved 99) across 6 regions / ~70 countries,
  frozen at this batch's GEM pull. Multi-batch by design (SOP §2.2: shard for reviewability).
- **Status changes → qa notes**, not staged Status edits (`fetch_timeline` host down — known issue).

## Resumable scaffolding (the "pick up where I left off" ask)
`batches/staging/devpipeline_exhaustive/`
- `WORKLIST.json` — full 473-unit scope, by region/country, frozen at the 2026-06-08 pull.
- `_build_worklist.py` — regenerates WORKLIST + per-country `<region>/<slug>.worklist.json` (each unit's
  current values + correct paired `[ref]` per cell + blank-ref fill targets).
- `_devpipeline_exhaustive_brief.md` — the per-country subagent brief (exhaustive, blue, more-URLs rule).
- `_state.py` — resume ledger: recomputes remaining countries/regions from `<slug>.done.json` markers.
- `PROGRESS.md` — fine-grained in-flight ledger (region + per-country table).
- `<region>/<slug>.{updates,qa,wiki,entity,monitor}.json` + `<slug>.done.json` (resume marker), then
  `_build/staged_*.json` (assembled) → the region xlsx.
**"Other units" later** = everything not in WORKLIST (operating/idle/mothballed/cancelled/retired).

## Plan / status
- [x] Fresh GEM pull (1,277 unit rows) + colmap re-derived (`gem_export.colmap.json`).
- [x] `dedup_index.py`, `stale_sweep.py` → dev_pipeline = 473 units.
- [x] Built worklist scaffolding + Middle East per-country worklists (9 countries, 18 units, ~343 cells).
- [x] Middle East fan-out (one subagent per country, exhaustive) — workflow `wf_e8cf7466-ccc`, 9/9 returned.
- [x] Assemble → `batches/lng_terminals_batch_20260608_1900_ET_middleeast_devpipeline_exhaustive_update.xlsx` → recalc clean.
- [x] **Re-check pass** (user follow-up): Wayback recovery of bot-blocked refs + resolve/delete unsourced values
  (workflow `wf_ddac9d76-14e`, 9/9). Merge via `_merge_recheck.py` → rebuilt
  `batches/lng_terminals_batch_20260608_1938_ET_middleeast_devpipeline_exhaustive_update.xlsx` → recalc clean.
- [x] **Mirror-dedup fix** (user follow-up): Egypt Ertugrul `Capacity`/`CapacityUnits` cited the GIIGNL-2025
  report via two mirror URLs as if "≥2 independent" — they're one document. Deduped to one canonical URL
  (value stays yellow = single source). New rule codified (CLAUDE.md + both briefs + workbook_conventions +
  memory); added a non-blocking `GIIGNL-DUP:` build guard. Rebuilt → `…_1938_ET_…exhaustive_update.xlsx`.
- [x] **STOP — handed xlsx to user to iterate.** Remaining 5 regions PENDING (resume via `_state.py`).

## Outcome — Middle East (2026-06-08, handed off; re-checked)
**Workbook (current):** `batches/lng_terminals_batch_20260608_1938_ET_middleeast_devpipeline_exhaustive_update.xlsx`
(README, updates, updates_all_fields, qa_review; recalc clean, no formula errors). Supersedes the `_1900_ET` build.

**Numbers (post re-check):** 18 units / 12 terminals / 9 countries exhaustively re-verified (~343 cells).
**284 update records — 268 blue** (re-verified unchanged) / **3 green** / **5 yellow** / **8 green-empty deletions**.
65 qa entries. (First pass was 271 records / 52 qa; the re-check added 13 recovered-ref cells, 8 deletions,
and several confidence upgrades.)

### Re-check pass — recover bot-blocked refs (Wayback) + resolve/delete unsourced values
A **401/403/000/202 is a bot-block, not a dead page** (Reuters/S&P/Bloomberg/Argus/etc. refuse automated clients
while the page is live + archived). This follow-up recovered those via the Wayback Machine (verify the value on
the snapshot; the *live* URL becomes the `[ref]` with a "bot-blocked; confirmed via Wayback" note) and resolved
the values the first pass left genuinely unsourced — search elsewhere → change/corroborate, else **green-empty
deletion** (recommend clearing an unsupportable value).
- **Refs recovered via Wayback:** ~19 distinct source URLs reinstated across all 9 countries (Egypt 5, Qatar 4,
  Iran 3, Iraq/Israel/Jordan/Lebanon/Oman 1 each, UAE 2 — applied across ~47 cell-overrides, each keeping its
  full first-pass ref set + the recovered URL).
- **Deletions staged (green-empty, 8):** **Iran** NIOC T1+T2 `Cost`/`CostUnits`/`CostYear` = $5,000,000,000 / USD
  / 2017 (Reuters source is bot-blocked AND has no Wayback snapshot; its own text + all independent sources
  ($2.3B invested / $3.3B export phase / ~$10B total) contradict $5B; the prior `url_verifier` "5 billion" PASS
  was a **false-positive substring** of "160.5 billion cubic metres"). **UAE** Ruwais T1+T2 `Pipelines` =
  "Dolphin Qatar–UAE Natural Gas Pipeline" (Ruwais feedgas comes from Habshan via a new dedicated transmission
  line, not the unrelated Dolphin import pipeline; no named substitute exists → cleared, not changed).
- **Confidence upgrades:** **Israel** NewMed `Cost` $435M single-soft-source → **green** (Rystad primary +
  offshore-mag + lngindustry); **Lebanon** Zahrani `PowerPlantsSupplied` yellow → **green** (Wayback-recovered
  MoEW PDF + LinkedIn = 2 independent); **Egypt** Ertugrul Gazi `Capacity` 4.10 mtpa now LIVE-sourced (two
  GIIGNL-2025 mirrors; staged yellow — single publisher).
- **Genuinely dead, stayed dropped** (404 / gone / value-absent-on-200, no usable snapshot): mechademy,
  hurriyetdailynews, rivieramm, GIIGNL-2021/2022 PDFs, CNBC-2019, adc.jo, Kallanish, lngjournal, etc. — those
  cells already carry ≥2 working staged sources.
- **Still unsourced, NOT deleted** (per the DO-NOT-DELETE rule): `Lat`/`Long`/`Accuracy` GEM geocodes;
  GEM-inferred shelved-status metadata (Egypt/Lebanon `ShelvedYear`/`StopYear`); `"unknown"` Owner/Parent
  placeholders (Iraq Al-Faw, Oman Qalhat T4, Iran T3); Israel NewMed shareholder-% split (needs a TASE filing).

**The only value changes (both green, both planned-start-year slips):**
- Khor Al-Zubair FSRU (Iraq) — `LatestPlannedStartYear` 2025 → **2026** (Excelerate Oct-2025 definitive agreement + 4 independent sources).
- Qatar North Field NFW T7-8 — `LatestPlannedStartYear` 2030 → **2031** (NGI + OE Digital).
- Lebanon Zahrani `PowerPlantsSupplied` — value unchanged but re-sourced to a single non-primary URL → **yellow**.

**Headline:** GEM's Middle East development pipeline is current and accurate — almost no value drift.
The dominant work was **reference-rot repair**: a large share of existing GEM `[ref]` URLs are dead
(404 / 403 / paywalled / GIIGNL-PDF-moved); each surviving + freshly-found independent URL was piled into
the cell per the "more the merrier" rule (up to 8 URLs on one `Owner [ref]`).

**Items flagged to the user (qa, not auto-staged):**
- Status leads (fetch_timeline down, so qa-only): **Jordan** Sheikh Sabah proposed→likely construction
  (EPCIC awarded, minister site inspection); **Qatar NFW** proposed→construction (EPCC + long-lead contracted).
- **Damietta SEGAS T2** capacity discrepancy: GEM 5.00 vs sourced 5.55 mtpa.
- Legitimately-unknown ownership left as-is: **Al-Faw** (Iraq) Owner/Parent, **Oman** Qalhat T4 Owner/Parent.
- Coordinates / cost / FID fields on several units are GEM-only (no independent decimal/figure) → left uncited.
- Israel context note: the Jan-2026 Chevron FID was the Leviathan gas-field/platform expansion, NOT the FLNG
  terminal — terminal stays pre-FID `proposed`.

## Outcome — Oceania (2026-06-08, next-smallest region after Middle East)
**Workbook:** `batches/lng_terminals_batch_20260608_1958_ET_oceania_devpipeline_exhaustive_update.xlsx`
(README, updates, updates_all_fields, qa_review; recalc clean).

**Fan-out:** 8 agents — Australia (9 units / 9 distinct terminals) sharded 3×3 and PNG (18 units / 3 terminals:
PAWA 12 town-site units, Papua LNG 5, Pasca 1) sharded per terminal, plus one agent each for Timor-Leste and
New Zealand. Workflow `wf_74359dc1-cdc` (Task `wewavxgez`), 8/8 returned. Canonical `australia.done.json` /
`papua-new-guinea.done.json` synthesized from the shard summaries so `_state.py` keys off the country slug.

**Numbers:** 29 units / 14 terminals / 4 countries exhaustively re-verified (~528 cells across shards).
**443 update records — 434 blue** (re-verified unchanged) / **9 green** (the only value changes) / 0 yellow / 0 deletions.
60 qa entries (2 high / 13 medium / 45 low). *(Agents initially colored 18 unchanged-but-strongly-sourced cells
green/yellow; recolored to blue at shard source per the "unchanged = blue" convention — source strength lives in
the ref count, matching the Middle East presentation.)*

**The only value changes (both equity restatements, both green):**
- **Ichthys FLNG T3** (Australia) — `Parent` equity restated: INPEX bought Tokyo Gas's 1.575% → INPEX 67.82% /
  TotalEnergies 26% / CPC 2.625% / Osaka Gas 1.2% / Kansai 1.2% / JERA 0.735% / Toho 0.42%.
- **Papua LNG T1-T4** (PNG) — `Owner`+`Parent` equity restated across all 4 units: ExxonMobil 38.1→37.04%,
  Santos 22.8→22.83%, ENEOS Xplora 2→2.58% (project-level field applied to every unit-row).

**Headline:** same as the Middle East — GEM's Oceania dev-pipeline is largely current; near-zero value drift.
Dominant work was **ref-rot repair + blank-ref fill** (~140 refs added; PNG PAWA left 48 cells blank-unsourced,
a proposed multi-town gen+LNG concept with sparse public data).

**Items flagged to the user (qa, not auto-staged):**
- **PNG T5 Kumul FLNG** (HIGH): GEM's `Source`/`Location`/`Capacity` conflate two distinct concepts — needs
  disentangling before any value edit; could not corroborate `Source='Elk and Antelope onshore gas fields'` off-GEM.
- **Australia NTLNG** "shelved" basis is editorial on-hold (status lead; `fetch_timeline` down → qa-only).
- **Pluto** `Location` Perth → Karratha (admin-centroid vs plant site).
- **Port Phillip Bay** `Capacity` 4.70 mtpa and Tasmania **Cost** $6.28B left uncited (no independent figure).
- **Timor Sunrise** still modeled floating, but the live concept is now onshore (Bayu-Undan → Beaço pipeline).

## Outcome — Africa (2026-06-08, third region)
**Workbook:** `batches/lng_terminals_batch_20260608_2121_ET_africa_devpipeline_exhaustive_update.xlsx`
(README, updates, updates_all_fields, **entity_additions, monitor_list**, qa_review; recalc clean).

**Fan-out:** 23 agents — Nigeria sharded into 5 (Brass, NLNG/Bonny, Olokola, Ace Gas/Golar/Riverside,
Transoceanic/UTM), Mozambique into 3 (Mozambique LNG, Coral North/Matola/Nacala, Rovuma FLNG+LNG), one agent each
for the other 15 countries. **Recovered from a mid-run session limit** — the first 23-agent dispatch tripped the
session cap (only nigeria-1 fully returned); recognized the stale-reset pattern, probed with 2 small agents, then
ran the remaining 19 in two throttled waves (10 + 9). Canonical `nigeria.done.json` / `mozambique.done.json`
synthesized from shard summaries so `_state.py` keys off the country slug.

**Numbers:** 51 units / 35 terminals / 17 countries exhaustively re-verified (~743 cells).
**743 update records — 732 blue** (re-verified unchanged) / **11 green** (value changes) / 0 yellow / 0 deletions.
149 qa entries (**13 high / 50 medium / 86 low**). **4 new entities** + **4 monitor leads** (see below).
*(33 unchanged-but-strongly-sourced cells recolored green/yellow→blue at the shard source per the "unchanged = blue"
convention; single-source fragility kept in qa, notably Kenya's 15 single-sourced cells.)*

### Assembler gap fixed (first region with new entities + monitor leads)
Africa was the first region whose agents emitted `*.entity.json` / `*.monitor.json`, exposing two latent bugs —
**both fixed (permanent repo improvements)**:
- `_merge_recheck.py` never globbed entity/monitor files — it now normalizes the varied agent key shapes onto the
  build schemas, dedupes (entities by name+type merging `referenced_by_*`; monitor by country+candidate, backfilling
  country from the shard done-marker), and writes `staged_entity_additions.json` / `staged_monitor_list.json`.
- `build_review_package.py` **update mode** loaded `staged_entity_additions.json` but never `staged_monitor_list.json`
  — it now also builds the `monitor_list` sheet in update mode (an exhaustive update legitimately surfaces
  sub-threshold discovery leads). Docstring + `inputs_summary` + `SHEET_DESCRIPTIONS` updated.
- Every new entity carries the **yellow "RUN entity_lookup before creating" flag** — the remote entity_lookup
  endpoint was degraded this batch, so the dup-check is not reliable; the researcher must re-run it before creating.

**The 11 value changes (all green; all FID/ownership reshapes):**
- **Coral North FLNG** (Mozambique) — Oct-2025 FID reshaped ownership: ExxonMobil exit, Eni 25→50%, ADNOC via XRG →
  `Owner`/`Parent`/`ParentHQCountry` restated + `Capacity` 3.40 → **3.6 mtpa**.
- **Matola FSRU** (Mozambique) — `Owner` Matola Gas Co → **Beluluane Gas Company**.
- **Yakaar-Teranga** (Senegal) — Kosmos exit → Petrosen 100% (`Owner`/`Parent`) + `FIDYear` 2025 → **2026**.
- **Ngqura** (South Africa) — `Operator` Strategic Fuel Fund → **Ukwanda LNG** + `LatestPlannedStartYear` 2029 → **2035**.
- **Richards Bay Transnet FSRU** (South Africa) — `FIDYear` 2026 → **2028**.

**4 new entities (entity_additions sheet, all yellow-flagged):** XRG (owner, UAE — Coral North), Beluluane Gas
Company (owner, Mozambique — Matola), Ukwanda LNG (operator, South Africa — Ngqura), Tamasa Energy Group (parent,
South Africa — Ngqura).

**4 monitor leads (monitor_list sheet):** Côte d'Ivoire CI-GNL / Abidjan FSRU revival; Mozambique Nacala FSRU
(Karpowership LNG-to-power) + Matola FSRU FID watch; Botswana LNG terminal intent (MDCB).

**Headline:** more value drift than Middle East / Oceania (11 changes vs 3 / 9) — Africa's dev-pipeline has moved.
The **13 HIGH qa items are dominated by status leads** the agent couldn't stage (fetch_timeline down): Mozambique
LNG T1/T2 force-majeure lifted Nov-2025 / restart Jan-2026 (**shelved→construction**); Coral North post-FID, hull
launched (**proposed→construction**); Rovuma FLNG revived **as** Coral North; Eni Congo FLNG II (Nguya) on stream
Dec-2025 (**construction→operating**); Karmol Dakar FSRU first cargo May-2025 (**construction→operating**). Plus
two data-quality flags — **Olokola** wrong `State/Province`='Cross River State' + coordinates plot near Calabar
(every source places it on the Ondo/Ogun coast) — and **Yakaar-Teranga** `Capacity`=10 mtpa now unsupported.
Dominant non-status work, as before, was ref-rot repair (e.g. NLNG's dead igu.org ref cited across 6 cells).

## Resume status (after Africa)
**`python batches/staging/devpipeline_exhaustive/_state.py`** → middleeast DONE (18/18) + oceania DONE (29/29) +
africa DONE (51/51) = **98/473 total (21%)**. Next region with work = **europe** (73 units / 18 countries);
remaining order europe → americas → asia (americas/asia will need `_shard_worklist.py`).
"Other units" (operating/idle/mothballed/cancelled/retired) remain a separate future batch outside this worklist.
