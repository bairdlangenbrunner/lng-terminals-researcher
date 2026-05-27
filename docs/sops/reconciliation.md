# LNG Terminals Reconciliation SOP

Last revised: 2026-05 (rev 1, initial draft)

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
2. **Which GIIGNL sections** are in scope. Default: both the liquefaction table (operating + recently-commissioned export terminals) and the regasification table (operating + recently-commissioned import terminals). Country narratives are also in scope as a secondary source for proposed/construction projects that may inform Discovery routing.
3. **Which GEM lifecycle states to compare against** — default: GIIGNL is operating-only, so the reconciliation primarily matches against GEM `operating`, `idled`, `mothballed`, `retired` rows (GIIGNL keeps recently-retired entries for one report cycle). GEM `construction` rows may match GIIGNL narrative mentions, but the value-level diff only meaningfully applies to operating capacity.
4. **Whether to include the country-summary tables** (per-country totals) as a sanity check on GEM's project-level rollups. Default: yes.

These parameters get written into the staging xlsx README sheet.

## §3 Workflow

### §3.1 Setup

1. Verify the GIIGNL report file is in project files at `<path-to-giignl-report>` (or wherever the user placed it).
2. `file <path>` to confirm format. The 2026 GIIGNL came as a zip of per-page JPEG + OCR text files + manifest.json, NOT as a parseable PDF. If the format differs, the extractor may need adjustment.
3. Materialize scripts to working directory per the CLAUDE.md instructions:
   - `pull_gem_db.py`, `normalize.py`, `dedup_index.py`
   - `giignl_extract.py`, `report_diff.py`, `url_verifier.py`
   - `build_review_package.py`, `recalc.py`
4. `python pull_gem_db.py` → fresh GEM CSV at `gem_export.csv`. **Mandatory** per the [ref]-fill SOP discipline — the database changes between batches.

### §3.2 Extract GIIGNL into structured form

`python giignl_extract.py <path-to-giignl-report> --output giignl_extracted.csv`

The extractor produces a flat CSV with GEM-aligned column names so the diff is column-comparable. See Appendix A for the per-table extraction rules.

**The extractor is vision-assisted, not pure regex.** GIIGNL tables have column structure that's lost in text-only OCR (the per-page `.txt` files have rows wrapped unpredictably). The extractor uses the per-page JPEG images plus the OCR text as a confirmation channel. Output rows include a `_source_page` column for traceability.

Verify the extraction before proceeding:
- Total liquefaction MTPA in the extracted CSV should match the GIIGNL Key Figures page (524 MTPA in 2026 edition)
- Total regasification MTPA should match Key Figures (1,247 MTPA in 2026 edition)
- Per-country subtotals (where GIIGNL displays them) should match the sum of country rows
- If totals don't match within 2%, suspect missing rows from OCR/parsing — investigate before continuing

### §3.3 Normalize both sides

`python normalize.py` is imported as a module by `report_diff.py`. Both the GEM CSV and the GIIGNL CSV go through:
- Country name normalization (ISO names, common variants)
- Owner/operator entity normalization (per `docs/reference/entity_canonical_map.md`)
- Capacity unit normalization (everything → mtpa)
- Terminal name normalization (strip "LNG Terminal", "FSRU", "FLNG" suffixes; handle "T1"/"Train 1" variants)

The normalized values are used for matching ONLY; the unnormalized values are preserved in the diff output for human readability.

### §3.4 Run the diff

`python report_diff.py --gem gem_export.csv --report giignl_extracted.csv --output giignl_diff.json`

The script produces a four-way classification per (country, normalized-terminal-name) pair:

| Classification | Meaning | Default route |
|---|---|---|
| **Match — values agree** | Both have the entity, values align within tolerance | Confidence bump only; no edit needed |
| **Match — values disagree** | Both have the entity, one or more fields differ | → Update workflow |
| **GIIGNL-only** | GIIGNL has it, GEM doesn't | → Discovery workflow |
| **GEM-only** | GEM has it, GIIGNL doesn't | → log only (usually expected, see §3.7) |

The script also produces a fifth category for human resolution:

| Classification | Meaning | Default route |
|---|---|---|
| **Ambiguous match** | Multiple GEM rows could match one GIIGNL row, or vice versa | Manual review in `giignl_diff` sheet |

