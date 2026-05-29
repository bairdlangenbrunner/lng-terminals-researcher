---
name: lng-terminals
description: Operating scaffolding for the GEM LNG Terminals research project — four workflows that produce a single staging xlsx per batch for the user to apply to the live GEM database manually. The workflows are (1) update existing terminals, (2) discover new terminals, (3) reconcile against the annual GIIGNL report, and (4) triage (decide what to work on this batch). Use this skill whenever the user asks for a terminals batch, a GIIGNL diff, a stale-sweep, a discovery run, an FSRU sync check, or any work that produces or modifies the staging xlsx (lng_terminals_batch_YYYYMMDD_HHMM_ET.xlsx). Also use this skill when the user mentions "the GEM database", "the terminals tracker", "GGIT", "GIIGNL", "the methodology doc", a country-level sweep, an FSRU vessel-to-terminal sync, the status timeline, the entity tree, or any of the standard GEM tools (entity link, ownership tree, wiki, test database). The skill is the executable scaffolding — the project's research rules live in GEM's published methodology doc (the "LNG Terminals Manual"), which is authoritative for what counts as a terminal, what the lifecycle states mean, and how units are named. The SOPs in this project are operational — they describe how to do the work, citing the methodology rather than restating it.
---

# LNG Terminals — Backend Scaffolding

## How this file fits in the project

This is project-knowledge scaffolding for an agentic research workflow that helps a GEM contractor update the Global Gas Infrastructure Tracker's LNG terminals dataset. The user has direct edit access to the live GEM database but does NOT delegate writes to the agent — every batch produces a staging xlsx that the user reviews and applies manually.

The project knowledge contains:

- **The GEM LNG Terminals Manual** (Google Doc) — the authoritative rules of what to research and how. Sometimes called "the methodology doc." Not committed to the repo; reference URL is in `docs/reference/sop_pointers.md`.
- **Four SOPs** — the operational rules for each workflow:
  - `docs/sops/reconciliation.md` — three-way diff against GIIGNL (generic body, GIIGNL-specific appendix; future IGU SOP reuses the body); typically runs first when a new annual report drops
  - `docs/sops/update.md` — update existing terminals (the bread-and-butter of the annual cycle); folds in [ref]-fill work
  - `docs/sops/discovery.md` — find new terminals not yet in the database
  - `docs/sops/triage.md` — decide what to work on this batch
- **This file** — the workflow router
- **6 reference docs** (`docs/reference/gem_db_schema.md`, `docs/reference/lifecycle_rules.md`, `docs/reference/source_roster.md`, `docs/reference/entity_canonical_map.md`, `docs/reference/unit_conventions.md`, `docs/country_notes/`, `docs/reference/sop_pointers.md`)
- **Python scripts** under `scripts/` — the tools. See `scripts/README.md` for the index.

### Reading files

All reference markdown, SOPs, and scripts are normal files on disk. Read them with the `view` tool whenever a workflow step references them. Don't read everything at session start — load on demand as the workflow dictates.

### Two artifacts pulled at batch time (not committed)

Two inputs are too large or too volatile to live in the repo:

1. **The fresh GEM database export** — pulled via `scripts/pull_gem_db.py` at the start of every batch. Auth cookies live in `.env` (see `.env.example`). The script writes the CSV and a derived column-index map (`.colmap.json`) into the working directory.
2. **The GIIGNL annual report** — when reconciling, download from giignl.org. The 2026 edition received 2026-05 is a real PDF v1.7 with a clean text layer; `scripts/giignl_extract.py` parses it via `pdftotext -layout`. (Earlier editions shipped as a zip-of-JPEGs+OCR-text+manifest — the file would report "Zip archive" not "PDF document". The vision-LLM pipeline for that format lives in git history.) Always `file <path>` before assuming the format.

## Read the methodology + relevant SOPs first

The methodology doc is authoritative. The SOPs are operational. Before any batch:

1. Confirm the methodology doc is in context (it's a long Google Doc — if it's not visible, ask the user to re-share). Note its "Last updated" line.
2. View the SOPs relevant to the workflow being run (one to three of them, depending on batch type).
3. Check `docs/reference/sop_pointers.md` for a quick rule lookup map.
4. If an SOP cites a methodology section that no longer exists or has changed, flag to the user before proceeding — the methodology is what GEM staff will review your edits against, so the SOPs must stay aligned.

## Workflow router

### Reconcile against GIIGNL (annual, triggered by report release)

Trigger phrases: "reconcile against GIIGNL", "GIIGNL diff", "compare GEM to the new GIIGNL", "process the [year] GIIGNL report".

Workflow:

1. Confirm the GIIGNL report is in project files. `file <path>` to confirm format. Two formats observed across editions: real PDF v1.7 (2026 edition received 2026-05; current pipeline) or zip-disguised-as-PDF (pre-2026; vision pipeline lives in git history). Note the edition year.
2. Confirm scope per Reconciliation SOP §2 (which GIIGNL tables — terminal-list, capacity-by-country, country-summary; which lifecycle states to include).
3. `python pull_gem_db.py` → fresh CSV.
4. `python giignl_extract.py <path-to-giignl-report> --output giignl_extracted.csv` → flat CSV with GEM-aligned column names per Reconciliation SOP §3 (Appendix A for GIIGNL-specific table parsing). The CSV's `status` column carries any in-table non-op tag ("Bontang Train E (Mothballed)").
   4a. **§3.2.1 narrative pass** (agent-driven; default yes): read the narrative pages (2026: liq pp.28-31, regas pp.48-52). Forward-looking findings (proposed/construction/expansion) → Discovery/Update routing. **Operating-status corrections** — where the prose says a train listed *untagged* in the operating table isn't actually operating (Bontang p.31: "only Trains G and H currently in operation" ⇒ Train F idled) — go in an agent-authored `giignl_prose_corrections.json` next to the extracted CSV, which `report_diff.py` auto-applies.
