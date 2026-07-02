# 2026-06-30 — Missing-year ref-sweep: status-timeline year backfill

**Trigger:** User asked for a picture of which LNG status-timeline milestones carry
a status but no year, with each backfillable year corroborated by verified sources —
ahead of a data-team discussion on how status is stored. New workflow class (not one
of the pre-existing router entries).

## What it is

A read-only research pass over the GEM read-only Postgres: every non-deleted LNG
(`plant."projectType" = 8`) `status_timeline` entry with `year IS NULL` and a tracked
status (`proposed`/`construction`/`operating`/`idled`/`mothballed`/`retired`/`shelved`/
`cancelled`/`FID`). Timeline-level gaps are invisible to a normal Update batch — the CSV
export only carries current status + anchor years — so this reads the timeline directly
([[status_timeline_readable_via_postgres]]). Each found year is corroborated with
`url_verifier.py`-passed sources and colored by confidence. Staging only; zero live-DB
edit footprint.

## Plan → workflow

Extract (deterministic DB query → shards) → one research subagent per shard against a
shared BRIEF → build (merge shards → csv/json/xlsx, re-derive `tl_order` from DB). A
second pass re-attacked the researchable UNRESOLVED.

## Outcome

**152 points** total.

- **FILLED 109** — high 50 (≥2 independent verified) / medium 24 (1 strong/primary) /
  low 35 (1 weak/proxy).
- **UNRESOLVED 43** — split into:
  - **Structural / unsourceable 31** — `substatus` starting `inferred` (GEM
    auto-classified dormancy: `inferred 2 y` shelved / `inferred 4 y` cancelled) OR
    `status=FID` + `substatus=planned` (an FID that never happened). No real dated event
    to cite — the "year" is an internal inference. These argue for a storage/methodology
    decision, not more research.
  - **Researchable-but-not-found 12** — genuine gaps (per-train shutdown dates, pre-web
    commissioning of legacy oil/NGL terminals, thin-coverage proposals).

The **backfillable-vs-structural split** is the headline for the data-team discussion:
of the 43 unfilled, 31 are structurally unsourceable and only 12 are true research gaps.

Data anomaly noted in passing: `status=retired` + `substatus=planned` (a retirement that
never happened) is contradictory — a correction candidate, not a missing year.
"Battery Rock 2005" was checked (flagged suspicious in an earlier pass) and vindicated —
DB shows an old mid-2000s project (proposed order=0 → cancelled 2007), so 2005 is plausible.

## Deliverable (KEPT)

- **`batches/deliverables/missing_year_refsweep_20260630_1146_ET.xlsx`** — tracked
  long-term (not gitignored, unlike routine `batches/*.xlsx`). Sheet
  `missing_year_refsweep` (one row per point) + `summary`. Year cell colored by tier
  (green=high / yellow=medium / red=low / grey=UNRESOLVED); `[ref]` URLs clickable.
- Regenerable siblings + raw research shards stay in
  `batches/staging/ref-sweep-missing-year-20260630_1146_ET/` as the audit trail:
  `missing_year_refsweep_results.{csv,json}`, `shards/*.json` (first pass),
  `shards_p2/*.json` (second pass), `BRIEF.md`, `_index.json`.

## Repeatable — the plumbing added this run

- **`scripts/refsweep_missing_year.py`** — the two deterministic ends in one tool.
  `extract` runs the canonical query, shards it, writes `BRIEF.md` + `_index.json`.
  `build` merges `shards/*.json` (+ `shards_p2/*.json` overlay by `st_id`), **re-derives
  `tl_order` fresh from the DB by `st_id`**, and writes csv/json/xlsx with tier coloring.
  Tested: `build` reproduces 152/109/43 with no warnings; `extract --shards 16` reproduces
  152 points with correct country names.
- **`docs/sops/ref_sweep.md`** (Ref-sweep SOP rev 1) — when to run, output, the
  extract→research→build workflow, UNRESOLVED interpretation, hard rules, pause-and-ask.
- **`docs/workflows.md` §8** — the command-by-command recipe.
- Router row in **`CLAUDE.md`**; abbrev **RSW** + index rows in
  **`docs/reference/sop_pointers.md`**; script-table entry in **`scripts/README.md`**.

## Failure classes fixed this run (so a rebuild is clean)

- **Schema drift blanked most years.** First-pass records were flattened
  (`year`/`ref1..3`/`tl_order`) but an early merge read only the raw fields
  (`proposed_year`/`proposed_refs`), blanking 92 first-pass years in the CSV. Fixed by
  treating the raw per-shard JSON as the immutable source of truth and rebuilding all
  three outputs from them with one canonical normalizer in `build`.
- **29 `None` `tl_order`s** (the second-pass points) — same schema-drift bug (raw shard
  field is `timeline_order`, flat field is `tl_order`). Fixed permanently: `build` always
  re-derives `tl_order` from the DB by `st_id`; the merge keeps input fields from the
  first-pass shards and overlays only research fields from the second pass.
- **Bontang trains C & D** (st_id 663/665) had verified 2018 in `verifications` but empty
  `proposed_year`/`proposed_refs` (agent contract slip). Patched
  `shards_p2/p2_bontang_result.json` to set 2018 + the IGU-2019 URL.

## Caveats / open items

- Read-only DB path required (`GEM_READONLY_DB_URL`); there is no CSV-export fallback for
  timeline-level data.
- Point count drifts run-to-run as staff edit the live DB — a re-extract the same day
  matched 151/152 (1-row drift: one st_id no longer missing-year, one newly missing-year).
  Expected data drift, not a bug.
- The 12 researchable UNRESOLVED are candidates for a future deeper pass (Wayback /
  regulator dockets / company IR / local-language press) or manual follow-up.