### §3.5 Matching algorithm

Two-pass match:

**Pass 1: exact match on (normalized country, normalized terminal name).** Highest confidence. Direct hit.

**Pass 2: fuzzy match within country** for unmatched GIIGNL rows. For each unmatched GIIGNL row, score every GEM row in the same country by:
- Token-set similarity of terminal name (e.g. "Arzew GL3Z" vs "Arzew LNG Terminal" → high overlap on "Arzew")
- Owner-entity overlap (any common entity → bonus)
- Capacity proximity (within 30% of nominal MTPA → bonus)
- Start-year proximity (within 2 years → bonus)
- FSRU vessel name match (when both rows are FSRUs) → strong bonus

Scores above a threshold get a "probable match" classification; below threshold = no match. Ambiguous when two GEM rows score within 10% of each other against the same GIIGNL row.

**Matching is at the project level, not the unit level**, because GIIGNL aggregates per-site and GEM splits into units. A GIIGNL row like "Arzew GL3Z, 4.7 MTPA, 1 train" matches a GEM project that may have one or more units; the diff records the GIIGNL-side numbers against the *project total* from GEM's per-unit rollup. If the GEM project's per-unit breakdown doesn't sum to the GIIGNL number, that itself is a `value-disagreement`.

### §3.6 Disagreement classification rules

Value disagreements get classified by field type, since each field has its own default cause-of-disagreement:

**Capacity disagreements** — most common. Usual causes:
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

Produces an xlsx with the standard sheets plus two reconciliation-specific sheets:

- `giignl_diff` — full diff output, color-coded per cell (green = match, yellow = ambiguous, red = disagreement, blue = GEM-only-expected, no fill = GIIGNL-only-needs-discovery)
- `giignl_to_action` — actionable findings with proposed routing (Update vs Discovery vs Review)

Empty sheets are omitted per CLAUDE.md convention.

`python recalc.py ../batches/lng_terminals_batch_<YYYYMMDD>_<HHMM>_ET.xlsx` → zero formula errors.

`present_files`.

### §3.11 Errata log