5. `python report_diff.py --extracted giignl_extracted.csv --report giignl --gem-csv gem_export.csv --output giignl_diff.json` → three-way diff (matches, GIIGNL-only, GEM-only, value-disagreements). Auto-discovers `giignl_prose_corrections.json` beside the extracted CSV (or pass `--prose-corrections <path>`).
6. Route findings per Reconciliation SOP §4:
   - GIIGNL-only → Discovery workflow (verify candidate is real and in-scope before adding)
   - GEM-only → log in `giignl_to_action` sheet, usually no action (GIIGNL has known gaps per the methodology FAQ)
   - Value-disagreement → Update workflow (GIIGNL is one source in a conflict, NOT automatically authoritative — the methodology FAQ says a more specific or current source takes priority)
   - Match → confidence bump on the GEM record
7. **DO NOT auto-apply GIIGNL values to the GEM record.** Every value-disagreement requires resolution through the Update workflow's normal source-search and confidence-labeling process.
8. `python build_review_package.py --mode reconciliation --report giignl --year <YEAR>` → staging xlsx with `giignl_diff_operating`, `giignl_diff_nonoperating`, and `giignl_to_action` sheets in addition to the standard sheets.
9. `python recalc.py`, then `present_files`.

(A future IGU reconciliation SOP will reuse this workflow body with `igu_extract.py` and `--report igu`.)

### Update existing terminals (most common)

Trigger phrases: "update terminals in [country/region]", "refresh the [country] entries", "fill blank refs for terminals X to Y", "annual update for [country]", "check what's stale in [country]", "go through [country] terminals".

Workflow (assuming scripts have been copied to a working directory per the section above):

1. `python pull_gem_db.py` → fresh CSV at `gem_export.csv`, prints derived column-index map. **Re-derive on every run** — the schema can drift between GEM database revisions.
2. Confirm batch scope per Update SOP §2 (which terminals/countries, depth of update, whether [ref]-fill is in scope, whether status updates are in scope).
3. `python dedup_index.py` → builds project/unit indexes per Update SOP §3.
4. For each terminal in scope:
   a. Pull the unit-level timeline from the live DB (`python fetch_timeline.py <UnitID>`) if any status changes are anticipated — the export does NOT contain timeline history, only anchor years and current status.
   b. Source-search per Update SOP §4 — using `docs/reference/source_roster.md` for tier selection and `docs/country_notes/` for country-specific tips.
   c. Apply lifecycle state machine per `docs/reference/lifecycle_rules.md` — especially the planned-vs-actual sub-status logic and the "closest non-planned-non-FID status to bottom" rule for deriving current status.
   d. For [ref]-fill: identify blank `[ref]` columns paired with **filled** data values (the equivalent of carrier-project Rule F — no orphan citations).
5. `python url_verifier.py <url> <expected1> <expected2> ...` on every URL before it goes in the xlsx. Or import as a module — see the script's docstring.
6. `python capacity_normalize.py` on any capacity changes — mtpa/bcm/y/m³ conversions, range handling per methodology ("record max in spreadsheet, range in wiki Background").
7. `python entity_lookup.py "<owner name>" "<country>"` before staging any new owner/operator — the methodology is emphatic about not creating duplicate entities.
8. **If any FSRU terminal is touched**: `python fsru_sync_check.py` — see "FSRU sync rule" below.
9. `python build_review_package.py --mode update --output ../batches/lng_terminals_batch_<YYYYMMDD>_<HHMM>_ET.xlsx` → staging xlsx. Stamp via `TZ=America/New_York date "+%Y%m%d_%H%M_ET"`.
10. `python recalc.py ../batches/lng_terminals_batch_<YYYYMMDD>_<HHMM>_ET.xlsx` → confirm zero formula errors.
11. `present_files`.

### Discover new terminals

Trigger phrases: "find new terminals in [country/region]", "discovery run", "what's missing from GEM in [region]", "catch-up sweep for [country]", "any new proposals in [region]".

Workflow:

1. Confirm parameters per Discovery SOP §2 (region/country scope, gap window if any, whether to include early-stage proposals that may not meet the "sufficient information to add" threshold from the methodology FAQ).
2. `python pull_gem_db.py` → fresh CSV; `python dedup_index.py` → indexes used for matching candidates against existing records.
3. **Country-level regulatory sweep** — Discovery SOP §4 lists per-country regulators (FERC/DOE for US, EU PCI portal + national TSOs for Europe, METI/JOGMEC for Japan, MOTIE for Korea, CNPC/Sinopec/CNOOC IR for China, etc.). Use `docs/country_notes/` to seed the search and contribute findings back.
4. **Trade press sweep** — per Discovery SOP §5, using `docs/reference/source_roster.md`. LNG Prime, Reuters, S&P Global Commodity Insights, Argus, Upstream are the workhorses.
5. **Sponsor IR sweep** — for known LNG developers (Cheniere, Venture Global, TotalEnergies, Sempra, Adnoc Gas, QatarEnergy, Petronas, NLNG, NextDecade, etc.) — per Discovery SOP §6 and `docs/reference/entity_canonical_map.md`.
6. For each candidate: apply the "sufficient information to add" threshold from the methodology FAQ (sponsor identified + approximate location + concrete step taken). Candidates that don't meet the threshold go in a `monitor_list` sheet, not `new_terminals`.
7. `python url_verifier.py` on all URLs; `python entity_lookup.py` on every new owner/operator/parent.
8. **If any candidate is an FSRU**: `python fsru_sync_check.py` against both the GEM terminals and (if available) the LNG carrier project's backend.
9. `python build_review_package.py --mode discovery --output ../batches/lng_terminals_batch_<YYYYMMDD>_<HHMM>_ET.xlsx` → staging xlsx (Eastern timestamp via `TZ=America/New_York date "+%Y%m%d_%H%M_ET"`).
10. `python recalc.py`, then `present_files`.

