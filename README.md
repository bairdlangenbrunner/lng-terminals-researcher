# LNG terminals tracker

Operational repository for an LLM research assistant that helps maintain
[GEM's Global Gas Infrastructure Tracker (GGIT) LNG terminals database](https://globalenergymonitor.org/projects/global-gas-infrastructure-tracker/).

This repo is designed to be used with [Claude Code](https://docs.claude.com/en/docs/claude-code).
The assistant produces staged xlsx files for review; it never edits the live
database directly.

## Quick start

1. Install dependencies: `pip install -r requirements.txt`
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

## Repository layout

```
CLAUDE.md                  Entry point for Claude Code — workflow router + hard rules
README.md                  This file
TODO.md                    Open design questions still to decide
requirements.txt           Python deps (openpyxl, pdfplumber, jieba, pypinyin)
.env.example               Template for auth cookies

docs/
  sops/                    The four workflow procedures
    reconciliation.md
    update.md
    discovery.md
    triage.md
  reference/               Lookup tables and rules (read on demand)
    gem_db_schema.md
    lifecycle_rules.md
    unit_conventions.md
    source_roster.md
    entity_canonical_map.md
    sop_pointers.md        Cross-SOP rule index
  country_notes/           One file per country (research notes, regulator URLs)
  design-history/          Original scaffolding conversation transcript

scripts/                   Python tools called by the workflows
  gem_query.py             Query the GEM read-only Postgres DB → CSV
  gem_all_fields.py        Reproduce the website's all-fields LNG CSV (no cookies)
  gem_export_via_web.py    Download all-fields CSV from the live website (cookies)
  pull_gem_db.py           Wrap a data-pull + derive the column-index map
  normalize.py             Country/entity/capacity canonicalization + CJK transliteration
  dedup_index.py           Build matching indexes for candidate dedup
  url_verifier.py          HTTP 200 + content + soft-error check
  capacity_normalize.py    mtpa/bcm/y conversions and range handling
  stale_sweep.py           Flag dormant units per lifecycle thresholds
  status_timeline.py       Validate timeline transitions + anchor years
  fetch_timeline.py        Pull full timeline for a UnitID from web UI
  entity_lookup.py         Check GEM entity system before adding new entities
  imo_tracker.py           Look up vessel IMO via marinetraffic.org
  giignl_extract.py        Parse the GIIGNL annual-report PDF → flat CSV (pdftotext -layout)
  report_diff.py           Reconciliation diff (GIIGNL or IGU vs GEM)
  fsru_sync_check.py       Cross-check FSRUs against carrier project
  build_review_package.py  Assemble the batch xlsx deliverable
  recalc.py                Formula-error check before presenting xlsx

batches/                   Batch outputs (gitignored; .gitkeep retained)
monitor_list/              Cross-batch monitor list (Discovery SOP §5)
```

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

- One branch per batch: `batch/2026-q3-italy-stale-sweep`
- Merge after the batch is applied to the live DB
- Tag each applied batch: `batch-2026-q3-italy-stale-sweep-applied`
- SOPs and reference docs: direct-to-main

## Methodology

This scaffolding follows GEM's GGIT LNG terminals methodology document.
The methodology is authoritative; this repo encodes how the agent applies it
operationally.

## Background

The original design conversation for this scaffolding is in
`docs/design-history/2026-05-scaffolding-conversation.txt` — useful for
understanding why specific decisions were made.
