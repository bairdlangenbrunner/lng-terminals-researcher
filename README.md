# LNG terminals researcher

Operational repository for an LLM research assistant that helps maintain
[GEM's Global Gas Infrastructure Tracker (GGIT) LNG terminals database](https://globalenergymonitor.org/projects/global-gas-infrastructure-tracker/).

This repo is designed to be used with [Claude Code](https://docs.claude.com/en/docs/claude-code).
The assistant produces staged xlsx files for review; it never edits the live
database directly.

## Eight workflows

| Workflow | When to use | Output |
|---|---|---|
| **Triage** | "What should we work on this quarter?" | Markdown memo with recommendations |
| **Reconciliation** | A new GIIGNL/IGU annual report is out | xlsx with diff vs current GEM data |
| **Update** | Refresh known terminals — **standard** tier (worklist: stale + pipeline + blank refs) or **exhaustive** tier (every field, every ref) | xlsx with staged updates |
| **Discovery** | Find terminals that aren't yet in GEM | xlsx with new terminal/unit candidates |
| **Regional sweep** | Scaled Update/Discovery across a whole region — one subagent per country, resumable ledger | One xlsx per region + committed staging tree |
| **QC** | Audit data health — link-rot, accuracy spot-check, did-my-edits-land | Markdown memo; fixes route to an Update batch |
| **Missing-year ref-sweep** | Status-timeline milestones with no year — backfill from research | xlsx worklist kept in `batches/deliverables/` |
| **Captive-power cross-tracker** | Match LNG terminals to GOGPT captive gas power plants | LNG staging xlsx (`CaptiveGasPower`/`PowerPlantsSupplied`) + memo for GOGPT-side gaps |

See `CLAUDE.md` for the routing logic and `docs/sops/` for the full procedures.

## Setup

```bash
pip install -r requirements.txt
brew install poppler        # or: apt-get install poppler-utils
```

`poppler` provides `pdftotext`, which the GIIGNL PDF extraction needs — it is not
pip-installable.

**Environment variables** (put them in `.env`, gitignored; `.env.example` is the
template). None are needed to read the repo or build a workbook from committed
staging — they gate the live-data scripts:

| Variable | Needed by | What it is |
|---|---|---|
| `GEM_READONLY_DB_URL` | `../gem-db-ops/gem_query.py` (the canonical data pull, in the sibling repo), `refsweep_missing_year.py`, `fetch_timeline.py`, `captive_power_colocation.py` | Postgres connection string for GEM's read-only replica (`postgres://readonly:…@host:5432/db`). Ask GEM staff. |
| `GEM_PROJECT_DB_SESSIONID`, `GEM_PROJECT_DB_CSRFTOKEN` | `fetch_timeline.py`, `entity_lookup.py --remote` | Login cookies from a browser session on the GEM project DB (copy `sessionid`/`csrftoken` from DevTools; re-copy when they expire). |
| `GEM_PROJECT_DB_BASE_URL` | `fetch_timeline.py` | Overrides the built-in project-DB host. Required for `fetch_timeline.py` — see Known issues. |

**Access prerequisite:** the GEM LNG Terminals Manual (a Google Doc) is the
authoritative methodology and is NOT in this repo. Ask your GEM lead for access;
the reference URL lives in `docs/reference/sop_pointers.md`.

## Getting started

1. Read `CLAUDE.md` — the workflow router and hard rules; it is the assistant's
   entry point and the fastest orientation for a human too.
2. Skim `batches/run_records/README.md` — the dated log of what was last done.
3. Run a **Triage** batch first (`docs/workflows.md` §4). It is memo-only —
   lowest-risk way to exercise the pipeline end to end.

Smoke-check the setup (from `scripts/`, needs `GEM_READONLY_DB_URL`):

```bash
python ../../gem-db-ops/gem_query.py --all-fields lng -o gem_export.csv   # fresh pull (engine lives in the sibling gem-db-ops repo)
python pull_gem_db.py --map-only                         # derive the column-index map (.colmap.json)
python dedup_index.py                                    # build the name-match indexes
```

All three succeeding means the data pull, schema map, and matching indexes work.

## Repository layout

In plain terms: **docs tell the assistant *how* to work, scripts do the mechanical work, data holds the input reports, and batches holds the output.**

```
CLAUDE.md                    Entry point for Claude Code — what the project is, workflow router, hard rules
README.md                    This file
TODO.md                      Open design questions and ideas not yet decided
requirements.txt             Python deps (pip install -r); the PDF reader also needs poppler's pdftotext
                             (brew install poppler / apt-get install poppler-utils — not pip-installable)
.env.example                 Template for .env (see Setup — env vars for the live-data scripts)
.gitignore                   Keeps data pulls, scratch outputs, and xlsx workbooks out of git

.claude/                     Claude Code settings (tool permissions); its README explains the choices

data/                        GIIGNL annual report PDFs 2020–2026 — the reconciliation input
  README.md                  Describes each edition (page counts, table locations, edition→year map)

docs/
  workflows.md               Step-by-step command recipes for every workflow
  sops/                      The procedures
    reconciliation.md        Compare GEM to a new GIIGNL report
    update.md                Refresh existing terminals (standard or exhaustive tier; fill blanks, advance status, [ref] backfill)
    discovery.md             Find terminals missing from GEM
    triage.md                Decide what to work on
    qc.md                    Audit data health (link-rot, accuracy, post-apply checks); fixes route to Update
    ref_sweep.md             Backfill missing years on status-timeline milestones
    captive_power.md         Match LNG terminals to GOGPT captive gas power plants (LNG-side staging only)
  reference/                 Lookup tables and rules (read on demand)
    gem_db_schema.md         What every GEM database column means
    lifecycle_rules.md       Status rules — when a project counts as proposed/shelved/cancelled etc.
    unit_conventions.md      How units/trains are named and how capacity numbers are written
    source_roster.md         Where to look for information, by country and source type
    entity_canonical_map.md  Correct spellings of company names GEM already uses
    workbook_conventions.md  What each sheet and cell color in the output xlsx means
    sop_pointers.md          Quick index of which rule lives in which document
  country_notes/             One research-notes file per country (regulators, quirks, key sources)
  design_history/            Original design conversation transcript — why things are the way they are

scripts/                     Python tools called by the workflows
  README.md                  The index: per-script purpose, run order, deep-dives on the tricky ones
  pull_gem_db.py             Write the column-index map (.colmap.json); the pull ENGINE lives in ../gem-db-ops (sibling repo)
  add_effective_status.py    Stamp effective_status onto the export + prune old CSV snapshots
  fetch_timeline.py          Pull a unit's full status history (the CSV export only has current status)
  giignl_extract.py          Turn the GIIGNL PDF's terminal tables into a flat CSV
  giignl_fsru_fleet.py       Extract the report's FSRU fleet table (which floating vessel is where)
  report_diff.py             Compare extracted GIIGNL data against GEM — list every disagreement
  fsru_sync_check.py         Check FSRU vessel names/IMOs agree with the LNG carrier project
  stale_sweep.py             Flag entries that haven't moved in too long; also lists the development
                             pipeline (every proposed/construction/shelved unit) for standard updates
  completeness_sweep.py      Find blank fields, missing [ref]s, and countries with no coverage
  sweep_worklist_split.py    Split the central worklists per country for a regional sweep (one
                             dispatch file per country; LNG-only)
  refsweep_missing_year.py   Missing-year ref-sweep: extract no-year milestones from the read-only
                             Postgres, build the research workbook
  captive_power_colocation.py  Match LNG terminals to GOGPT captive gas power plants (geo + name +
                             captive flags) from the read-only Postgres; emits tiered candidate pairs
  citation_qc.py             Re-verify every existing [ref] URL in scope (QC link-rot sweep)
  apply_check.py             Confirm an applied batch's edits actually landed in the live DB (QC)
  dedup_index.py             Name-matching indexes so "new" candidates can be checked against existing entries
  entity_lookup.py           Check whether a company already exists in GEM's shared entity system
  url_verifier.py            Verify a URL works and shows the claimed content — required for every ref
  imo_tracker.py             Look up a vessel's IMO number
  status_timeline.py         Validate that a status change follows the allowed transitions
  normalize.py               Standardize country/company/terminal names (incl. Chinese transliteration)
  capacity_normalize.py      Convert capacity units (mtpa, bcm/y, …) to one standard
  country_universe.py        Reference list of coastal countries (used to spot coverage gaps)
  monitor_store.py           Read/write monitor_list/current.json (watchlist candidates)
  build_review_package.py    Assemble everything into the final review xlsx
  recalc.py                  Sanity-check the xlsx for formula errors before it's presented

batches/                     Everything a batch produces; see batches/README.md for the tracked/ignored split
  README.md                  One-screen map of this tree
  staging/                   TRACKED: ALL per-batch staging inputs (the audit trail) — per-country sweep
                             research in <region>/, per-edition reconciliation staging in recon/<edition>/,
                             ad-hoc batches in <scope>/, plus the sweep ledger stub (SWEEP_PROGRESS.md),
                             subagent briefs, and _assemble.py which merges sweep output. Derived files
                             there (extracted CSV, diff, _build assemblies) are gitignored; see its README
  run_records/               TRACKED: one dated md per major run (trigger → work → outcome) + index README
  deliverables/              TRACKED (xlsx included): workbooks kept long-term because the exact artifact matters
  old/                       Superseded workbooks parked for pruning (gitignored)
                             Routine workbooks land at this tree's top level as
                             lng_terminals_batch_<stamp>_ET[_<scope>]_<mode>.xlsx (gitignored — regenerable)

work/                        Scratch — derived sweep/index/QC outputs, regenerable (gitignored)
monitor_list/                current.json: discovery candidates not yet solid enough to add, re-checked each batch
notes/                       Ad-hoc analysis memos that aren't run records (rare)
```

A batch in progress also drops the untracked fresh data pull (`gem_export.csv` + `.colmap.json`) wherever it was pulled (repo root or `scripts/`). Everything else batch-scoped — extracted report CSVs, diffs, `staged_*.json`, prose/narrative findings — lives under `batches/staging/` per its README, never loose in the repo root.

## Known issues

- **`fetch_timeline.py`'s default host is stale.** The built-in Heroku URL
  404s; set `GEM_PROJECT_DB_BASE_URL` to the live project-DB host. Until it is
  reachable, route status changes to qa notes rather than staging blind
  timeline edits. (Timeline *reads/audits* have an alternative path: the
  read-only Postgres `status_timeline` table via `GEM_READONLY_DB_URL`.)

## Hard rules

A non-exhaustive list of things the agent should never do (full list in `CLAUDE.md`):

- Never edit the live GEM database. All outputs are staging xlsx.
- Pull a fresh GEM CSV at the start of every batch — schema and data drift.
- Verify every URL before staging it as a [ref]. HTTP 200 alone isn't enough; check for soft-error pages and content references.
- Never fill a `[ref]` column without paired data — and vice versa (Rule F).
- Run `entity_lookup.py` before staging any new entity. The GEM entity system is shared across trackers.
- Status timeline edits require pulling the full timeline first (`fetch_timeline.py`). The CSV export doesn't include it.
- Out-of-scope fields (LH2, NH3, SyntheticLNG, PCI, AltFuel*) are read-only.

## Running tests

```bash
pytest tests/
```

Covers the unit/capacity normalizers, the GIIGNL owner-parser edge cases, the
workbook build guard, and a snapshot extraction of the committed 2026 GIIGNL PDF
(skipped if `pdftotext` is absent). See `tests/README.md`.

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
`docs/design_history/2026-05-scaffolding-conversation.txt` — useful for
understanding why specific decisions were made.