### Triage (decide what to work on this batch)

Trigger phrases: "what should we work on this quarter", "what's stale", "plan the [Q1/Q2/Q3/Q4] batch", "where are the gaps", "what hasn't been touched in a while".

Workflow:

1. `python pull_gem_db.py` → fresh CSV.
2. `python stale_sweep.py` → for each terminal/unit, compute LastUpdated age and lifecycle-rule-driven flags:
   - Proposed/Construction units with LastUpdated > 12 months → due for refresh
   - Proposed units with no updates > 2 years → candidates for inferred shelved (per methodology)
   - Shelved units with no updates > 4 years → candidates for inferred cancelled (per methodology)
   - Operating units with LastUpdated > 18 months → due for refresh (lower priority than active development)
3. Pull triage inputs per Triage SOP §3:
   - Stale-sweep results (above)
   - Recent news scan (last quarter) for activity in countries that haven't been touched recently
   - GIIGNL reconciliation backlog (any unprocessed findings from a prior reconciliation batch)
   - User priorities (existing GEM team commitments, upcoming publications)
   - Whether a fresh GIIGNL/IGU report has dropped since the last reconciliation
4. Produce a triage memo (markdown, not xlsx) with recommended batch composition. The user decides scope before any Update or Discovery batch starts.

## FSRU sync rule (cross-project)

FSRUs are tracked in both the GEM terminals tracker and (if the user is also running it) the LNG carrier project. Each project owns its own fields:

| Field type | Owned by | Examples |
|---|---|---|
| Vessel identity & technical specs | Carriers | IMO, builder, hull, m³ LNG capacity, propulsion, delivery year, vessel owner, vessel operator |
| Terminal identity & operations | Terminals | Country, port, terminal name, sendout capacity (mtpa/bcm), terminal operator, lifecycle status, location, sponsor |
| Linking fields (both records must agree) | Sync rule | Vessel name, IMO |

**Sync rule mechanics:**

1. When a terminals batch adds or updates an FSRU terminal, the FloatingVesselName + (IMO if known) go in the staging xlsx with a sync-touchpoint flag.
2. When a carriers batch updates an FSRU vessel that's deployed, the terminal name + country go in the carrier xlsx with the same flag.
3. `fsru_sync_check.py` diffs both backends on (IMO ↔ terminal name) pairs and surfaces mismatches. Mismatches go in a `fsru_sync` sheet of whichever xlsx is the current deliverable.
4. **Vessel reassignment** (FSRU moves from terminal A to terminal B) is a real and observed pattern — at least one terminal in the export has three FSRUs in sequence. The script handles it by modeling: terminal A's prior FSRU gets an "Idled" or "Retired" status timeline entry on the unit-row; terminal B (or a new unit on terminal A) gets the new FSRU. The carrier record's deployment field updates correspondingly.

Edge cases:
- **FSU / FRU** (floating storage only / floating regas only) — same rule applies.
- **Deepwater Port LNG terminals** (offshore but not floating) — terminals only, no vessel record, no sync needed. The script skips them.

If the user isn't running the carrier project, `fsru_sync_check.py` short-circuits to "skipped — no carrier backend available" and logs the FSRU entries for future cross-check.

## Scripts — what each does and when to read its source

