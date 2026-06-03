# LNG terminals researcher

Operational repository for an LLM research assistant that helps maintain
[GEM's Global Gas Infrastructure Tracker (GGIT) LNG terminals database](https://globalenergymonitor.org/projects/global-gas-infrastructure-tracker/).

This repo is designed to be used with [Claude Code](https://docs.claude.com/en/docs/claude-code).
The assistant produces staged xlsx files for review; it never edits the live
database directly.

## Four workflows

| Workflow | When to use | Output |
|---|---|---|
| **Triage** | "What should we work on this quarter?" | Markdown memo with recommendations |
| **Reconciliation** | A new GIIGNL/IGU annual report is out | xlsx with diff vs current GEM data |
| **Update** | Refresh known terminals (fill blanks, advance status, [ref] backfill) | xlsx with staged updates |
| **Discovery** | Find terminals that aren't yet in GEM | xlsx with new terminal/unit candidates |

See `CLAUDE.md` for the routing logic and `docs/sops/` for the full procedures.

## Repository layout

In plain terms: **docs tell the assistant *how* to work, scripts do the mechanical work, data holds the input reports, and batches holds the output.**

```
CLAUDE.md                    Entry point for Claude Code — what the project is, workflow router, hard rules
README.md                    This file
TODO.md                      Open design questions and ideas not yet decided
requirements.txt             Python deps (pip install -r); the PDF reader also needs poppler's pdftotext
                             (brew install poppler / apt-get install poppler-utils — not pip-installable)
.env.example                 Template for .env (GEM login cookies — only the web-export fallback needs them)
.gitignore                   Keeps data pulls, scratch outputs, and xlsx workbooks out of git
giignl_2026_triage_memo.md   Planning memo from triaging the 2026 GIIGNL report

.claude/                     Claude Code settings (tool permissions); its README explains the choices

data/                        GIIGNL annual report PDFs 2020–2026 — the reconciliation input
  README.md                  Describes each edition (page counts, table locations, edition→year map)

docs/
  workflows.md               Step-by-step command recipes for every workflow
  sops/                      The four procedures
    reconciliation.md        Compare GEM to a new GIIGNL report
    update.md                Refresh existing terminals (fill blanks, advance status, [ref] backfill)
    discovery.md             Find terminals missing from GEM
    triage.md                Decide what to work on
  reference/                 Lookup tables and rules (read on demand)
    gem_db_schema.md         What every GEM database column means
    lifecycle_rules.md       Status rules — when a project counts as proposed/shelved/cancelled etc.
    unit_conventions.md      How units/trains are named and how capacity numbers are written
    source_roster.md         Where to look for information, by country and source type
    entity_canonical_map.md  Correct spellings of company names GEM already uses
    workbook_conventions.md  What each sheet and cell color in the output xlsx means
    sop_pointers.md          Quick index of which rule lives in which document
  country_notes/             One research-notes file per country (regulators, quirks, key sources)
  design-history/            Original design conversation transcript — why things are the way they are

scripts/                     Python tools called by the workflows
  README.md                  The index: per-script purpose, run order, deep-dives on the tricky ones
  gem_all_fields.py          Download the full LNG dataset from GEM (no login) — the usual way
  gem_export_via_web.py      Same download via the website with login cookies — the fallback
  gem_query.py               Ask the GEM read-only database direct questions
  pull_gem_db.py             Wrap a download + write the column-index map (.colmap.json)
  fetch_timeline.py          Pull a unit's full status history (the CSV export only has current status)
  giignl_extract.py          Turn the GIIGNL PDF's terminal tables into a flat CSV
  giignl_fsru_fleet.py       Extract the report's FSRU fleet table (which floating vessel is where)
  report_diff.py             Compare extracted GIIGNL data against GEM — list every disagreement
  fsru_sync_check.py         Check FSRU vessel names/IMOs agree with the LNG carrier project
  stale_sweep.py             Flag entries that haven't moved in too long
  completeness_sweep.py      Find blank fields, missing [ref]s, and countries with no coverage
  dedup_index.py             Name-matching indexes so "new" candidates can be checked against existing entries
  entity_lookup.py           Check whether a company already exists in GEM's shared entity system
  url_verifier.py            Verify a URL works and shows the claimed content — required for every ref
  imo_tracker.py             Look up a vessel's IMO number
  status_timeline.py         Validate that a status change follows the allowed transitions
  normalize.py               Standardize country/company/terminal names (incl. Chinese transliteration)
  capacity_normalize.py      Convert capacity units (mtpa, bcm/y, …) to one standard
  country_universe.py        Reference list of coastal countries (used to spot coverage gaps)
  build_review_package.py    Assemble everything into the final review xlsx
  recalc.py                  Sanity-check the xlsx for formula errors before it's presented

batches/                     Finished review workbooks (*.xlsx, gitignored — regenerable)
  staging/                   TRACKED: per-country sweep research (the audit trail), the sweep ledger
                             (SWEEP_PROGRESS.md), subagent briefs, and _assemble.py which merges it all

work/                        Scratch — derived sweep/index outputs, regenerable (gitignored)
monitor_list/                current.json: discovery candidates not yet solid enough to add, re-checked each batch
```

A batch in progress also drops untracked working files at the repo root — `gem_export.csv` + `.colmap.json` (the fresh data pull), `giignl_extracted.csv` / `giignl_diff.json` / `giignl_fsru_fleet.json` (report extraction and diff), and `staged_*.json` plus the prose/narrative findings JSONs (the agent's staged research). All regenerable or batch-scoped, so they stay out of git.

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
