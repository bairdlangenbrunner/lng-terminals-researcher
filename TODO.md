# TODO — Open design questions

Decisions surfaced during scaffolding but deferred. Resolve before or during
first real batches. Format: each item is decision-oriented; pick a direction
and edit the doc rather than leaving as a TODO indefinitely.

---

## OPEN: Wiki page editing as part of the agent workflow

Currently omitted from the Update SOP. The methodology specifies that
researchers manually edit the Background section of each terminal's wiki page,
and several scaffolding pieces (capacity ranges, cost ranges) generate
"add this to wiki Background" notes that have no current target.

**Options:**
- (A) Add a `wiki_background_additions` sheet to the batch xlsx; user manually
  transfers to wiki.
- (B) Have the agent stage actual wiki page edits in a `wiki_edits/` directory
  as markdown files, named by `TerminalName_underscored.md`.
- (C) Leave it manual outside the agent workflow entirely.

**Recommendation:** (A) is lowest-effort, (B) is most useful if you'll edit
many wikis per batch.

---

## OPEN: AltFuelNotes field

`AltFuelNotes` does not appear in the all-fields CSV export but may exist
in the live DB edit UI. Need to:

1. Confirm presence in the live UI
2. Decide whether to add it to EXPECTED_COLUMNS in `scripts/pull_gem_db.py`
3. Decide if it's in-scope (probably yes — it's notes, not values)

**Action:** check on the next live-DB visit.

---

## OPEN: Batch output directory naming convention

Triage SOP §3.3 assumes prior batch xlsx is findable for reconciliation
backlog scanning. The repo has `batches/` but no enforced naming convention.

**Options:**
- (A) Free-form filenames; triage prompts user "where's the last reconciliation batch?"
- (B) Convention: `batches/<YYYY-MM-DD>_<workflow>_<scope>.xlsx`
  e.g. `batches/2026-07-15_reconciliation_giignl-2026.xlsx`
- (C) Convention with subdirs by workflow: `batches/reconciliation/2026-07-15_giignl.xlsx`

**Recommendation:** (B). Simple, sortable, greppable.

---

## OPEN: Activity scan in triage — programmatic or LLM-shaped?

Triage SOP §3.2 calls for a "lightweight 90-day activity scan" to identify
countries/sponsors with notable recent activity. Currently described as
LLM-shaped (read recent headlines, summarize).

**Programmatic option:** RSS feed pulls from LNG Prime, Reuters Energy,
major sponsor IR pages. Deterministic and repeatable but limited to
configured feeds.

**LLM-shaped option:** Claude reads recent headlines via web search, summarizes
notable items. Catches surprise developments but variable between runs.

**Recommendation:** start LLM-shaped to learn what patterns emerge, formalize
into programmatic feeds as warranted.

---

## OPEN: "GEM-only = usually expected" default in reconciliation

Reconciliation SOP §4 treats GEM-only matches (operating terminals in GEM
not listed in GIIGNL) as "usually expected" because GEM tracks more than
GIIGNL does. The `giignl_to_action` sheet still flags them, but with a
soft "investigate" framing.

**Concern:** this default could let real GEM errors slip through when GIIGNL
genuinely should have included a terminal and didn't.

**Options:**
- (A) Keep current: soft flag, user investigates
- (B) Hard flag every GEM-only operating row; force review
- (C) Threshold-based: GEM-only with capacity >X mtpa gets hard flag

**Recommendation:** (A) until first reconciliation reveals failure modes.

---

## OPEN: Per-row URL citation for GIIGNL rows

Reconciliation SOP uses a `report_citation` column instead of URL for GIIGNL
sourced data (since GIIGNL is a PDF, not a URL). Build script (`build_review_package.py`)
needs explicit support for this column in the giignl_diff sheet — currently
it's not in the schema.

**Action:** add `report_citation` column to giignl_diff sheet and update
build script. Format suggestion: `"GIIGNL 2026, page 34, table 2"`.

May also need clarification from GEM on whether `report_citation` values
should be entered into `Source [ref]` or a different column in the live DB.

---

## OPEN: Project-level matching for GIIGNL diff

`report_diff.py` does project-level matching (collapses GEM unit-rows to
projects before diffing). This means unit-level capacity disagreements get
reported at the project total, potentially masking individual-train differences.

**Tradeoff:** GIIGNL also reports project-level totals in most tables, so
unit-level matching would force GIIGNL data to be split arbitrarily.

**Options:**
- (A) Keep project-level matching, flag total disagreements
- (B) Switch to unit-level where GIIGNL provides train-level breakdowns
- (C) Hybrid: project-level for match, unit-level diff displayed in supplemental sheet

**Recommendation:** (A) for first reconciliation, (C) if (A) misses important
disagreements.
