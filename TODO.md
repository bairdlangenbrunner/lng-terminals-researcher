# TODO — Open design questions

Decisions surfaced during scaffolding but deferred. Resolve before or during
first real batches. Format: each item is decision-oriented; pick a direction
and edit the doc rather than leaving as a TODO indefinitely.

Resolved items are collapsed to one-liners (full history in git); open items
keep their options.

---

## Resolved (one-liners; details in git history)

- **Wiki page editing** (2026-06): option (A) — `wiki_updates` sheet in
  `build_review_package.py` collects narrative content; user pastes into the
  wiki manually.
- **Batch output naming** (2026-05-27, extended 2026-06-03):
  `batches/lng_terminals_batch_<YYYYMMDD>_<HHMM>_ET[_<scope>]_<mode>.xlsx`,
  stamp via `TZ=America/New_York`; see `docs/reference/workbook_conventions.md`.
- **Per-row GIIGNL citation** (2026-06, rev 8): superseded — the raw-diff sheet
  carries a `report_page` column for PDF cross-checks, `edits_to_gem`'s
  `_change` column states sources, and the SOP rules GIIGNL is cited by
  edition/table in prose, never as a `[ref]` URL (Reconciliation SOP, URL
  rules; `[ref]` columns hold independently verified URLs only).
- **Project-level matching for the GIIGNL diff** (2026-06): option (C) —
  `report_diff.py` aligns at unit level (`_align_units`, train-range pre-pass,
  `_unit_designators`) with project-total fallback; see the deep-dive in
  `scripts/README.md`.
- **`report_diff.py` fuzzy-match nondeterminism** (2026-05-28): fixed —
  the three driving set iterations are `sorted()`; consecutive runs are
  byte-identical.
- **GIIGNL 2026 extraction + matcher defects** (2026-06, mostly): country
  leaks, footer-as-row, orphaned names, romanization/hyphenation misses all
  fixed (see the `giignl_extract.py` / `report_diff.py` deep-dives). RESIDUAL:
  dense-block owner-cell bleed surfaces as occasional lone-token owner deltas —
  tracked in the `_attribute_owner_fragments` deep-dive, not here.
- **Qatar Ras Laffan project-level match** (2026-06): `_unit_designators`
  maps GIIGNL `N(*)`/`S(*)` codes to the GEM unit with the same code; the
  train-range pre-pass sums per-train rows into GEM range-units.

---

## OPEN: AltFuelNotes field

`AltFuelNotes` does not appear in the all-fields CSV export but may exist
in the live DB edit UI. Need to:

1. Confirm presence in the live UI
2. Decide whether to add it to EXPECTED_COLUMNS in `scripts/pull_gem_db.py`
3. Decide if it's in-scope (probably yes — it's notes, not values)

**Action:** check on the next live-DB visit.

---

## OPEN: GIIGNL narrative prose extraction — helper script or stay agent-driven?

Narrative prose parsing is a real reconciliation step (Reconciliation SOP
§3.2.1), agent-driven today: the agent reads the narrative pages, produces
Discovery/Update candidates, and feeds table corrections to the diff via
`giignl_prose_corrections.json` (Bontang/NWS cases).

**Open question:** whether to build a helper to focus that read.
- (A) Stay fully agent-driven — agent reads the narrative page ranges directly.
  Simplest; no new code. Risk: long narratives, easy to miss a paragraph.
- (B) `giignl_prose_extract.py` (or extend `giignl_extract.py`) to pre-filter
  narrative paragraphs containing capacity/date/lifecycle keywords, so the agent
  reviews a focused shortlist. Deterministic pre-filter, agent still judges.
- (C) Full structured prose extraction (regex/LLM) emitting candidate rows
  directly into the routing sheet. Most automation; highest build + maintenance.

**Recommendation:** (A) held for the 2026 edition; move to (B) once we see
which paragraphs get missed. Same "programmatic vs LLM-shaped" tradeoff as the
triage activity scan below.

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
GIIGNL does. The routing sheet still flags them, but with a soft
"investigate" framing.

**Concern:** this default could let real GEM errors slip through when GIIGNL
genuinely should have included a terminal and didn't.

**Options:**
- (A) Keep current: soft flag, user investigates
- (B) Hard flag every GEM-only operating row; force review
- (C) Threshold-based: GEM-only with capacity >X mtpa gets hard flag

**Recommendation:** (A) until first reconciliation reveals failure modes.
