# LNG terminals researcher

Operational repository for an LLM research assistant that helps maintain
[GEM's Global Gas Infrastructure Tracker (GGIT) LNG terminals database](https://globalenergymonitor.org/projects/global-gas-infrastructure-tracker/).

This repo is designed to be used with [Claude Code](https://docs.claude.com/en/docs/claude-code).
The assistant produces staged xlsx files for review; it never edits the live
database directly.

## Quick start

1. Install dependencies: `pip install -r requirements.txt`
   - Plus the **`pdftotext` CLI from poppler** (a system dependency the GIIGNL extractor shells out to — not pip-installable): `brew install poppler` (macOS) / `apt-get install poppler-utils` (Debian/Ubuntu)
2. Copy `.env.example` to `.env` and fill in GEM auth cookies (only needed for the cookie-based web export; `gem_all_fields.py` needs no cookies)
3. Open the repo in Claude Code: `claude .`
4. Claude reads `CLAUDE.md` automatically and routes from there

## Four workflows

| Workflow | When to use | Output |
|---|---|---|
| **Triage** | "What should we work on this quarter?" | Markdown memo with recommendations |
| **Reconciliation** | A new GIIGNL/IGU annual report is out | xlsx with diff vs current GEM data |
| **Update** | Refresh known terminals (fill blanks, advance status, [ref] backfill) | xlsx with staged updates |
| **Discovery** | Find terminals that aren't yet in GEM | xlsx with new terminal/unit candidates |

See `CLAUDE.md` for the routing logic and `docs/sops/` for the full procedures.

## Repository layout — what each file and folder does

In plain terms: **docs tell the assistant *how* to work, scripts do the mechanical work, data holds the input reports, and batches holds the output.**

### Top-level files

| File | What it does |
|---|---|
| `CLAUDE.md` | The first thing Claude Code reads in every session. Says what this project is, which workflow to run for a given request, and the hard rules it must never break. |
| `README.md` | This file. |
| `TODO.md` | A running list of open design questions and ideas not yet decided. |
| `requirements.txt` | The Python packages to install. (The PDF reader also needs poppler's `pdftotext`, installed separately — see Quick start.) |
| `.env.example` | A template for `.env`, which holds GEM login cookies. Only needed for the cookie-based export fallback. |
| `.gitignore` | Tells git which files *not* to track: data pulls, scratch outputs, the xlsx workbooks. |
| `giignl_2026_triage_memo.md` | A planning memo from triaging the 2026 GIIGNL report — what looked worth working on. |

### `.claude/` — Claude Code settings

Project-level settings for the assistant, mainly which tools it may use without prompting. Its own `README.md` explains the choices.

### `data/` — the GIIGNL report archive

Every GIIGNL annual report PDF from 2020 to 2026 — the input for the reconciliation workflow. `data/README.md` describes each edition (page counts, where the tables live, which calendar year an edition covers).

### `docs/` — instructions the assistant reads on demand

| Path | What it does |
|---|---|
| `docs/workflows.md` | Step-by-step command recipes for every workflow — which script to run when, in what order. |
| `docs/sops/` | The four procedure documents: `reconciliation.md` (compare GEM to a new GIIGNL report), `update.md` (refresh existing terminals), `discovery.md` (find terminals missing from GEM), `triage.md` (decide what to work on). |
| `docs/reference/gem_db_schema.md` | What every column in the GEM database means. |
| `docs/reference/lifecycle_rules.md` | Status rules — when a project counts as proposed, shelved, cancelled, etc. |
| `docs/reference/unit_conventions.md` | How units/trains/phases are named and how capacity numbers are written. |
| `docs/reference/source_roster.md` | Where to look for information, by country and source type. |
| `docs/reference/entity_canonical_map.md` | The correct spellings of company names GEM already uses. |
| `docs/reference/workbook_conventions.md` | What each sheet and cell color in the output xlsx means. |
| `docs/reference/sop_pointers.md` | A quick index of which rule lives in which document. |
| `docs/country_notes/` | One research-notes file per country (regulators, quirks, key sources). |
| `docs/design-history/` | The transcript of the original design conversation — why things are the way they are. |

### `scripts/` — the Python tools

`scripts/README.md` is the index: what each script does, the usual run order, and deep-dives on the tricky ones. In one line each:

**Getting GEM data:**

| Script | What it does |
|---|---|
| `gem_all_fields.py` | Downloads the full LNG terminals dataset from GEM (no login needed). The usual way. |
| `gem_export_via_web.py` | Same download via the website with login cookies. The fallback. |
| `gem_query.py` | Asks the GEM read-only database direct questions. |
| `pull_gem_db.py` | Wraps a download and writes the column-index map (`.colmap.json`) so scripts know which column is which. |
| `fetch_timeline.py` | Pulls a unit's full status history (the CSV export only has the current status). |

**Reading the GIIGNL report:**

| Script | What it does |
|---|---|
| `giignl_extract.py` | Turns the GIIGNL PDF's terminal tables into a flat CSV. |
| `giignl_fsru_fleet.py` | Extracts the report's FSRU fleet table (which floating vessel is where). |

**Comparing and checking:**

| Script | What it does |
|---|---|
| `report_diff.py` | Compares the extracted GIIGNL data against GEM and lists every disagreement. |
| `fsru_sync_check.py` | Checks FSRU vessel names/IMOs agree with the LNG carrier project. |
| `stale_sweep.py` | Flags entries that haven't moved in too long. |
| `completeness_sweep.py` | Finds blank fields, missing `[ref]`s, and countries with no coverage. |
| `dedup_index.py` | Builds name-matching indexes so a "new" candidate can be checked against existing entries. |
| `entity_lookup.py` | Checks whether a company already exists in GEM's shared entity system. |
| `url_verifier.py` | Verifies a URL actually works and shows the claimed content — required before any URL goes in the xlsx. |
| `imo_tracker.py` | Looks up a vessel's IMO number. |
| `status_timeline.py` | Validates that a proposed status change follows the allowed transitions. |

**Cleaning data:**

| Script | What it does |
|---|---|
| `normalize.py` | Standardizes country, company, and terminal names (including Chinese transliteration). |
| `capacity_normalize.py` | Converts capacity units (mtpa, bcm/y, …) to one standard. |
| `country_universe.py` | The reference list of coastal countries (used to spot coverage gaps). |

**Building the deliverable:**

| Script | What it does |
|---|---|
| `build_review_package.py` | Assembles everything into the final review xlsx. |
| `recalc.py` | Sanity-checks the xlsx for formula errors before it's presented. |

### `batches/` — the output

Finished review workbooks (`.xlsx`) land here; they're regenerable so git ignores them. `batches/staging/` *is* tracked: the per-country research files from regional sweeps (the audit trail), plus the sweep ledger (`SWEEP_PROGRESS.md`), the briefs given to per-country subagents, and `_assemble.py` which merges it all for the workbook build.

### `work/` — scratch

Derived sweep/index outputs scripts regenerate on demand. Git ignores everything but the folder itself.

### `monitor_list/` — the watch list

`current.json`: discovery candidates that aren't solid enough to add yet, carried between batches so they get re-checked.

### Files that appear during a batch (untracked)

A batch in progress drops working files at the repo root — `gem_export.csv` and its `.colmap.json` (the fresh data pull), `giignl_extracted.csv` / `giignl_diff.json` / `giignl_fsru_fleet.json` (report extraction and diff), and `staged_*.json` plus the prose/narrative findings JSONs (the agent's staged research). All are regenerable or batch-scoped scratch, so they stay out of git.

## Hard rules

A non-exhaustive list of things the agent should never do (full list in `CLAUDE.md`):

- Never edit the live GEM database. All outputs are staging xlsx.
- Pull a fresh GEM CSV at the start of every batch — schema and data drift.
- Verify every URL before staging it as a [ref]. HTTP 200 alone isn't enough; check for soft-error pages and content references.
- Never fill a `[ref]` column without paired data — and vice versa (Rule F).
- Run `entity_lookup.py` before staging any new entity. The GEM entity system is shared across trackers.
- Status timeline edits require pulling the full timeline first (`fetch_timeline.py`). The CSV export doesn't include it.
- Out-of-scope fields (LH2, NH3, SyntheticLNG, PCI, AltFuel*) are read-only.

## Branching and batches

- **Targeted batch** (one country, a stale-sweep, a reconciliation): one branch per batch, e.g. `batch/2026-q3-italy-stale-sweep`; merge after the batch is applied to the live DB; optionally tag `batch-...-applied`.
- **Regional / full-tracker sweep**: a single long-lived branch carries the whole multi-region pass, with the `batches/staging/` tree committed as the diffable audit trail (see the "Regional sweep" section in `CLAUDE.md`).
- SOPs and reference docs: direct-to-main.

## Methodology

This scaffolding follows GEM's GGIT LNG terminals methodology document.
The methodology is authoritative; this repo encodes how the agent applies it
operationally.

## Background

The original design conversation for this scaffolding is in
`docs/design-history/2026-05-scaffolding-conversation.txt` — useful for
understanding why specific decisions were made.