| Script | Purpose | Read source when |
|---|---|---|
| `pull_gem_db.py` | Wraps `gem_export_via_web.py`; pulls all-fields CSV and derives the 115-col column-index map | Schema changed; column indices look wrong; auth fails (cookies stale) |
| `fetch_timeline.py` | Pulls the full status timeline for a UnitID from the live DB UI (export doesn't include timeline history) | UI changed; timeline parse returns nothing for a unit known to have one |
| `normalize.py` | Canonical country / entity / capacity-unit names (module, imported by others) | Adding new country/entity; cluster matching is over- or under-merging |
| `dedup_index.py` | Builds project-level and unit-level indexes from the GEM export | New batch type that needs a different index shape |
| `capacity_normalize.py` | mtpa ↔ bcm/y ↔ m³ LNG storage conversion; range handling; per-train vs total reconciliation | New capacity unit appears in source; conversion factor disputed |
| `status_timeline.py` | Derives current status from a timeline per the methodology's "closest non-planned-non-FID to bottom" rule; validates legal transitions | Methodology updates state machine; anomalous transition observed |
| `stale_sweep.py` | Computes stale flags per `docs/reference/lifecycle_rules.md` (inferred shelved at 2yr, inferred cancelled at 4yr, etc.) | Methodology revises the year thresholds |
| `entity_lookup.py` | Queries the GEM entity system to avoid duplicate entity creation | Entity search UI changed; known entity not being found |
| `url_verifier.py` | HTTP 200 + content check + soft-error detection (paywall stubs, Cloudflare, members-only) | Verifier flags false positives/negatives; new source pattern needs handling |
| `imo_tracker.py` | IMO → marinetraffic.org per-vessel URL (FSRU vessel lookup) | marinetraffic.org URL pattern changed; Cloudflare gating |
| `giignl_extract.py` | Parses GIIGNL report into a flat CSV with GEM-aligned columns. 2026 edition is a real PDF v1.7 with a clean text layer — uses `pdftotext -layout` + column-position-based row partitioning; per-country capacity subtotals are used as block-boundary budgets so rows route to the right country even when labels appear mid-block. GIIGNL vertically *centers* each country label+subtotal within its block, so rows above the label inherit the previous country; a post-pass (`_truecup_country_subtotals`) reclaims them by *tentatively* pulling rows from the **single immediately-preceding country** and committing only if the run then reaches the country's published subtotal (within a 6%/2% reach band). This catches the case the running budget misses (the previous country's block spilled over from an earlier page so its page-local cumulative never reaches its subtotal — e.g. Brunei T1/T2 inherited Australia, whose 85.8 MTPA block began on the prior page) WITHOUT the failure mode of an earlier naive version: a multi-page country like China regas (264 MTPA, pages 55–57) looks "short" on each page and would otherwise swallow the whole USA+Bangladesh blocks above it to reach its subtotal. The two guards — never pull through more than one preceding country, and commit only on reaching the subtotal — keep it to genuine centered-label misattributions (Brunei, Ain-Sokhna, Damietta, Moheshkhali, Brazilian/Malaysian/German/UK terminals, etc.). The standalone page footer ("<page#> - GIIGNL Annual Report <year> Edition") is skipped during line classification (`_PAGE_FOOTER_RE`) — otherwise the line-merge pass folds it into the last data row of the page and the column slicer splits it across cells (e.g. "Annual" → country "… GIIGNL An" + site "nual Report 2026 Edition"), corrupting that row AND poisoning the country walk for the rest of the page (this had silently dropped QatarEnergy LNG S(2) T4 and mis-countried Ruwais/San Juan/Yamal T1/etc.). **Embedded label/subtotal-on-a-data-row + cross-page blocks (QatarEnergy fix):** GIIGNL also centers a country label+subtotal directly ONTO a data row's physical lines — Qatar's "77.0 MTPA" + "N(3) T6" sit on the N(3) T6 row. A subtotal line is now recorded but NOT skipped when its name column (col 1) carries a fragment, so the trailing train code isn't lost (this had degraded N(3) T6 / S(3) T6 to a bare "QatarEnergy LNG"; the same fix also recovers regas terminal names previously eaten by such lines — Jamaica "Old Harbour", Croatia "Krk expansion", Türkiye "Saros LNG", Ravenna's "BW Singapore" vessel). Because the centered label makes rows ABOVE it inherit the previous country and the per-page `_truecup_country_subtotals` can't repair a block that spans pages (Qatar liq spans 34-35 so neither page reaches 77.0; N(1)/N(2) stranded on Oman, Oman T1 on USA), a section-wide `_reclaim_cross_page` re-runs the reclaim over ALL pages' rows in report order, iterated to a fixpoint (Qatar pulls N(1)/N(2) from Oman → Oman then pulls Oman T1 from USA), choosing the pull count CLOSEST to the subtotal — not merely within band, else Indonesia (24.9) swallows Canada's Tilbury LNG (0.3). It keys off `_robust_subtotal_map` (each subtotal → its NEAREST data row's country, since the sequential walk otherwise mis-files Oman's 11.4 under USA). Zero-width chars are stripped (`_clean_text` + normalize) so "S(2 )" yields designator token "s(2". A regas FSRU row whose EVERY site fragment carries an (FSRU)/(FSU) tag (site "Ravenna (FSRU)" + vessel "BW Singapore (FSRU)") takes the first fragment as site, last as vessel (trailing "and" stripped for dual-FSU rows like Malaysia "Tenaga Empat … and Tenaga Satu"). **Row partitioning by name-start (APLNG/Darwin/Prelude fix):** lines are assigned to the NEAREST data line, NOT split at the midpoint between data lines (the midpoint absorbed a row's leading name into the row ABOVE when a site name spans multiple physical lines). A distance TIE is resolved by content: a capitalized name-START fragment (no capacity, opening/balanced parens, not "Expansion"/"Extension", no FSRU/FLNG tag) is the LEADING name of the row BELOW; a continuation (lowercase, dangling close-paren like "…Ahmeyim Phase 1)", a bare "Expansion", or a facility-tagged vessel like "Italis LNG (FSRU)") stays with the row ABOVE. This un-fuses "APLNG T2" from "Darwin LNG (new" (so APLNG T1+T2 group → 9.0), recovers "Darwin LNG (new supply source Barossa project)", Croatia "Krk" (main row, fixing the earlier fragmentation), "Piombino"/"Panigaglia", and un-merges cross-terminal bleeds (Al Zour+Dakar, Zeebrugge+Krk). A facility tag in PARENTHESES — "(FLNG)"/"(FSRU)" — is NOT stripped as a status hint (it's part of the name: "Prelude (FLNG)", "PFLNG Dua (FLNG)"); `normalize_terminal_name` drops a trailing parenthetical facility tag for MATCHING only ("prelude (flng)"→"prelude" exact-matches GEM "Prelude FLNG Terminal"), keeping the tag in the displayed site_name. **Non-operating status hint → `status` column (Bontang/Balhaf fix):** GIIGNL's liq/regas tables are operating-only, but a few rows are annotated as not-currently-operating with a status parenthetical — "Bontang Train E (Mothballed)", "Balhaf T1/T2 (stopped)", "Atlantic LNG T1 (Mothballed)". `_strip_train_suffix` already peels such a parenthetical off the liq name; `_status_from_hint` now maps the peeled word to a canonical GEM non-op status (`_NONOP_STATUS_HINTS`: mothballed→mothballed, stopped/idle/suspended→idled, retired/decommissioned→retired, …) written to a new LAST CSV column `status` (regas peels its own trailing status paren via `_STATUS_HINT_RE`, since facility-tag stripping leaves a "(Mothballed)" in the site name). An UNRECOGNIZED hint maps to "" (row stays operating, raw hint kept only in notes — we don't guess). report_diff then EXCLUDES a status-bearing row from the operating total. NB: facility tags "(FLNG)/(FSRU)/(FSU)/(FRU)/(FPSO)" are explicitly NOT status hints (kept as part of the name). Earlier editions shipped as zip-of-JPEGs + OCR; that pipeline lives in git history if a future edition reverts | New GIIGNL edition layout changes column positions; new country added to super-region marker list; subtotal detection misfires; true-up over/under-pulls (diff per-country row sums against subtotals across ALL pages, not one page, and watch for cross-country pulls); footer/header text bleeds into a row (re-check `_PAGE_FOOTER_RE`); a multi-line site name is split across two rows or fused with a neighbour (check the nearest-data-line tie-break in `_partition_lines_by_data` — the name-start vs continuation classification); a GIIGNL status parenthetical ("(Mothballed)"/"(stopped)") isn't recognized as non-op (extend `_NONOP_STATUS_HINTS`) or a facility tag is wrongly eaten as a status (check the `_strip_train_suffix` exclusion list) |
| `report_diff.py` (alias matching) | Project key includes `section_type` so a single GEM terminal with both liquefaction and regasification (e.g. Sabine Pass: 6 export trains + 1 import terminal) splits into two distinct projects, not one summed entry. Alias map includes GEM `OtherNames` + `LocalNames`, with CJK transliteration via jieba + pypinyin (e.g. `中石油唐山曹妃甸LNG接收站` → `zhong shiyou tangshan caofeidian lng jieshouzhan` so distinctive city tokens can match). **Row-folding (report side):** rows ending in "Expansion"/"Extension" fold into the base "<Site>" row, AND per-complex unit-code rows ("Arzew GL1Z/2Z/3Z") fold into "Arzew" (`_strip_unit_code_suffix`: trailing letters+digits token), AND explicit per-train rows ("Bontang Train E/F/G/H") fold into "Bontang" (`_strip_train_word_suffix`: trailing literal word "Train"/"Trains" + a 1-2 char code/roman numeral) — all conservative, firing only when the base resolves (a GEM key/alias, another report row, or ≥2 report peers sharing the base), so bare "expansion" artifacts are left alone. The unit-code fold deliberately ignores single-letter codes (else it eats "Senboku II"); the train-word fold needs the literal word "Train", which is what makes "Bontang Train E"→"Bontang" safe while "Corpus Christi Stage III" / "Senboku II" are left alone. **Same-name-by-owner families:** GEM disambiguates multiple distinct terminals that share a base name with a trailing first-owner parenthetical — "Tianjin LNG Terminal (PipeChina)" / "(Sinopec)" / "(Beijing Gas Group)" (common for Chinese terminals; also Salina Cruz, QatarEnergy LNG (N)/(S)). When ≥2 GEM terminals in a country+section share a base name, the parenthetical is treated as an OWNER tag, not a name token: it's added to `owners_set` and the fuzzy match-tokens are built from the base name only (so the owner word "sinopec" doesn't drag in Liuheng/Longkou (Sinopec)). Fuzzy matching strips the report-side parenthetical too, and a tie-break prefers the candidate whose GEM parenthetical owner equals the GIIGNL row's first owner. **FSRU-vs-onshore same-port split (`_FLOAT_VARIANT_SUFFIX`, `collision_regas`):** at a regas port GEM may track BOTH a floating terminal and an onshore one under names that normalize identically — `normalize_terminal_name` strips both " FSRU" and " LNG Terminal", so "Ravenna FSRU" + "Ravenna LNG Terminal" both → "ravenna" (≈12 ports: Ravenna, Stade, Hazira, Payra, Summit Matarbari, Dongying, Yantai, Paldiski, Brunsbüttel, Wilhelmshaven TES, Haldia, FGEN Batangas). A pre-scan flags such ports (a regas (country,name) with BOTH a floating and a non-floating GEM terminal); the FLOATING member is keyed under a " fsru" name suffix on the GEM side, and a vessel-bearing GIIGNL row at that port (`_report_row_is_floating`) gets the same suffix — so onshore↔onshore and FSRU↔FSRU match instead of collapsing into one merged project (this had wrongly combined GIIGNL's onshore Ravenna 0.7 + Ravenna FSRU 3.7 into a single 4.4-vs-0.7 entry). Restricted to regasification (a report row's floating-ness is undeterminable for GIIGNL liquefaction, so liq FLNG/onshore pairs — Cameroon, Rovuma — are left merged). The suffix is non-parenthetical so it doesn't trip the family logic above | New non-Latin language in LocalNames; matching needs more script support; fold over/under-merges (check `report_sites_merged`); same-name family matched to wrong sibling (check parenthetical-owner vs GIIGNL first owner); an FSRU/onshore same-port pair merges or mis-routes (check `collision_regas` membership + `_report_row_is_floating` — needs the GIIGNL row to carry a vessel/FSRU type) |
| `report_diff.py` (unit-level alignment) | `_align_units`: within a matched project, aligns each GIIGNL row to a specific GEM unit when the GEM unit name is a token of the GIIGNL site name (GIIGNL "Arzew GL1Z" ⊃ GEM unit "GL1Z") + capacity corroboration → `match_granularity="unit"` with a `unit_matches` list; falls back to project-total (operating-only) when GIIGNL rows don't map to GEM unit names (Taichung). **Sub-terminal designator → GEM unit (Pass 1.5, `_unit_designators`):** GIIGNL splits a complex into sub-terminals, each its own report project ("QatarEnergy LNG S(1)/S(2)/S(3)"), while GEM splits the SAME complex into one terminal with train-range units ("QatarEnergy LNG (S)" → units "S(1) T1-2"/"S(2) T3-5"/"S(3) T6-7") — a many-report-projects-to-one-GEM-terminal shape `_align_units` can't reach (GEM unit tokens {s(2,t3,5} ⊄ report site {qatarenergy,lng,s(2}), and the plain project matcher would wrongly compare each sub-terminal against the WHOLE terminal (the bogus S(2)=14.1 vs (S)=36.3 "61% conflict"). A report project carrying a parenthesized-digit designator (S(2)→"s2") that identifies exactly ONE GEM unit within a SINGLE GEM terminal in the same country+section is matched to that UNIT (`match_type="unit_designator"`, compared at unit level: S(2) 14.1 vs unit 14.1), gated on a 4+ name-token or owner overlap. The designator inherently routes n*→(N), s*→(S), so it ALSO disambiguates GEM's same-base-name siblings without the parenthetical-owner heuristic. **GEM owner parsing** now uses `parse_entity_list` (same as the report side) instead of a comma-only split: GEM cells are ";"-separated with "[NN%]" brackets ("QatarEnergy [70%]; Exxon Mobil Corp [30%]"), and the old split collapsed every multi-owner cell to a single (often wrong) tag, manufacturing false owner conflicts on nearly every match (`parse_entity_list`'s %-regex now also accepts "[…]" brackets; "qatar energy" added to the entity map). **Project-spanning guard:** a unit is accepted only if the GIIGNL row's capacity is at least as close to that unit as to the project total — stops a whole-terminal GIIGNL row from being pinned to one unit via a coincidental code token (GIIGNL "Portovaya LNG T1 (+ FSU)" = 1.5 = the whole terminal would otherwise emit a spurious unit-level 100% conflict against GEM unit "T1" = 0.75 beside the correct project-level 1.5-vs-1.5 match). **Multi-terminal FSRU site split (`_split_multiterminal_fsru_sites`):** GIIGNL labels several physically distinct FSRU terminals at one port with the SAME site name, disambiguating only by vessel — e.g. Germany "Wilhelmshaven" appears twice (Höegh Esperanza, Excelerate Excelsior), which GEM tracks as two terminals ("Wilhelmshaven FSRU" + "Wilhelmshaven TES FSRU"); Egypt "Ain-Sokhna" lists three vessels split across GEM "Ain Sokhna FSRU" (Energos Power) and "Sumed FSRU" (Höegh Galleon, Energos Eskimo). Each GIIGNL vessel row is routed to the GEM terminal whose **terminal-level `FloatingVesselName`** carries it (GIIGNL "Excelerate Excelsior" ⊇ GEM "Excelsior"), and the site is emitted as one report sub-project per GEM terminal (display name carries the vessel, e.g. "Wilhelmshaven (Höegh Esperanza)"), each force-matched. Fires only when the site's vessels resolve to **≥2 distinct GEM terminals** AND every row maps — distinguishing it from the sequential-berth case below. **FSRU operating-only (`_fsru_operating_report_capacity`):** for a genuine single-terminal berth that cycled vessels (one GEM operating unit + retired vessels) where GIIGNL lists every deployed FSRU as an operating row, the report capacity is recomputed as the sum of only the GIIGNL rows whose vessel (matched against GEM `unit_name`) maps to a GEM OPERATING unit; the others become per-vessel notes in `disagreements`. Also emits `nonoperating_units` (non-op units of matched projects) for the `giignl_diff_nonoperating` sheet. **Non-operating GIIGNL rows (Bontang/Balhaf fix):** a report row carrying a `status` (set by giignl_extract from a "(Mothballed)"/"(stopped)" hint, i.e. status ∈ `_NONOP_STATUSES`) is split out of the report project into `nonop_rows` and EXCLUDED from `total_capacity_mtpa`/`trains_count`/`rows` — so the operating comparison sums only the operating trains (Bontang report=F+G+H=8.7 vs GEM operating G+H=5.75, NOT 11.6; Balhaf both-trains-stopped → report 0 vs GEM 0, killing the old spurious 7.2-vs-0). The excluded rows surface on the match as `report_nonoperating` (operating sheet column, no red), and `_corroborate_nonop` aligns each to the GEM non-op unit whose name is a token of the row's site_name+trains (lowercased — `_simple_tokens` doesn't case-fold and `trains` isn't normalized), filling that unit's `giignl_narrative_mention` + clearing its `is_gem_only` flag (Bontang E↔unit E idled; Balhaf T1/T2↔GEM T1/T2 mothballed). Tiny blast radius — only fires when a GIIGNL row actually carries a status (≈4 rows in the 2026 edition). **§3.2.1 prose operating-status corrections (Bontang Train F fix):** GIIGNL's TABLE is operating-only but its NARRATIVE can say a train listed *untagged* in the table isn't actually operating — Bontang p.31: "only Trains G and H currently in operation" means Train F (untagged in the table, no "(Mothballed)") is idled too. The narrative pass is agent-driven (SOP §3.2.1), so this is fed via an agent-authored `giignl_prose_corrections.json` (auto-discovered next to the extracted CSV, or `--prose-corrections`): `_load_prose_corrections` + `_apply_prose_corrections` run right after the FSRU split and BEFORE matching, moving each named unit's report row from `rows`→`nonop_rows` (status from the file, default idled), recomputing the operating total, and stamping `_prose_source` (the citation flows into `report_nonoperating` and the corroboration note). This drops Bontang from a bogus report 8.7-vs-5.75 (51%) to 5.8-vs-5.75 (0.9%, just the per-train cap nuance, G+H both 2.9 in GIIGNL vs 2.8/2.95 in GEM) — F now corroborates GEM's idled F via prose. Capacity NUMBERS are never changed here (§5.6 prefers the tabular value); nothing is applied to GEM (§3.8) — it only makes the GIIGNL side internally consistent with GIIGNL's own prose. The file's second section, `nonop_corroborations`, handles the related case where a GEM non-op unit has NO GIIGNL table row because the unit already ceased (NWS Train 2: dropped from the operating table, but the narrative names it "permanently ceased") — `_load_prose_corrections` returns `{op, nonop}`, and the nonoperating-units pass fills `giignl_narrative_mention` + clears `is_gem_only` for the named GEM unit (keyed GEM terminal+unit) | Unit names don't tokenize cleanly against report site names; alignment over/under-matches (check `match_granularity` + `unit_matches`); a same-named multi-terminal FSRU port doesn't split or splits wrong (check GEM `FloatingVesselName` vs GIIGNL vessel; needs ≥2 distinct GEM terminals); FSRU vessel names don't match GEM unit names (check the FSRU notes in `disagreements`); a sub-terminal designator matches the wrong or no GEM unit (check `_unit_designators` — needs exactly one unit in one terminal + name/owner corroboration); owner deltas look systematically wrong (check the GEM cell separator/bracket format vs `parse_entity_list`); a "(Mothballed)"/"(stopped)" GIIGNL row is still summed into the operating total or doesn't corroborate its GEM non-op unit (check the `status` column in `giignl_extracted.csv`, the `_NONOP_STATUSES` membership, and `_corroborate_nonop` token match against site_name+trains); a terminal where GIIGNL's NARRATIVE corrects the table's operating status (a train listed untagged but the prose says it's down — Bontang Train F) is still over-summed (add an entry to `giignl_prose_corrections.json` keyed country+site+section with the `nonoperating_units` + citation, and confirm `_apply_prose_corrections` matched the unit token to the report row) |
| `report_diff.py` | Diff buckets (matches / fuzzy / report-only / gem-only / nonoperating_units / ambiguous). Parameterized on report type so the same script serves GIIGNL and (future) IGU | Adding a new reconcilable source; match algorithm over/under-merging |
| `fsru_sync_check.py` | Cross-check FSRU records between GEM terminals and LNG carrier project backends | Sync conventions change; reassignment detection misfires |
| `build_review_package.py` | xlsx scaffolding — sheets, color fills, frozen panes, headers | Adding a new sheet section; changing color convention |
| `recalc.py` | Open the xlsx, force recalc, return any formula errors | Always run before present_files |

Trust the scripts by default. They're versioned scaffolding, not throwaway code. Read the source when behavior surprises you — and if you fix something, the user can copy the patched file back into project knowledge so the next batch benefits.

## Output workbook structure

Single combined xlsx per batch, written to the **in-repo** `batches/` directory at the repo root: `<repo-root>/batches/lng_terminals_batch_<YYYYMMDD>_<HHMM>_ET.xlsx`. The Eastern-time HHMM disambiguates multiple batches in one day. Generate via:

    TZ=America/New_York date "+%Y%m%d_%H%M_ET"

**Path caveat — the `../batches/` shorthand in the workflow commands assumes the working directory is `scripts/`.** The canonical target is the tracked `batches/` dir *inside* this repo (it has a `.gitkeep`). If you invoke the build from the repo root (e.g. `python scripts/build_review_package.py …`), use `--output batches/…`, NOT `--output ../batches/…` — the latter resolves to a sibling of the repo and `mkdir(parents=True)` will silently create a stray external dir. **Always confirm the written file is under `<repo-root>/batches/` after building.**

**Never overwrite an existing batch file — every (re)build gets a NEW file with a freshly-generated timestamp.** Regenerate the stamp at build time (don't reuse one captured earlier in the session) and pass it as `--output`. This applies even to small iterative rebuilds within one session (e.g. tweak a color, then add a column → two distinct files). Multiple files per day is the intended behavior; the user prunes old ones.

Sheets (empty sheets are omitted from the final workbook):

| Sheet | Populated when | Contents |
|---|---|---|
| `README` | Always | Batch params, color conventions, **per-sheet definitions for every other tab in this workbook**, and input-summary stats (incl. any SOP §6 gate trips). The definitions are sourced from `SHEET_DESCRIPTIONS` in `scripts/build_review_package.py` — required so a researcher can open the file without prior context and know what each tab is for. |
| `updates` | Update workflow | Rows for existing units being updated, with old → new diffs and citations |
| `new_terminals` | Discovery workflow | Newly discovered projects (project-level fields) |
| `new_units` | Discovery or update | Unit-level data for new terminals AND new units within existing terminals (expansions, new trains) |
| `status_timeline_additions` | Any workflow touching status | Append-only timeline entries to add to the live DB per methodology |
| `entity_additions` | Any workflow adding owners | New immediate owners/operators/vessel-owners to create, with duplicate-check flags |
| `giignl_diff_operating` | Reconciliation workflow | OPERATING match audit: GEM operating capacity vs GIIGNL's operating-only tables. One project-total row per match; per-unit rows beneath it for unit-granularity matches (GIIGNL row ⊃ GEM unit name, e.g. Arzew GL1Z↔GL1Z) — see `level` column. `gem_unit_name` = operating units only. Conflicting cells red — capacity conflicts graded by size (light red <5% delta, darker red >=5% or undefined); owner-only deltas light red; fuzzy `confidence` yellow (see Color conventions). |
| `giignl_diff_nonoperating` | Reconciliation workflow | Non-operating units (proposed/construction/shelved/cancelled/idled/mothballed/retired) of matched projects. Each defaults to a light-red `gem_only_flag` = "GEM has, GIIGNL doesn't" unless the §3.2.1 narrative pass filled `giignl_narrative_mention` (confirmed forward phase, no conflict). |
| `giignl_to_action` | Reconciliation workflow | Workflow routing: findings categorized for Update / Discovery / Review |
| `candidate_edits` | Reconciliation workflow | GEM-CSV-shaped sheet (115 cols + 2 meta cols) of GEM unit-rows flagged by the diff — for editing in DB shape |
| `giignl_full_extract` | Reconciliation workflow | Raw GIIGNL extraction (every row parsed from the PDF) for reference |
| `fsru_sync` | Any batch touching FSRUs | Cross-check matches / mismatches / reassignments |
| `monitor_list` | Discovery workflow | Candidates that don't meet "sufficient information to add" threshold |
| `stale_sweep` | Triage or update | Stale-flag output from `stale_sweep.py` |
| `country_notes_contributions` | Any batch developing new country knowledge | Drafted additions to GEM's country-resource Google doc, for user to copy over manually |
| `qa_review` | Always | Per-cell citation log, conflicts, defects, verification log, negative-result log |

**When adding a new sheet builder to `build_review_package.py`, also add a corresponding entry to `SHEET_DESCRIPTIONS`** in that same file — otherwise the README will fall back to a "no description registered" placeholder that prompts the next agent to backfill it.

## Color conventions (cells in `updates`, `new_units`, `giignl_diff_operating`)

Ported from the carrier project, with one addition:

- **Green** — high confidence: primary/regulatory source (FERC, DOE, EU PCI portal, national regulator, sponsor IR) OR two independent corroborating sources agreeing on the value
- **Yellow** — entity-level confirmation but value implied, contested, or from a single non-primary source
- **Red** — single weak source; prefer leaving the cell blank with a `qa_review` log entry
- **Blue** (terminals-specific) — value unchanged from existing DB value but re-verified this batch (the methodology's "no changes" outcome, applied at cell granularity)

Confidence applies per cell, not per row.

**Reconciliation override for the `giignl_diff_*` sheets:** their cell semantics differ. In `giignl_diff_operating`, **red marks a GIIGNL-vs-GEM value conflict** (any non-zero capacity delta — compared at 2-decimal precision, no tolerance band — or an owner present in one source but not the other; on a per-unit row, the unit's capacity cells when that unit disagrees), applied to the conflicting field cell(s) plus the row's `disagreements` summary cell. **Capacity conflicts are graded by size:** a `<5%` capacity delta gets **light red** (FFE5E5); a `>=5%` delta (or an undefined delta, i.e. GEM capacity is 0) gets a **darker red** (FFB0B0). This is purely a visual severity cue — every non-zero delta is still flagged, nothing is suppressed by the band. Owner-only deltas stay light red. **Yellow** flags the `confidence` cell of a fuzzy (medium-confidence) match. In `giignl_diff_nonoperating`, **light red marks "GEM has, GIIGNL doesn't"** (`gem_only_flag` + `gem_unit_name`) — the default for a non-op unit, suppressed only when the §3.2.1 narrative pass confirms the forward phase. Agreeing/confirmed cells are left unfilled. See Reconciliation SOP §4. (The single-weak-source meaning of red above governs `updates` / `new_units`, not the `giignl_diff_*` sheets.)

## Hard requirements (these override anything below)

- **Never modify the live GEM database.** Every batch produces a staging xlsx; the user applies edits manually. The agent's edit footprint is exactly zero on the production DB.
- **Every URL passes the verification gate before going in the xlsx** — no exceptions, even URLs that worked in prior batches. URLs decay; paywalls change; soft-errors happen.
- **Pull a fresh GEM CSV at the start of every batch** — the user (and other GEM staff) edit between batches.
- **Re-derive the column-index map from the fresh header row** — don't hard-code offsets, the 115-col schema can drift.
- **Never auto-apply GIIGNL or IGU values.** A reconciliation finding is a candidate for Update, not an applied edit.
- **Project-level field changes apply to ALL unit-rows of a multi-unit project.** The export duplicates project-level fields across unit-rows; updates must too, or the next export will show inconsistencies.
- **No orphan `[ref]` cells** — never fill a `[ref]` without a paired data value in the same cell-pair (carries over from carrier project Rule F).
- **Status timeline updates require pulling the existing timeline first** via `fetch_timeline.py` — the export only has current status + anchor years, not the full ordered timeline.
- **Don't create duplicate entities.** Run `entity_lookup.py` before staging any new owner/operator/parent. The methodology is emphatic — entities are shared across all GEM trackers, and duplicates create real cleanup work for the Ownership Team.
- **Out-of-scope fields are read-only.** LH2, NH3, SyntheticLNG, RetrofitProposed, AltFuelPrelimAgreement, AltFuelCallMarketInterest, AltFuelNotes, PCINotes, PCI3-PCI6 are explicitly "no longer updated as of 2026" per the methodology. The build script must NEVER write to these columns.

## When to escalate to the user

Pause and ask before proceeding when:

- A whole class of GEM values looks systematically wrong (suggests a schema misunderstanding, not a research finding)
- A methodology rule and an SOP rule conflict
- A discovery batch surfaces more than ~5 candidate clusters in the same country (suggests systematic gap — could be a research priority signal, but worth a conversation before generating 5+ new project records)
- The "sufficient information to add" threshold is genuinely ambiguous on a candidate (sponsor named but extremely vague location, or vice versa)
- A reconciliation batch finds disagreement on more than ~10% of matched rows (suggests either a GIIGNL methodology change or a systematic GEM issue) — judge this by *material* capacity/owner conflicts, not the raw `matches_with_disagreement` count, which now inflates because any non-zero capacity delta flags and owner-set deltas are usually benign (see Reconciliation SOP §6)
- An entity that should exist in the GEM entity system isn't found — could be a search issue, or could be a real gap
- The GIIGNL report file isn't in either expected format (real PDF v1.7 with text layer, or legacy zip-of-JPEGs+OCR) — layout change requires confirming `giignl_extract.py` still works
- FSRU sync surfaces a reassignment that can't be cleanly resolved (vessel moved to a terminal that doesn't exist in GEM yet)
