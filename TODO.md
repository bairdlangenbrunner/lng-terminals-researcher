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

## RESOLVED: Batch output directory naming convention

Decided 2026-05-27: `batches/lng_terminals_batch_<YYYYMMDD>_<HHMM>_ET.xlsx`. Eastern-time HHMM disambiguates multiple batches the same day (e.g. AM dry-run + PM full run). Generate via `TZ=America/New_York date "+%Y%m%d_%H%M_ET"`. Documented in CLAUDE.md and Reconciliation SOP §3.10.

---

## OPEN: GIIGNL narrative prose extraction — helper script or stay agent-driven?

Decided 2026-05-28: narrative prose parsing is now a real reconciliation step
(Reconciliation SOP §3.2.1) — the operating-only tables miss the proposed/
construction/expansion activity GIIGNL discloses in the country narratives
(Yuedong/PipeChina is the canonical example). The step is **agent-driven today**:
the agent reads the narrative pages and produces structured Discovery/Update
candidates.

**Open question:** whether to build a helper to focus that read.
- (A) Stay fully agent-driven — agent reads the narrative page ranges directly.
  Simplest; no new code. Risk: long narratives, easy to miss a paragraph.
- (B) `giignl_prose_extract.py` (or extend `giignl_extract.py`) to pre-filter
  narrative paragraphs containing capacity/date/lifecycle keywords, so the agent
  reviews a focused shortlist. Deterministic pre-filter, agent still judges.
- (C) Full structured prose extraction (regex/LLM) emitting candidate rows
  directly into `giignl_to_action`. Most automation; highest build + maintenance.

**Recommendation:** (A) for the first edition that uses the step, then (B) once
we see which paragraphs get missed. Mirrors the triage activity-scan tradeoff
below. This is the same "programmatic vs LLM-shaped" decision.

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

---

## RESOLVED: `report_diff.py` fuzzy matching is nondeterministic

Resolved 2026-05-28: the three set iterations that drove the jitter
(`matched_report_keys`, `giignl_only_keys`, `gem_only_keys`) are now wrapped in
`sorted()` in `_classify`. The critical one was the `giignl_only_keys` loop,
which `discard()`s from `gem_only_keys` as it assigns fuzzy matches, so when
several report rows contend for the same GEM candidate (Qatar's QatarEnergy LNG
train rows vs the (N)/(S) GEM records) the winner depended on set-iteration
order. Verified reproducible: two consecutive runs on the 2026 data now produce
byte-identical `giignl_diff.json`. No semantic change — only ordering.

Cause (for the record): the fuzzy pass iterated Python `set`s, and string hash
randomization (PYTHONHASHSEED) shuffled tie-breaking among borderline candidates.
Exact + alias matches were always stable; only the fuzzy/gem-only boundary moved.

---

## OPEN: GIIGNL 2026 extraction + matcher defects (found 2026-05-28, not yet fixed)

Investigation of the 2026 reconciliation diff (before building the package) found
the §6 gates tripped largely by **noise, not real findings**. Two root causes,
both deferred (user chose to build the package as-is first):

**A. `giignl_extract.py` block-boundary / artifact bugs** — inflate the
GIIGNL-only ("report_only", ~100) list with rows that aren't real discoveries:
- **Country leaks at block boundaries:** "Das Island" (UAE) tagged Qatar;
  "Guantang" (Taiwan / CPC) tagged Korea; "Zeebrugge Expansion Krk" merges
  Belgium + Croatia on one row. The §3.2 sequential country-walk / subtotal-budget
  logic mis-routes some rows.
- **Page footer leaked as a data row:** country `"4 - GIIGNL Annual Report 2026
  Edition"`, site `"Dabhol Expansion nual Report 2026 Edition"` — running
  header/footer not stripped before row partitioning.
- **Orphaned site names:** a China row whose site is literally `"expansion"`
  (the real name landed on a prior physical line and got split off).
- **Owner-token doubling:** "PipeChina PipeChina 60%", "Fluxys LNG LNG Hrvatska".

**B. `report_diff.py` matcher misses on romanization/hyphenation** — major
terminals that ARE in GEM get classified GIIGNL-only because the fuzzy pass
doesn't normalize hyphens/romanization: Pyeong-Taek, Tong-Yeong, Samcheok
(KOGAS), Higashi-Ohgishima, Himeji (JERA), etc. Real GIIGNL-only count is well
below the raw 100 once these are matched.

**Also observed (benign, no action):** ~85 of 88 value-disagreements are
owner-set deltas (GIIGNL full JV vs GEM immediate owner, per §3.6); only ~14–17
are real capacity deltas >10%. The §6 disagreement gate trips on the raw 50%,
but the substantive signal is just the capacity reds.

**Suggested fix order (per the 2026-05-28 conversation):** (1) extractor
header/footer + country-boundary fixes → shrinks false GIIGNL-only; (2) matcher
hyphen/romanization normalization → shrinks it further and reveals the true
GIIGNL-only count; (3) re-run diff, decide owner-only routing (likely log-only,
not ~85 Update rows), then rebuild the package.

**Partial progress 2026-05-28 (matcher, expansion rows):** added report-side
folding of "<Site> Expansion"/"Extension" rows into the base "<Site>" project so
GIIGNL's split phased terminals sum correctly (fixed Taichung's spurious 23.8%
capacity disagreement — `Taichung` 6.1 + `Taichung Expansion` 1.9 = GEM's 8.0).
Also folded: Cartagena SPEC LNG, Yangshan Shanghai, South Hook LNG. Note the
post-fold Yangshan (12 vs GEM 6) and South Hook (19.5 vs GEM 15.6) now surface as
real fuzzy-match capacity gaps — investigate whether GEM is missing the expansion
units or GIIGNL double-counts. The extractor artifacts under root cause A above
are deliberately NOT folded (the fold requires a resolvable base partner), so
"Zeebrugge Expansion Krk", the bare "expansion" China row, and the "Dabhol
Expansion nual Report 2026 Edition" footer-leak still need the extractor fixes
in (1).