When reconciliation finds GIIGNL clearly wrong (e.g. capacity figure that contradicts the operator's own filings), record in `country_notes_contributions` sheet under "GIIGNL errata observed". Over multiple years this builds a useful record of GIIGNL's failure modes (which countries it covers poorly, which kinds of fields it gets wrong) that informs future reconciliations.

## §4 Confidence labels (reconciliation-specific)

Standard color scheme from CLAUDE.md applies, with reconciliation-specific cell semantics:

- **Green** — Match with values agreeing within tolerance. Confidence bump on the GEM record; no edit needed.
- **Yellow** — Match but values disagree, OR ambiguous match. Requires Update workflow follow-up.
- **Red** — Disagreement where GIIGNL contradicts GEM on a primary field (status, capacity) and the disagreement looks substantive. Requires Update workflow follow-up and probably new source research.
- **Blue** — GEM-only finding that's expected (GIIGNL gap, not a GEM error). No action needed; re-verified by absence.

GIIGNL-only findings get no color fill — they're not GEM cells, they're new candidates.

## §5 Edge cases and gotchas

### §5.1 GIIGNL's geographic scope ≠ GEM's

GIIGNL is import/export-focused and largely member-driven. Some terminals never appear in GIIGNL even though they exist (small-scale, non-member countries, certain Russian terminals post-sanctions). The country-resource doc and `docs/country_notes/` should track known GIIGNL coverage gaps.

### §5.2 FSRU vessel reassignments

GIIGNL reports the FSRU vessel currently at each terminal. If a terminal swapped FSRUs since the last GIIGNL, the diff will show the FSRU vessel name disagreement. This is real signal — route to Update workflow with the FSRU sync rule (CLAUDE.md) for cross-check against the carrier project.

GIIGNL sometimes shows a recently-departed FSRU at its old terminal because GIIGNL is published months after year-end. Don't immediately treat as "GIIGNL is wrong" — check whether GEM's record has the swap-out documented.

### §5.3 Multi-terminal sites

Some sites host multiple terminals (e.g. one country's main LNG hub). GIIGNL may aggregate or split differently from GEM. The matching algorithm's "ambiguous match" classification catches this — it requires manual resolution before any action.

### §5.4 Operating-but-not-yet-in-GIIGNL

GIIGNL covers operating terminals through the report year. A terminal that started up in early calendar year covered by the report should appear; one that started in late Q4 of that year often doesn't. If a recently-started GEM `operating` terminal isn't in GIIGNL, check the GEM `ActualStartYear` — if Q4 or later, expect it in next year's GIIGNL.

### §5.5 Floating storage units (FSU/FRU) not in liquefaction or regasification tables

FSU and FRU vessels are non-standard. GIIGNL handling varies. Check the terminal narrative sections for mentions rather than expecting tabular rows.

### §5.6 The capacity numbers in GIIGNL's narrative don't always match its own tables

GIIGNL's country narratives sometimes cite a different capacity number than the GIIGNL tabular row for the same terminal. When this happens, prefer the tabular value for the diff (it's the structured source) and log the narrative discrepancy as a GIIGNL errata.

## §6 Pause-and-ask triggers

Stop and consult the user before proceeding when:

- More than ~10% of matched rows have value disagreements → systematic issue (GIIGNL methodology change, GEM schema misunderstanding, or extractor bug). Don't auto-route 100+ Update batches; review the pattern first.
- The extractor produces totals that diverge from GIIGNL's Key Figures by more than 2% → likely missing rows. Don't proceed with an incomplete diff.
- GIIGNL-only findings exceed ~30 candidates → may indicate a GEM coverage gap for a whole region, worth scoping a Discovery batch around it rather than treating as 30 individual discoveries.
- The GIIGNL report file is in an unexpected format (not the zip-of-images structure) → extractor needs adjustment before proceeding.
- A country shows GIIGNL country-summary totals that diverge dramatically from the sum of GEM operating capacity for that country → could be a country definition mismatch (e.g. one source includes a disputed territory) or a real coverage gap.

---

## Appendix A — GIIGNL-specific extraction rules

These are the rules that `giignl_extract.py` implements. They're documented here because they evolve with each GIIGNL edition.

### A.1 Source format (2026 edition)

The 2026 GIIGNL Annual Report file is named `.pdf` but is actually a zip archive containing:
- 80 JPEG page images (`1.jpeg` through `80.jpeg`)
- 80 OCR text files (`1.txt` through `80.txt`)
- `manifest.json` with per-page metadata

OCR text quality is decent for prose, structurally messy for tables (column boundaries lost, rows wrap). The extractor uses both:
- OCR text as primary source for narrative pages
- JPEG images via vision processing for tabular pages, with OCR text as a confirmation channel

### A.2 Page sections (2026 edition)

| Pages | Section | Use |
|---|---|---|
| 1-3 | Cover, profile, editorial | Skip |
| 4-7 | Key figures, narrative overview | Use Key Figures totals as extraction sanity check |
| 8-27 | Trade dynamics narrative | Skip for diff; informational |
| 28-31 | Liquefaction narrative | Use country sections as secondary signal for Discovery routing |
| 32-37 | **Liquefaction tables** | Primary extraction source for export terminal diff |
| 48-52 | Regasification narrative | Use country sections as secondary signal |
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

### A.6 OCR artifact handling

The 2026 OCR shows these consistent artifacts:
- `\u0002` characters appearing as soft-hyphen breaks within words (e.g. `Mids\u0002cale` for "Midscale")
- Line breaks (`\r\n`) inserted mid-cell, especially in long owner descriptions
- Numbers occasionally split across lines (`125,\n000` for "125,000")
- Capacity unit suffixes ("MTPA") rendered inconsistently

The extractor's text-cleanup pass:
1. Strip `\u0002` characters
2. Re-join wrapped numeric values
3. Normalize whitespace
4. Re-attach orphaned units to preceding numbers

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
| Run diff | `python report_diff.py --gem ... --report ... --output giignl_diff.json` |
| Verify URLs (for any pre-searched corroborating sources) | `python url_verifier.py <url> <expected...>` |
| Build staging xlsx | `python build_review_package.py --mode reconciliation --report giignl --year <YEAR>` |
| Sanity check | `python recalc.py <xlsx>` |
| Present | `present_files` |
