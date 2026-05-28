# LNG Terminals Reconciliation SOP

Last revised: 2026-05-28 (rev 5)

Revision notes:
- rev 5 (2026-05-28): three fixes. (1) `giignl_extract.py` now skips the standalone page footer ("GIIGNL Annual Report <year> Edition") during line classification — it had been merged into the last data row of each page, corrupting 8 rows and poisoning the country walk (dropped QatarEnergy LNG S(2) T4 → S(2) read 9.4 not 14.1; mis-countried Ruwais/San Juan/Yamal T1/etc.) — §3.2. (2) `report_diff.py` gained `_split_multiterminal_fsru_sites` (§3.5/§5.3): a GIIGNL FSRU port that GEM models as several distinct terminals (Wilhelmshaven, Ain-Sokhna) is split per vessel and each routed to its GEM terminal via `FloatingVesselName`, instead of summing into one bogus project. (3) `giignl_diff_operating` capacity-conflict fill is now graded by size — light red <5%, darker red >=5% (§4). Known follow-up: non-FSRU multi-terminal complexes (Qatar Ras Laffan) still compare at project total (§5.3, TODO).
- rev 4 (2026-05-28): `giignl_diff` split into TWO sheets — `giignl_diff_operating` (GEM operating capacity vs GIIGNL's operating-only tables) and `giignl_diff_nonoperating` (matched projects' non-op units, each defaulting to a "GEM has, GIIGNL doesn't" highlight unless the §3.2.1 narrative pass confirms the forward phase). `report_diff.py` gained **unit-level alignment** (§3.5): GIIGNL rows whose site name contains a GEM unit name (GIIGNL "Arzew GL1Z" ⊃ GEM unit "GL1Z") align 1:1 to GEM units, with a project-total fallback (Taichung) when they don't; a conservative unit-code fold groups per-complex rows ("Arzew GL1Z/2Z/3Z" → one "Arzew" project) so they match and align. `gem_unit_name` on a match now lists OPERATING units only.
- rev 3 (2026-05-28): narrative prose extraction promoted from an informal "secondary source" note to an actual workflow step (new §3.2.1) — the operating-only tables miss proposed/construction/expansion activity that the country narratives disclose. `report_diff.py` gained report-side expansion-row folding (§3.5) and deterministic (sorted) set iteration (§3.4). New §5.7 distinguishes forward-looking narrative phases from table disagreements.
- rev 2 (2026-05-27): pipeline rewritten for real-PDF input (`pdftotext -layout` instead of zip-of-JPEGs+vision). §3.5 matching algorithm extended to three passes (canonical / alias-incl-LocalNames-with-transliteration / 3-criteria fuzzy). Project key now includes `section_type` (Sabine-Pass-style mixed-facility-type terminals split into two project entries). §3.10 batch filename convention pinned to `lng_terminals_batch_<YYYYMMDD>_<HHMM>_ET.xlsx`; README sheet-definitions block now mandatory.
- rev 1 (2026-05): initial draft (zip-of-JPEGs + vision pipeline).

Operational rules for reconciling the GEM LNG terminals database against an authoritative annual report — primarily GIIGNL, with the same workflow body intended to serve a future IGU reconciliation SOP. This SOP describes how to do the diff cleanly; the *fixes* go through the Update or Discovery workflows. Reconciliation surfaces work; it does not perform it.

The methodology doc (LNG Terminals Manual) is authoritative for the underlying research rules. This SOP is operational.

## §1 When to run this SOP

Trigger conditions:
- A new GIIGNL Annual Report has been published (typically June, covering the prior calendar year) and added to the project files
- The user explicitly requests a reconciliation batch
- Triage SOP §3 flags "unprocessed GIIGNL reconciliation" as a backlog item

