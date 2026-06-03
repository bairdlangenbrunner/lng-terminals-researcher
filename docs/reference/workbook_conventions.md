# Output workbook conventions

Full sheet definitions and color semantics for the staging xlsx. The naming/path/timestamp rules are restated as hard requirements in `CLAUDE.md`; this file carries the detail.

## File naming and location

Single combined xlsx per batch, written to the **in-repo** `batches/` directory at the repo root: `<repo-root>/batches/lng_terminals_batch_<YYYYMMDD>_<HHMM>_ET[_<scope>]_<mode>.xlsx`. The Eastern-time HHMM disambiguates multiple batches in one day. Generate via:

    TZ=America/New_York date "+%Y%m%d_%H%M_ET"

**The name says what it is** (convention since 2026-06): the `<mode>` token (`update` / `discovery` / `reconciliation`) is ALWAYS present, and the `<scope>` slug — lowercase, hyphenated; a country (`japan`), a region (`africa`, `southeast-asia`), or a report edition (`giignl2026`) — is present whenever the batch is scoped. Omit `_<scope>` only for a genuinely global batch. Examples: `…_ET_japan_update.xlsx`, `…_ET_asia_discovery.xlsx`, `…_ET_giignl2026_reconciliation.xlsx`. (Pre-convention files used `[_<region>]` without a mode token for update builds; they are not renamed. Triage and QC are memo-only — `batches/triage_<stamp>_ET.md` / `batches/qc_<stamp>_ET.md` — and never produce a workbook.)

**Path caveat — the `../batches/` shorthand in the workflow commands assumes the working directory is `scripts/`.** The canonical target is the tracked `batches/` dir *inside* this repo (it has a `.gitkeep`). If you invoke the build from the repo root (e.g. `python scripts/build_review_package.py …`), use `--output batches/…`, NOT `--output ../batches/…` — the latter resolves to a sibling of the repo and `mkdir(parents=True)` will silently create a stray external dir. **Always confirm the written file is under `<repo-root>/batches/` after building.**

**Never overwrite an existing batch file — every (re)build gets a NEW file with a freshly-generated timestamp.** Regenerate the stamp at build time (don't reuse one captured earlier in the session) and pass it as `--output`. This applies even to small iterative rebuilds within one session (e.g. tweak a color, then add a column → two distinct files). Multiple files per day is the intended behavior; the user prunes old ones.

## Sheets

Empty sheets are omitted from the final workbook.

| Sheet | Populated when | Contents |
|---|---|---|
| `README` | Always | Batch params, color conventions, **per-sheet definitions for every other tab in this workbook**, and input-summary stats (incl. any SOP §6 gate trips). The definitions are sourced from `SHEET_DESCRIPTIONS` in `scripts/build_review_package.py` — required so a researcher can open the file without prior context and know what each tab is for. |
| `updates` | Update workflow | Rows for existing units being updated, with old → new diffs and citations |
| `new_terminals` | Discovery workflow | Newly discovered projects (project-level fields) |
| `new_units` | Discovery or update | Unit-level data for new terminals AND new units within existing terminals (expansions, new trains) |
| `wiki_updates` | Update or discovery | Narrative / Background content that does NOT map to a structured DB column (force majeure, sanctions, disputes, JV/ownership context, linked pipelines/power plants, port status, historical events) — destined for the GEM.wiki Background, kept separate from `updates` so non-column findings aren't lost. `verification_status` color-coded. |
| `status_timeline_additions` | Any workflow touching status | Append-only timeline entries to add to the live DB per methodology |
| `entity_additions` | Any workflow adding owners | New immediate owners/operators/vessel-owners to create, with duplicate-check flags |
| `giignl_diff_operating` | Reconciliation workflow | OPERATING match audit: GEM operating capacity vs GIIGNL's operating-only tables. One project-total row per match; per-unit rows beneath it for unit-granularity matches (GIIGNL row ⊃ GEM unit name, e.g. Arzew GL1Z↔GL1Z) — see `level` column. `gem_unit_name` = operating units only. Conflicting cells red — capacity conflicts graded by size (light red <5% delta, darker red >=5% or undefined); owner-only deltas light red; fuzzy `confidence` yellow (see Color conventions). `insight`/`suggested_resolution` carry the GEM-vs-GIIGNL verdict; for the "GIIGNL counts a construction phase as operating" case (Corpus Christi, issue #6) the verdict is "do NOT bump GEM capacity, verify status only" and the GEM researcher note is quoted + echoed into `analyst_note` (rule f / `_nonop_explains_shortfall`). |
| `giignl_diff_nonoperating` | Reconciliation workflow | Non-operating units (proposed/construction/shelved/cancelled/idled/mothballed/retired) of matched projects. Each defaults to a light-red `gem_only_flag` = "GEM has, GIIGNL doesn't" unless a UNIT-level confirmation (prose correction / table non-op tag) filled `giignl_narrative_mention` (clears the flag). A TERMINAL-level §3.2.1 narrative finding matched by terminal+section (Darwin Barossa restart, NLNG Train 7) ALSO annotates `giignl_narrative_mention` for cross-check but does NOT clear the flag (it doesn't pin the specific unit). A `researcher_notes` column carries the GEM unit's own note (often explains WHY a unit is held non-operating — e.g. Corpus Christi Stage 3: commercial ops not declared), so a gem-only row reads as a deliberate documented decision, not an omission. |
| `giignl_fsru_fleet` | Reconciliation workflow | Cross-check of the GIIGNL FSRU fleet table (`giignl_fsru_fleet.py`) vs GEM floating-vessel records — one row per fleet vessel, matched to a GEM FSRU terminal. Flags GEM terminals missing the "FSRU" naming convention (red), vessel-name deltas (blank/reassignment/naming), and vessel-owner deltas, with a `suggested_action`. Catches fleet-only FSRUs (Tema). |
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
