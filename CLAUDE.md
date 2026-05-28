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
4. `python giignl_extract.py <path-to-giignl-report> --output giignl_extracted.csv` → flat CSV with GEM-aligned column names per Reconciliation SOP §3 (Appendix A for GIIGNL-specific table parsing).
5. `python report_diff.py --gem gem_export.csv --report giignl_extracted.csv --output giignl_diff.json` → three-way diff (matches, GIIGNL-only, GEM-only, value-disagreements).
6. Route findings per Reconciliation SOP §4:
   - GIIGNL-only → Discovery workflow (verify candidate is real and in-scope before adding)
   - GEM-only → log in `giignl_to_action` sheet, usually no action (GIIGNL has known gaps per the methodology FAQ)
   - Value-disagreement → Update workflow (GIIGNL is one source in a conflict, NOT automatically authoritative — the methodology FAQ says a more specific or current source takes priority)
   - Match → confidence bump on the GEM record
7. **DO NOT auto-apply GIIGNL values to the GEM record.** Every value-disagreement requires resolution through the Update workflow's normal source-search and confidence-labeling process.
8. `python build_review_package.py --mode reconciliation --report giignl --year <YEAR>` → staging xlsx with `giignl_diff` and `giignl_to_action` sheets in addition to the standard sheets.
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
| `giignl_extract.py` | Parses GIIGNL report into a flat CSV with GEM-aligned columns. 2026 edition is a real PDF v1.7 with a clean text layer — uses `pdftotext -layout` + column-position-based row partitioning; per-country capacity subtotals are used as block-boundary budgets so rows route to the right country even when labels appear mid-block. Earlier editions shipped as zip-of-JPEGs + OCR; that pipeline lives in git history if a future edition reverts | New GIIGNL edition layout changes column positions; new country added to super-region marker list; subtotal detection misfires |
| `report_diff.py` (alias matching) | Project key includes `section_type` so a single GEM terminal with both liquefaction and regasification (e.g. Sabine Pass: 6 export trains + 1 import terminal) splits into two distinct projects, not one summed entry. Alias map includes GEM `OtherNames` + `LocalNames`, with CJK transliteration via jieba + pypinyin (e.g. `中石油唐山曹妃甸LNG接收站` → `zhong shiyou tangshan caofeidian lng jieshouzhan` so distinctive city tokens can match) | New non-Latin language appears in LocalNames; matching needs additional script support |
| `report_diff.py` | Three-way diff (matches / report-only / GEM-only / value-disagreements). Parameterized on report type so the same script serves GIIGNL and (future) IGU | Adding a new reconcilable source; match algorithm over/under-merging |
| `fsru_sync_check.py` | Cross-check FSRU records between GEM terminals and LNG carrier project backends | Sync conventions change; reassignment detection misfires |
| `build_review_package.py` | xlsx scaffolding — sheets, color fills, frozen panes, headers | Adding a new sheet section; changing color convention |
| `recalc.py` | Open the xlsx, force recalc, return any formula errors | Always run before present_files |

Trust the scripts by default. They're versioned scaffolding, not throwaway code. Read the source when behavior surprises you — and if you fix something, the user can copy the patched file back into project knowledge so the next batch benefits.

## Output workbook structure

Single combined xlsx per batch: `../batches/lng_terminals_batch_<YYYYMMDD>_<HHMM>_ET.xlsx`. The Eastern-time HHMM disambiguates multiple batches in one day. Generate via:

    TZ=America/New_York date "+%Y%m%d_%H%M_ET"

Sheets (empty sheets are omitted from the final workbook):

| Sheet | Populated when | Contents |
|---|---|---|
| `README` | Always | Batch params, color conventions, **per-sheet definitions for every other tab in this workbook**, and input-summary stats (incl. any SOP §6 gate trips). The definitions are sourced from `SHEET_DESCRIPTIONS` in `scripts/build_review_package.py` — required so a researcher can open the file without prior context and know what each tab is for. |
| `updates` | Update workflow | Rows for existing units being updated, with old → new diffs and citations |
| `new_terminals` | Discovery workflow | Newly discovered projects (project-level fields) |
| `new_units` | Discovery or update | Unit-level data for new terminals AND new units within existing terminals (expansions, new trains) |
| `status_timeline_additions` | Any workflow touching status | Append-only timeline entries to add to the live DB per methodology |
| `entity_additions` | Any workflow adding owners | New immediate owners/operators/vessel-owners to create, with duplicate-check flags |
| `giignl_diff` | Reconciliation workflow | Match-level audit: one row per matched project (exact or fuzzy), with side-by-side capacity, owner-set deltas, and disagreements column |
| `giignl_to_action` | Reconciliation workflow | Workflow routing: findings categorized for Update / Discovery / Review |
| `candidate_edits` | Reconciliation workflow | GEM-CSV-shaped sheet (115 cols + 2 meta cols) of GEM unit-rows flagged by the diff — for editing in DB shape |
| `giignl_full_extract` | Reconciliation workflow | Raw GIIGNL extraction (every row parsed from the PDF) for reference |
| `fsru_sync` | Any batch touching FSRUs | Cross-check matches / mismatches / reassignments |
| `monitor_list` | Discovery workflow | Candidates that don't meet "sufficient information to add" threshold |
| `stale_sweep` | Triage or update | Stale-flag output from `stale_sweep.py` |
| `country_notes_contributions` | Any batch developing new country knowledge | Drafted additions to GEM's country-resource Google doc, for user to copy over manually |
| `qa_review` | Always | Per-cell citation log, conflicts, defects, verification log, negative-result log |

**When adding a new sheet builder to `build_review_package.py`, also add a corresponding entry to `SHEET_DESCRIPTIONS`** in that same file — otherwise the README will fall back to a "no description registered" placeholder that prompts the next agent to backfill it.

## Color conventions (cells in `updates`, `new_units`, `giignl_diff`)

Ported from the carrier project, with one addition:

- **Green** — high confidence: primary/regulatory source (FERC, DOE, EU PCI portal, national regulator, sponsor IR) OR two independent corroborating sources agreeing on the value
- **Yellow** — entity-level confirmation but value implied, contested, or from a single non-primary source
- **Red** — single weak source; prefer leaving the cell blank with a `qa_review` log entry
- **Blue** (terminals-specific) — value unchanged from existing DB value but re-verified this batch (the methodology's "no changes" outcome, applied at cell granularity)

Confidence applies per cell, not per row.

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
- A reconciliation batch finds disagreement on more than ~10% of matched rows (suggests either a GIIGNL methodology change or a systematic GEM issue)
- An entity that should exist in the GEM entity system isn't found — could be a search issue, or could be a real gap
- The GIIGNL report file isn't in either expected format (real PDF v1.7 with text layer, or legacy zip-of-JPEGs+OCR) — layout change requires confirming `giignl_extract.py` still works
- FSRU sync surfaces a reassignment that can't be cleanly resolved (vessel moved to a terminal that doesn't exist in GEM yet)