Do NOT run reconciliation:
- More than once against the same report edition (it's an annual workflow, not recurring)
- Against partial or draft GIIGNL releases — wait for the published edition
- As a substitute for Update or Discovery batches — its outputs are inputs to those, not replacements

## §2 Confirm parameters at batch start

Before any tool runs, confirm with the user:

1. **Which report edition** — typically the year on the cover (e.g. "GIIGNL 2026 Annual Report" covers calendar year 2025 trade data)
2. **Which GIIGNL sections** are in scope. Default:
   - The liquefaction table (operating + recently-commissioned export terminals) and the regasification table (operating + recently-commissioned import terminals) — the **primary structured diff input** (§3.4).
   - The country-**narrative** prose sections (liquefaction + regasification narratives — Appendix A.2 page ranges) — a **secondary but actual extraction step** (§3.2.1), not a manual skim. The tables are operating-only; the narratives are where GIIGNL discloses proposed, under-construction, and expansion activity, which routes to Discovery and Update + `status_timeline_additions`. Confirm whether to run the prose pass this batch (default: yes).
3. **Which GEM lifecycle states to compare against** — default: GIIGNL is operating-only, so the reconciliation primarily matches against GEM `operating`, `idled`, `mothballed`, `retired` rows (GIIGNL keeps recently-retired entries for one report cycle). GEM `construction` rows may match GIIGNL narrative mentions, but the value-level diff only meaningfully applies to operating capacity.
4. **Whether to include the country-summary tables** (per-country totals) as a sanity check on GEM's project-level rollups. Default: yes.

These parameters get written into the staging xlsx README sheet.

## §3 Workflow

### §3.1 Setup

1. Verify the GIIGNL report file is in project files at `<path-to-giignl-report>` (or wherever the user placed it).
2. `file <path>` to confirm format. Two formats observed across editions:
   - **Real PDF (current pipeline)** — file reports "PDF document, version 1.7". The 2026 edition received 2026-05 is this format. `giignl_extract.py` parses via `pdftotext -layout` against page text.
   - **Zip-disguised-as-PDF (legacy)** — file reports a zip archive, contains per-page JPEG + OCR text files + manifest.json. The pre-2026 pipeline staged JPEGs and did vision-LLM extraction. That code path is in git history and would need restoration if a future edition reverts.
3. The scripts are committed to `scripts/` (no separate "materialize" step needed):
   - `gem_query.py` / `gem_all_fields.py` for the GEM pull (no auth cookies needed)
   - `giignl_extract.py`, `report_diff.py`, `url_verifier.py`
   - `build_review_package.py`, `recalc.py`
4. `python scripts/gem_query.py --all-fields lng -o gem_export.csv` → fresh GEM CSV. **Mandatory** per the [ref]-fill SOP discipline — the database changes between batches.
5. `python scripts/pull_gem_db.py --map-only --out gem_export.csv` → derives the column-index map `gem_export.colmap.json` (consumed by `report_diff.py` and `build_review_package.py`).

### §3.2 Extract GIIGNL into structured form

`python scripts/giignl_extract.py <path-to-giignl-report.pdf> --output giignl_extracted.csv`

The extractor produces a flat CSV with GEM-aligned column names so the diff is column-comparable. See Appendix A for the per-table extraction rules.

**Pipeline (2026 edition, real PDF):** `pdftotext -layout` is invoked per page; the column positions are derived from the table header row's keyword positions; each page is partitioned into rows by data-line midpoint heuristics with multi-line cell merging. Country labels are assigned via a SEQUENTIAL walk (`_assign_countries_sequential` in `giignl_extract.py`) with **per-country capacity budgets sourced from the subtotal lines** (e.g. "Bangladesh 7.5 MTPA") — once cumulative capacity for the current country exceeds its subtotal (2% tolerance), subsequent rows go into a pending buffer that gets back-filled when the next country's label arrives. This is what prevents China's rows from getting tagged Bangladesh when China's label appears mid-block. Train suffixes ("T1", "T1-6", "T1 - T6") get stripped into a separate `trains` column so multiple GIIGNL train-rows roll up to one project-level entry on report_diff's side.

Output rows include a `report_page` column for traceability back to the PDF.

Verify the extraction before proceeding:
- Total liquefaction MTPA in the extracted CSV should match the GIIGNL Key Figures page (524 MTPA in 2026 edition)
- Total regasification MTPA should match Key Figures (1,247 MTPA in 2026 edition)
- Per-country subtotals (where GIIGNL displays them) should match the sum of country rows
- If totals don't match within 2%, suspect missing rows from OCR/parsing — investigate before continuing

### §3.2.1 Narrative prose extraction (secondary pass)

The liquefaction/regasification *tables* are operating-only and feed the structured diff (§3.4). The country-*narrative* sections (Appendix A.2 page ranges) are where GIIGNL discloses **proposed / under-construction / expansion** activity, and that signal is valuable enough to be a real step, not an informal read.

Read the narrative pages and extract, for each terminal mentioned with a concrete development, a structured candidate carrying:
- project + sponsor/operator (normalize via `docs/reference/entity_canonical_map.md`)
- lifecycle signal (proposed / FID / construction-start / commissioning / expansion)
- anchor date(s) — construction-start month/year, target completion year
- capacity figure, and whether it's a **new unit** or an **expansion** of existing capacity
- source page (for traceability)

Canonical example — the bar for "extract, don't skim":

> "PipeChina commenced construction of three 240,000 cbm LNG tanks at its Yuedong terminal in December 2025, adding to three existing 160,000 cbm tanks. The expansion will boost the terminal's regasification capacity to 6 MTPA, with completion targeted for December 2028."

That single paragraph clears the methodology's "sufficient information to update" bar: it identifies the project (Yuedong / PipeChina), flips lifecycle proposed→construction with a Dec-2025 anchor, logs an **expansion** (not a new unit), sets regas capacity to 6 MTPA, and gives a Dec-2028 target. It should land as an Update + a `status_timeline_additions` entry — not get lost in prose.

Routing:
- **Project not in GEM** → Discovery candidate. Apply the "sufficient information to add" threshold; below-threshold mentions go to `monitor_list`.
- **Project in GEM, lifecycle/capacity change** → Update + `status_timeline_additions` (pull the existing timeline first per the Update SOP — the export has only current status + anchor years).
- Every prose-derived finding carries a `GIIGNL <year> narrative, p.<n>` citation. Like the tables, GIIGNL prose is **not authoritative and never auto-applied** (§3.8) — it's a routing candidate that goes through the normal source-search and confidence labeling.

Prose findings do **not** enter `giignl_diff` (that sheet is the table-level match audit). They land in `giignl_to_action` with their target route.

**Implementation status:** this pass is **agent-driven today** — the agent reads the narrative pages (the 2026 text layer is clean per Appendix A.1) and produces the structured candidates directly. `giignl_extract.py` parses the **tables only**; do not expect it to surface prose findings. A future helper (`giignl_prose_extract.py`, or an extension of `giignl_extract.py`) could pre-filter narrative paragraphs containing capacity/date/lifecycle keywords to focus the read — see the TODO item. Per Appendix A.2, the in-scope narrative pages for the 2026 edition are the liquefaction narrative (pp. 28–31) and the regasification narrative (pp. 48–52); always re-derive page ranges per edition.

### §3.3 Normalize both sides

`normalize.py` is imported as a module by `report_diff.py`. Both the GEM CSV and the GIIGNL CSV go through:
- Country name normalization (ISO names, common variants — `_COUNTRY_MAP`)
- Owner/operator entity normalization (per `docs/reference/entity_canonical_map.md` — `_ENTITY_MAP`)
- Capacity unit normalization (everything → mtpa — `to_mtpa()` / `_CAPACITY_TO_MTPA`)
- Terminal name normalization (strip "LNG Terminal", "FSRU", "FLNG" suffixes; handle "T1"/"Train 1" variants — `normalize_terminal_name()`)
- **LocalNames transliteration** (`transliterate_to_english()`): GEM's `LocalNames` column may contain names in non-Latin scripts (Chinese, Korean, etc.). For Chinese, the helper segments with **jieba** and runs **pypinyin** per-word so each Chinese word becomes a distinctive 4+ char Latin token (e.g. `中石油唐山曹妃甸LNG接收站` → `zhong shiyou tangshan caofeidian lng jieshouzhan`). The transliterated variants are registered as aliases alongside `OtherNames`. Hooks present for Japanese / Korean / Arabic / Russian; only Chinese implemented today.

The normalized values are used for matching ONLY; the unnormalized values are preserved in the diff output for human readability.

### §3.4 Run the diff

`python scripts/report_diff.py --report giignl --extracted giignl_extracted.csv --gem-csv gem_export.csv --output giignl_diff.json`

(Note the flags: `--report {giignl,igu}` selects the report type, `--extracted` is the GIIGNL CSV from §3.2, `--gem-csv` is the GEM export. Earlier drafts of this SOP showed `--gem`/`--report <csv>`, which the script rejects.)

**Run-to-run determinism:** the diff is now reproducible — the set iterations in the classifier (`matched_report_keys`, `giignl_only_keys`, `gem_only_keys`) are sorted before iterating, so two runs on identical inputs produce byte-identical `giignl_diff.json` (fixed 2026-05-28; previously the fuzzy/gem-only boundary jittered ±1–2 rows because the fuzzy pass `discard()`s from `gem_only_keys` as it assigns matches and set order was hash-randomized). You can safely re-run `report_diff.py` without the counts drifting.

The script produces a four-way classification per (country, normalized-terminal-name) pair:

| Classification | Meaning | Default route |
|---|---|---|
| **Match — values agree** | Both have the entity, capacity is identical (to 2 decimals) and owner sets match | Confidence bump only; no edit needed |
| **Match — values disagree** | Both have the entity, one or more fields differ | → Update workflow |
| **GIIGNL-only** | GIIGNL has it, GEM doesn't | → Discovery workflow |
| **GEM-only** | GEM has it, GIIGNL doesn't | → log only (usually expected, see §3.7) |

The script also produces a fifth category for human resolution:

| Classification | Meaning | Default route |
|---|---|---|
| **Ambiguous match** | Multiple GEM rows could match one GIIGNL row, or vice versa | Manual review in `giignl_diff` sheet |

### §3.5 Matching algorithm

Three-pass match:

**Pass 1a: exact match on (normalized country, normalized TerminalName, section_type).** Highest confidence. Direct hit on GEM's primary name.

**Pass 1b: alias match on (normalized country, normalized alias, section_type).** Same confidence as 1a. Aliases come from BOTH the `OtherNames` column AND the `LocalNames` column — and for non-Latin LocalNames (Chinese today, hooks for Japanese / Korean / Arabic / Russian later), `normalize.transliterate_to_english` produces additional English-script variants. Chinese path: jieba word segmentation + pypinyin per-word → e.g. `中石油唐山曹妃甸LNG接收站` emits `zhong shiyou tangshan caofeidian lng jieshouzhan`, giving distinctive 4+ char tokens (`tangshan`, `caofeidian`) that the fuzzy pass can match. Example matches added by this pass: GIIGNL's `Kribi` → GEM's `Cameroon FLNG Terminal` (via OtherNames `Kribi FLNG Terminal`), GIIGNL's `Aqaba` → GEM's `Sheikh Sabah LNG Terminal`, GIIGNL's `Świnoujście` → GEM's `Świnoujście Polskie LNG Terminal`. Diff records these as `match_type=exact_via_alias` with the `matched_alias` column showing which alias hit.

**Pass 2: fuzzy match within country and section_type** for unmatched GIIGNL rows. For each unmatched GIIGNL row, a GEM project is a fuzzy candidate iff (any of):
- (a) **substring match** — the normalized GIIGNL site name is contained in any GEM name (canonical or alias) OR vice versa; strong signal
- (b) **token + owner overlap** — at least one shared 4+ char token AND at least one shared owner-entity tag; the owner confirms the token
- (c) **multi-token overlap** — 2+ distinctive shared 4+ char tokens (catches cases where the owner cell was truncated/mis-parsed; 2 distinctive tokens are strong enough to surface as a candidate even without owner overlap)

Token extraction strips leading/trailing punctuation so `"(tangshan),"` tokenizes as `"tangshan"`. Candidates include all aliases (OtherNames + LocalNames + transliterations) so a single distinctive city name like `Caofeidian` from a Chinese LocalName can serve as a matching token.

Score every GEM row in the same country+section by:
- Token-set similarity of terminal name (e.g. "Arzew GL3Z" vs "Arzew LNG Terminal" → high overlap on "Arzew")
- Owner-entity overlap (any common entity → bonus)
- Capacity proximity (within 30% of nominal MTPA → bonus)
- Start-year proximity (within 2 years → bonus)
- FSRU vessel name match (when both rows are FSRUs) → strong bonus

Scores above a threshold get a "probable match" classification; below threshold = no match. Ambiguous when two GEM rows score within 10% of each other against the same GIIGNL row.

**Pass 3: unit-level alignment within a matched project.** Project matching (passes 1–2) finds the right GEM project; this pass then tries to align each GIIGNL row to a *specific GEM unit*. The bridge is that a GEM unit name often appears as a token inside the GIIGNL site name — GIIGNL `Arzew GL1Z` ⊃ GEM unit `GL1Z`. A GEM unit is accepted for a report row when its normalized name is a token-subset of the report site name AND (the unit name is code-like, i.e. contains a digit, OR the capacities are within 25%). When ≥1 unit aligns, the match is `match_granularity = "unit"` and the diff carries a `unit_matches` list (per-unit GIIGNL-vs-GEM capacity comparison); the `giignl_diff_operating` sheet renders one row per aligned unit beneath the project-total row. When nothing aligns (GIIGNL's rows don't map to GEM's unit names — e.g. Taichung's `Taichung`/`Taichung Expansion` rows vs GEM's `Phase N` units), it stays `match_granularity = "project"` and only the project total is compared. Implemented as `_align_units` in `report_diff.py`. Arzew is the canonical 1:1 case (GIIGNL GL1Z/GL2Z/GL3Z ↔ GEM units, all agree; the retired `GL4Z` GEM has but GIIGNL doesn't lands in `giignl_diff_nonoperating`). **Project-spanning guard:** a unit alignment is accepted only when the GIIGNL row's capacity is at least as close to that unit's capacity as to the GEM project total — otherwise a single GIIGNL row that actually covers the whole terminal gets mis-pinned to one unit by a coincidental code token, producing a contradictory unit-level conflict beside an agreeing project total. Worked example: GIIGNL `Portovaya LNG T1 (+ Portovyy FSU)` = 1.5 MTPA (the whole terminal); without the guard it pinned to GEM unit `T1` (0.75) and emitted a spurious unit-level 100% disagreement next to the correct project-level 1.5-vs-1.5 match. With the guard, Portovaya stays `match_granularity = "project"`.

**Project-level fallback.** GIIGNL aggregates per-site and GEM splits into units, so when unit alignment fails the diff records the GIIGNL-side numbers against the GEM *project total* (operating-unit rollup). If that total doesn't match the GIIGNL number, it's a `value-disagreement`. Either way, only **operating** GEM capacity enters the comparison (GIIGNL's tables are operating-only) — non-operating units are split out to `giignl_diff_nonoperating` (§3.10).

**Multi-terminal FSRU sites — split by vessel.** GIIGNL labels several physically distinct FSRU terminals at one port with the SAME site name, disambiguating only by vessel. `_split_multiterminal_fsru_sites` routes each GIIGNL vessel row to the GEM terminal whose **terminal-level `FloatingVesselName`** carries that vessel (GIIGNL "Excelerate Excelsior" ⊇ GEM "Excelsior"), then emits one report sub-project per GEM terminal — display name carries the vessel (e.g. "Wilhelmshaven (Höegh Esperanza)"), each force-matched. It fires only when the site's distinct vessels resolve to **≥2 distinct GEM terminals** AND every row maps. Worked examples: Germany "Wilhelmshaven" (Höegh Esperanza → GEM "Wilhelmshaven FSRU"; Excelerate Excelsior → GEM "Wilhelmshaven TES FSRU"); Egypt "Ain-Sokhna" (Energos Power → GEM "Ain Sokhna FSRU"; Höegh Galleon + Energos Eskimo → GEM "Sumed FSRU" — note GEM Ain Sokhna carries Höegh *Gallant*, a different retired vessel). This also recovers GEM terminals that GIIGNL conflates under the neighbour's label (Sumed was previously a false gem-only).

**Single-berth FSRU — operating-vessel capacity only.** For a port that GEM models as ONE terminal cycling vessels (one operating unit + superseded vessels as `retired`/`idled` units), where GIIGNL still lists each deployed FSRU as a separate operating row, `_fsru_operating_report_capacity` aligns each GIIGNL FSRU row to a GEM unit **by vessel name** (GEM's `unit_name` is the vessel identity) and sums only the rows mapping to a GEM *operating* unit; rows mapping to a retired/idled GEM unit, or to no GEM unit, become per-vessel notes in `disagreements` (a status/discovery signal, not a capacity delta). This is the fallback for the genuinely single-terminal case (the multi-terminal split above handles ports GEM models as several terminals). (If GEM runs several FSRUs concurrently at one terminal, all map to operating units and the full sum is compared — the rule self-adjusts.)

**Same-name terminals disambiguated by first owner.** GEM distinguishes multiple distinct terminals that share a base name by appending the first owner in parentheses — `Tianjin LNG Terminal (PipeChina)` / `(Sinopec)` / `(Beijing Gas Group)` (common for Chinese terminals; also Salina Cruz, QatarEnergy LNG (N)/(S)). When ≥2 GEM terminals in a country+section share a base name (paren stripped), `_build_gem_project_table` treats the parenthetical as an **owner tag**, not a name token: it is added to `owners_set` and the fuzzy match-tokens are built from the base name only. Without this, the owner word ("sinopec") matches as a name token and drags in every other same-owner terminal — GIIGNL `Tianjin LNG (Sinopec)` went `ambiguous` against Liuheng/Longkou (Sinopec). The fuzzy pass strips the report-side parenthetical too, and when several candidates remain it prefers the one whose GEM parenthetical owner equals the GIIGNL row's **first owner**. Result: each Tianjin GIIGNL row routes to the right sibling (Sinopec 10.8 vs 10.8 agrees; PipeChina 6 vs 12 and Nangang/Beijing 12 vs 5 surface as real capacity findings).

**The project key is `(country_norm, name_norm, section_type)`, not just `(country_norm, name_norm)`** — a single GEM `TerminalName` may host BOTH liquefaction (export) AND regasification (import) units (Sabine Pass is the canonical example: 6 export trains plus 1 import terminal under one TerminalName). Without `section_type` in the key, their capacities sum incorrectly and the GIIGNL liquefaction-table row gets compared against the inflated total. The implementation lives in `_build_gem_project_table` in `report_diff.py` and applies symmetrically to the report side in `_classify`.

**Expansion-row folding (report side).** GIIGNL splits a phased terminal across separate rows — e.g. Taiwan lists `Taichung` (6.1 MTPA, 2009) and `Taichung Expansion` (1.9 MTPA, 2025) as two rows for the single CPC terminal that GEM models as one project (8.0 MTPA across Phase 1/2/2-expansion units). GEM collapses its units to a project total of 8.0, so comparing the un-summed `Taichung` row (6.1) against it produces a spurious ~24% capacity disagreement while `Taichung Expansion` orphans into `report_only`. To fix this, `_classify` folds a report row whose name ends in **"Expansion"** or **"Extension"** into the base `<Site>` group (summing capacity, unioning owners). The fold is deliberately conservative — it only triggers when the stripped base name resolves to a real partner (another report row, a GEM canonical key, or a GEM alias). This avoids merging two failure modes that look superficially similar:
- **Extraction artifacts** — a bare `expansion` (China row whose real site name split onto a prior line), `(Gravity-Based Structure) expansion`, `Zeebrugge Expansion Krk` (Belgium+Croatia merged). These have no resolvable base, so they stay as `report_only` and remain flagged for the extractor fixes (see TODO). (The former page-footer-leak artifacts — "Dabhol Expansion nual Report 2026 Edition" etc. — are now fixed upstream: `giignl_extract.py` skips the standalone "GIIGNL Annual Report <year> Edition" footer line, see §3.2.)
- **Genuinely distinct named stages/trains** that lack an "Expansion" suffix — `Senboku II`, `Corpus Christi Stage III`, `Bontang Train E` — are never touched by the fold.

**Unit-code folding (report side).** A second conservative fold handles per-complex rows that carry a unit/complex *code* suffix — Algeria's Sonatrach complexes `Arzew GL1Z` / `Arzew GL2Z` / `Arzew GL3Z` (and `Skikda GL1K`), which GEM models as units inside one project (`Arzew-Bethioua LNG Terminal`). `_strip_unit_code_suffix` peels a trailing token of the form *1-4 letters + digits + optional letter* (`GL1Z`, `GL2Z`, `GL1K`) — the digit requirement is what protects genuinely distinct named stages with no digit (`Senboku II`, `Bontang Train E`, `Corpus Christi Stage III`). The fold fires when the stripped base resolves to a GEM key/alias **or** ≥2 report rows share the base (`Arzew` is confirmed by its three peers). Once folded to one `Arzew` project, the substring-fuzzy pass matches it to `Arzew-Bethioua` and Pass 3 aligns the three rows 1:1 to GEM units `GL1Z/GL2Z/GL3Z`.

When either fold happens, the diff entry carries a `report_sites_merged` list (e.g. `["Taichung", "Taichung Expansion"]` or `["Arzew GL1Z", "Arzew GL2Z", "Arzew GL3Z"]`) so the merge is auditable. **Watch for post-fold capacity gaps:** Yangshan Shanghai (report 12.0 vs GEM 6.0) surfaces the *expansion* capacity as a real fuzzy-match disagreement — investigate whether GEM is missing the expansion units or GIIGNL double-counts, per §3.6.

### §3.6 Disagreement classification rules

Value disagreements get classified by field type, since each field has its own default cause-of-disagreement:

**Capacity disagreements** — most common. **Any non-zero capacity difference is a conflict** (compared at the 2-decimal precision the diff reports), not just a delta above some percentage band. A 1.0 MTPA gap on a mid-size terminal (e.g. Zeebrugge: GEM 12.3 vs GIIGNL 11.3, ~8%) and a 0.04 MTPA rounding gap (e.g. Sergipe: GEM 5.64 vs GIIGNL 5.6) both get flagged red — the researcher decides materiality during the Update pass; the diff's job is to surface every difference, not to pre-filter. (There is intentionally no tolerance band: a prior >10% threshold silently hid real sub-10% discrepancies.) Usual causes:
- Unit conversion error in either source (GIIGNL is always MTPA for these tables)
- Per-train vs total reconciliation issue (GEM has 6 units of 3.3 MTPA = 19.8 MTPA project total; GIIGNL shows 22.2 MTPA — investigate the difference)
- Expansion or debottlenecking captured by one source but not the other
- One source quoting nameplate, the other quoting actual achieved capacity (methodology says use nameplate)

**Start-year disagreements** — usual causes:
- Planned vs actual confusion
- Different definition of "operating" (commissioning cargo vs commercial operations — see methodology FAQ on Calcasieu Pass)
- Multi-train projects with staggered starts being averaged

**Owner disagreements** — usual causes:
- Immediate owner vs ultimate parent
- Stale data in one source after a recent ownership change
- JV percentages cited differently (GIIGNL often shows percentages; GEM stores immediate owner separately from parent)

**Status disagreements** — usual causes:
- GIIGNL drops shelved/cancelled projects entirely; if GEM has the project as proposed and GIIGNL doesn't list it, that's GEM-only (expected), not a status disagreement
- GIIGNL lists a project that GEM has as `cancelled` → strong signal GEM is wrong; check if the project was revived

Each disagreement goes into `giignl_diff` sheet with a `disagreement_category` column drawn from the above. The Update workflow uses the category to pick its source-search strategy.

### §3.7 Routing GEM-only findings

GEM-only is the most common classification and usually requires no action — GIIGNL has known gaps:
- GIIGNL doesn't comprehensively cover small-scale or non-member-country terminals
- GIIGNL drops projects below a coverage threshold
- GIIGNL only covers operating; GEM tracks proposed/construction/shelved/cancelled

**Flag for review** when GEM-only is suspicious:
- GEM `operating` status in a GIIGNL-member country that GIIGNL doesn't list — possibly a GEM error (project was actually cancelled or never operated)
- GEM project listed in a country where GIIGNL's country-summary total wouldn't accommodate it (e.g. GEM has a 5 MTPA terminal in a country GIIGNL reports as 8 MTPA total when GEM's other terminals already sum to 8)
- GEM `operating` with `LastUpdated > 18 months` and not in GIIGNL — possibly stale data that should move to `mothballed`/`retired`

These get routed to `giignl_to_action` sheet with `route: review` (not directly to Update) — the conclusion may be "GEM is correct, GIIGNL gap" rather than an actionable edit.

### §3.8 No auto-application of GIIGNL values

**Hard rule.** A value disagreement is a *candidate* for update, not an applied edit. Every disagreement goes through the Update workflow's normal source-search and confidence-labeling process. The methodology FAQ is explicit: "if we find a more specific or current source on a terminal that conflicts with the report, that source/data should take priority."

The reconciliation batch's xlsx output includes:
- `giignl_diff` sheet — every diff finding with full context (both sides' values, classification, category)
- `giignl_to_action` sheet — findings that route to Update or Discovery, with target action noted

The Update / Discovery batches that consume these findings cite GIIGNL as ONE source among others, with the same source-tier treatment as other annual industry reports. Per `docs/reference/source_roster.md`, GIIGNL is Tier 1 but not authoritative — sponsor IR or primary regulatory filings take priority.

### §3.9 URL verification

Any URLs included in the staging xlsx (e.g. for GIIGNL-only findings where the agent has pre-searched for confirming sources) must pass `url_verifier.py` per the standard rules. The GIIGNL document itself is NOT a URL-citable source for individual rows — there's no per-row URL into a paginated PDF. Cite GIIGNL by edition year and table name in a separate `report_citation` column, not as a URL.

### §3.10 Build the staging package

`python build_review_package.py --mode reconciliation --report giignl --year <YEAR> --output ../batches/lng_terminals_batch_<YYYYMMDD>_<HHMM>_ET.xlsx`

Get the Eastern-time stamp via `TZ=America/New_York date "+%Y%m%d_%H%M_ET"`. The HHMM_ET suffix disambiguates multiple batches in one day.

**README sheet definitions are MANDATORY.** Every staging xlsx must include a "Sheet definitions" block in the README listing every other tab and what it contains, so a researcher opening the file without prior context knows what each tab is for. This is handled automatically by `build_review_package.py` via the `SHEET_DESCRIPTIONS` constant + `_populate_readme_sheet_defs(wb)` helper, which is invoked at the end of `main()`. If you add a new sheet builder to the script, you MUST add a corresponding entry to `SHEET_DESCRIPTIONS` — otherwise the README will fall back to a "no description registered" placeholder that prompts the next agent to fix it.

Produces an xlsx with the standard sheets plus three reconciliation-specific sheets:

- `giignl_diff_operating` — OPERATING match audit: GEM operating capacity vs GIIGNL's operating-only tables. One project-total row per match (exact + fuzzy); for `match_granularity = "unit"` matches (§3.5), one per-unit row is emitted beneath it (the `level` column distinguishes `project` from `unit` rows). `gem_unit_name` lists **operating units only** (so the unit list reconciles with the operating capacity). `report_sites_merged` lists folded rows (expansion or unit-code, §3.5). **Red fill** marks conflicting cells: the `disagreements` cell, the four capacity columns when capacity differs at all (any non-zero delta), `owners_report_only`/`owners_gem_only` when non-empty, and a per-unit row's capacity cells when that unit disagrees. **Capacity conflicts are graded by size** — light red (FFE5E5) for a `<5%` delta, darker red (FFB0B0) for `>=5%` (or undefined when GEM capacity is 0); owner-only deltas stay light red (§4). Fuzzy matches get a yellow `confidence` cell. (Triggers mirror `report_diff.py`'s disagreement logic; keep in sync.)
- `giignl_diff_nonoperating` — non-operating units (proposed/construction/shelved/cancelled/idled/mothballed/retired) of **matched** projects. GIIGNL's tables are operating-only, so each row defaults to a light-red `gem_only_flag` = "GEM has, GIIGNL doesn't" UNLESS the §3.2.1 narrative pass populated `giignl_narrative_mention` (a confirmed forward phase → no conflict per §5.7; left unfilled). Worked example: Taichung Phase 3 (in the p.52 narrative → no highlight) vs Phase 4 (absent everywhere → highlighted); Arzew `GL4Z` retired → highlighted (GIIGNL drops retired).
- `giignl_to_action` — actionable findings with proposed routing (Update vs Discovery vs Review)

Empty sheets are omitted per CLAUDE.md convention.

`python recalc.py ../batches/lng_terminals_batch_<YYYYMMDD>_<HHMM>_ET.xlsx` → zero formula errors.

`present_files`.

### §3.11 Errata log

When reconciliation finds GIIGNL clearly wrong (e.g. capacity figure that contradicts the operator's own filings), record in `country_notes_contributions` sheet under "GIIGNL errata observed". Over multiple years this builds a useful record of GIIGNL's failure modes (which countries it covers poorly, which kinds of fields it gets wrong) that informs future reconciliations.

## §4 Cell colors in the reconciliation sheets (reconciliation-specific)

This is what `build_review_package.py` actually applies — it overrides the generic CLAUDE.md color scheme for these sheets.

**`giignl_diff_operating`:**
- **Red — a value in conflict between GIIGNL and GEM:** any non-zero capacity delta (compared at 2-decimal precision — no tolerance band), or an owner present in one source but not the other. Applied per-cell to the conflicting field(s) — the four capacity columns and/or `owners_report_only` / `owners_gem_only` — plus the row's `disagreements` summary cell. On a per-unit row, the unit's capacity cells get the fill when that unit disagrees. Every such finding routes to the Update workflow (§3.8: do NOT auto-apply GIIGNL values). **Capacity conflicts are graded by size** (`_cap_conflict_fill` in `build_review_package.py`):
  - **Light red (FFE5E5)** — capacity delta `<5%` (relative to GEM capacity, the `capacity_delta_pct` column).
  - **Darker red (FFB0B0)** — capacity delta `>=5%`, OR an undefined delta (GEM capacity is 0, so the percent can't be computed — treated as material). This is a visual severity cue only; the no-tolerance-band rule is unchanged (every non-zero delta is still flagged — see §3.6/§5). Owner-only deltas and the `disagreements` summary cell stay light red.
- **Yellow (FFF8E1)** — the `confidence` cell of a fuzzy (medium-confidence) match. Flags that the *match itself* is uncertain and should be verified before the diff is trusted.
- **No fill** — capacity is identical (to 2 decimals) and owner sets match, or the cell is not part of a disagreement.

This sheet contains only matched projects (operating side); GEM-only and GIIGNL-only *projects* live in `giignl_to_action`.

**`giignl_diff_nonoperating`:**
- **Light red (FFE5E5)** — the `gem_only_flag` and `gem_unit_name` cells of a non-op unit that GIIGNL does NOT cover (no operating-table row and no narrative mention) → "GEM has, GIIGNL doesn't". This is the default for non-op units.
- **No fill** — `giignl_narrative_mention` is populated (the §3.2.1 prose pass found GIIGNL discussing this forward phase): a confirmed phase on the same trajectory, NOT a conflict (§5.7).

Note: owner-set deltas (operating sheet) are the most common disagreement and usually benign — GIIGNL lists the full JV while GEM stores the immediate owner(s) (see §3.6). They still get the light-red fill, but most route to "log only / confidence note". Real research signal concentrates in the capacity-delta reds (especially the **darker** >=5% ones) and in the non-op highlights.

## §5 Edge cases and gotchas

### §5.1 GIIGNL's geographic scope ≠ GEM's

GIIGNL is import/export-focused and largely member-driven. Some terminals never appear in GIIGNL even though they exist (small-scale, non-member countries, certain Russian terminals post-sanctions). The country-resource doc and `docs/country_notes/` should track known GIIGNL coverage gaps.

### §5.2 FSRU vessel reassignments

GIIGNL reports the FSRU vessel currently at each terminal. If a terminal swapped FSRUs since the last GIIGNL, the diff will show the FSRU vessel name disagreement. This is real signal — route to Update workflow with the FSRU sync rule (CLAUDE.md) for cross-check against the carrier project.

GIIGNL sometimes shows a recently-departed FSRU at its old terminal because GIIGNL is published months after year-end. Don't immediately treat as "GIIGNL is wrong" — check whether GEM's record has the swap-out documented.

### §5.3 Multi-terminal sites

Some sites host multiple terminals (e.g. one country's main LNG hub). GIIGNL may aggregate or split differently from GEM. The matching algorithm's "ambiguous match" classification catches this — it requires manual resolution before any action.

**FSRU ports GEM models as several terminals** are handled automatically by `_split_multiterminal_fsru_sites` (§3.5): GIIGNL gives each FSRU terminal at a port the same site name (disambiguated only by vessel), so the rows are split by vessel and routed to the matching GEM terminal via `FloatingVesselName`. Examples: Wilhelmshaven (Höegh Esperanza ↔ "Wilhelmshaven FSRU", Excelerate Excelsior ↔ "Wilhelmshaven TES FSRU"), Ain-Sokhna (Energos Power ↔ "Ain Sokhna FSRU"; Höegh Galleon + Energos Eskimo ↔ "Sumed FSRU"). **Caveat — non-FSRU multi-terminal complexes are NOT auto-split:** the Qatar Ras Laffan complex (GIIGNL "QatarEnergy LNG N(1..4)/S(1..3)" sub-rows vs GEM's two terminals "QatarEnergy LNG (N)"/"(S)", each with multi-train units) still matches at project total and per-sub-row fuzzy, so a GIIGNL sub-complex (e.g. S(2)=14.1) is compared against the whole GEM terminal total (S=36.3) rather than the matching GEM unit (S(2) T3-5=14.1). Treat these project-level deltas as "complex split differently," not real capacity conflicts, until a code-token unit-alignment pass is added (see TODO).

### §5.4 Operating-but-not-yet-in-GIIGNL

GIIGNL covers operating terminals through the report year. A terminal that started up in early calendar year covered by the report should appear; one that started in late Q4 of that year often doesn't. If a recently-started GEM `operating` terminal isn't in GIIGNL, check the GEM `ActualStartYear` — if Q4 or later, expect it in next year's GIIGNL.

### §5.5 Floating storage units (FSU/FRU) not in liquefaction or regasification tables

FSU and FRU vessels are non-standard. GIIGNL handling varies. Check the terminal narrative sections for mentions rather than expecting tabular rows.

### §5.6 The capacity numbers in GIIGNL's narrative don't always match its own tables

GIIGNL's country narratives sometimes cite a different capacity number than the GIIGNL tabular row for the same terminal. When this happens, prefer the tabular value for the diff (it's the structured source) and log the narrative discrepancy as a GIIGNL errata.

### §5.7 The narrative describes *future* phases the operating table doesn't (not a disagreement)

The liquefaction/regasification tables are operating-only, but the country narrative routinely forward-references phases that aren't operating yet. **Don't mistake a forward-looking phase mention for a table-vs-table capacity disagreement.** Worked example (Taiwan, CPC Taichung, 2026 edition): the table rows sum to 8.0 MTPA (`Taichung` 6.1 + `Taichung Expansion` 1.9), the p.48 narrative says the terminal "reached a total nominal capacity of 8 MTPA in 2026 following the commencement of operations of Phase 2," and then mentions Phase 3. GEM correctly shows the terminal at 8.0 MTPA operating with Phase 3 (construction, →10) and Phase 4 (proposed, →13) as non-operating units. All three sources agree; there is no conflict — the table, the narrative's "8 MTPA," and GEM's operating total are the same number, and the Phase 3/4 figures are simply later points on the same trajectory.

So when GEM's operating total matches the table but the narrative names higher future-phase capacities: confirm GEM already carries those phases as `construction`/`proposed` units (confidence bump), rather than logging a capacity disagreement. If GEM is *missing* a narrated under-construction/proposed phase, that routes to Discovery/Update as a new-unit finding — this is exactly what the §3.2.1 narrative prose pass is for. Narrative phase mentions are a routing input to Discovery/Update, never a `giignl_diff` table-disagreement row.

## §6 Pause-and-ask triggers

Stop and consult the user before proceeding when:

- More than ~10% of matched rows have value disagreements → systematic issue (GIIGNL methodology change, GEM schema misunderstanding, or extractor bug). Don't auto-route 100+ Update batches; review the pattern first. **Apply this to *material* disagreements, not the raw count.** Since any non-zero capacity delta now flags (§3.6) and owner-set deltas are usually benign (full JV vs immediate owner, §4), the raw `matches_with_disagreement` count is dominated by rounding-level capacity gaps and owner-list differences. Judge this trigger by the share of rows with a *substantive* capacity or owner conflict, not by the headline `disagreement_pct_of_matches` the README prints.
- The extractor produces totals that diverge from GIIGNL's Key Figures by more than 2% → likely missing rows. Don't proceed with an incomplete diff.
- GIIGNL-only findings exceed ~30 candidates → may indicate a GEM coverage gap for a whole region, worth scoping a Discovery batch around it rather than treating as 30 individual discoveries.
- The GIIGNL report file is in an unexpected format (not the real-PDF-v1.7 path that the current `giignl_extract.py` expects, and not the legacy zip-of-JPEGs structure either) → extractor needs adjustment before proceeding.
- A country shows GIIGNL country-summary totals that diverge dramatically from the sum of GEM operating capacity for that country → could be a country definition mismatch (e.g. one source includes a disputed territory) or a real coverage gap.
- The §3.2.1 prose pass surfaces more than ~5 proposed/construction candidates in one country that GEM lacks → same signal as the GIIGNL-only >30 trigger at a smaller scale: likely a regional coverage gap worth scoping as a Discovery batch rather than routing individually.

---

## Appendix A — GIIGNL-specific extraction rules

These are the rules that `giignl_extract.py` implements. They're documented here because they evolve with each GIIGNL edition.

### A.1 Source format (2026 edition, real PDF)

The 2026 GIIGNL Annual Report received 2026-05 is a real PDF v1.7 (80 pages, A4, Adobe InDesign-produced) with a clean text layer. The extractor uses `pdftotext -layout` per page; the layout-preserving mode keeps column structure intact enough to parse with character-position windows.

(Earlier editions shipped as zip-of-JPEGs+OCR-text+manifest.json — file would report a zip archive instead of "PDF document". That pipeline staged page JPEGs and did vision-LLM extraction; it's preserved in git history if a future edition reverts.)

### A.2 Page sections (2026 edition)

| Pages | Section | Use |
|---|---|---|
| 1-3 | Cover, profile, editorial | Skip |
| 4-7 | Key figures, narrative overview | Use Key Figures totals as extraction sanity check |
| 8-27 | Trade dynamics narrative | Skip for diff; informational |
| 28-31 | Liquefaction narrative | **Prose-extraction pass (§3.2.1)** — extract proposed/construction/expansion mentions for Discovery/Update routing |
| 32-37 | **Liquefaction tables** | Primary extraction source for export terminal diff |
| 48-52 | Regasification narrative | **Prose-extraction pass (§3.2.1)** — extract proposed/construction/expansion mentions for Discovery/Update routing |
| 53-62 | **Regasification tables** | Primary extraction source for import terminal diff |
| 64-77 | Contracts, shipping, member info | Skip for diff |

Page numbers may shift between editions — always re-derive section boundaries from the report's TOC or by content-pattern detection.

### A.3 Liquefaction table schema

Columns observed in 2026:
1. Country (with subtotal MTPA shown for multi-project countries)
2. Project name (e.g. "Arzew GL3Z", "NLNG T1", "Idku T2")
3. Nominal capacity (MTPA, decimal)
4. Number of trains (integer, typically 1 per row since rows are per-train)
5. Number of tanks (integer)
6. Total storage capacity (liq m³)
7. Owner(s) — free text with percentages, e.g. "Sonatrach" or "ENI 50%, EGAS 40%, EGPC 10%"
8. Operator
9. MT-LT Buyer(s) — comma-separated entities
10. Start date — year only

Extractor produces normalized CSV with columns:
- `_giignl_section` = "liquefaction"
- `_source_page` (integer)
- `country` (raw)
- `country_normalized` (per normalize.py)
- `project` (raw)
- `project_normalized` (lowercased, "T1"/"Train 1" unified)
- `facility_type` = "export"
- `capacity_mtpa` (float)
- `n_trains` (int)
- `n_tanks` (int)
- `storage_m3` (int)
- `owners_raw` (text)
- `owners_parsed` (list of {entity, pct})
- `operator` (text)
- `buyers_raw` (text)
- `buyers_parsed` (list of entities)
- `start_year` (int)

### A.4 Regasification table schema

Columns observed in 2026:
1. Market (country)
2. Site (with FSRU vessel name appended when applicable, e.g. "Escobar / Excelerate Expedient (FSRU)")
3. Concept ("Onshore" or "Offshore")
4. Number of tanks
5. Total capacity (liq m³)
6. Number of vaporizers (may be N/A for FSRUs)
7. Nominal capacity (MTPA, decimal)
8. Owner — free text, often split into "Owner: X / Charterer: Y" for FSRUs
9. Operator — free text, often split for FSRUs as "FSRU: X / Terminal: Y"
10. Third Party Access (Yes/No/dash)
11. Additional Services offered (text or dash)
12. Start-up date — year only

Extractor produces normalized CSV with columns:
- `_giignl_section` = "regasification"
- `_source_page`
- `country` (raw and normalized)
- `site` (raw)
- `site_normalized`
- `facility_type` = "import"
- `is_floating` (bool, derived from "FSRU" or "FLNG" in site/concept)
- `vessel_name` (when floating, extracted from site text)
- `concept` = "onshore" | "offshore"
- `capacity_mtpa` (float)
- `n_tanks`, `storage_m3`, `n_vaporizers`
- `owners_raw`, `owners_parsed`
- `charterer` (when FSRU)
- `operator_raw`, `operator_parsed`
- `terminal_operator` (when FSRU has separate terminal operator)
- `tpa` (bool — Third Party Access)
- `additional_services` (text)
- `start_year` (int)

### A.5 Country subtotal rows

GIIGNL inserts subtotal labels for some countries (e.g. "Algeria 25.3 MTPA"). The extractor:
- Detects subtotal rows by pattern: country name + capacity + "MTPA" without other fields
- Uses subtotals as a sanity check (sum of per-project rows in that country should match)
- Does NOT produce an output row for subtotals (they're metadata)

### A.6 PDF text-layer artifact handling (2026 edition, real PDF)

`pdftotext -layout` output is clean for body text but has layout artifacts the extractor handles:

- **Country labels vertically centered** against their block — a label is linearized AFTER some of its rows and BEFORE others. Handled by `_assign_countries_sequential`'s pending buffer (back-filled at the next label).
- **Country block boundaries invisible from text alone** when Country X's last row is immediately followed by Country Y's first row (no label or separator between). Handled via **per-country capacity budgets** sourced from subtotal lines: once cumulative > subtotal × 1.02, the next row goes pending instead of inheriting current_country. This is what stops China's Beihai/Caofeidian/etc. from getting tagged Bangladesh on page 55.
- **Multi-line cells** (owner descriptions wrapping 3-5 physical lines) merged via data-line-anchored partitioning (each data line owns lines around it up to the midpoint with the adjacent data line).
- **Multi-line country labels** like "Mauritania/" + "Senegal" or "Equatorial" + "Guinea" stitched based on line proximity + no intervening data line.
- **Super-region markers** like "ATLANTIC BASIN: 236.5 MTPA" / "ASIA: 707.9 MTPA" / "MIDDLE EAST: …" — detected via `_SUPER_REGION_RE` and skipped (they look superficially like country labels).
- **Subtotal-line overlap** — sometimes "7.5 MTPA" sits on the same physical line as an adjacent row's owner-cell continuation. Detection requires col 0 matches the subtotal pattern AND the capacity column is empty (data rows always have capacity; subtotals don't). The owner continuation that happened to share this line is lost — acceptable trade-off vs missing the country budget signal.

(The pre-2026 vision pipeline handled different artifacts — soft-hyphen breaks, OCR-wrapped numbers, etc. See git history if a future edition reverts to the zip-of-JPEGs format.)

### A.7 What to add for IGU (future)

IGU's World LNG Report has different table layouts but the same conceptual content. The shared `report_diff.py` body works unchanged; only `igu_extract.py` differs from `giignl_extract.py`. Likely IGU-specific changes:
- Different section page ranges
- IGU often uses bcm/y as primary unit (convert via `capacity_normalize.py`)
- IGU's "operating capacity" definitions may differ from GIIGNL — document in the IGU SOP appendix

---

## Quick-reference card

| Step | Command |
|---|---|
| Pull GEM | `python pull_gem_db.py` |
| Extract GIIGNL | `python giignl_extract.py <path-to-giignl-report> --output giignl_extracted.csv` |
| Verify extraction totals | Compare against GIIGNL Key Figures (524 MTPA liq / 1,247 MTPA regas for 2026 edition) |
| Run diff | `python report_diff.py --report giignl --extracted giignl_extracted.csv --gem-csv gem_export.csv --output giignl_diff.json` |
| Verify URLs (for any pre-searched corroborating sources) | `python url_verifier.py <url> <expected...>` |
| Build staging xlsx | `python build_review_package.py --mode reconciliation --report giignl --year <YEAR>` |
| Sanity check | `python recalc.py <xlsx>` |
| Present | `present_files` |
