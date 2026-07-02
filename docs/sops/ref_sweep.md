# LNG Terminals Missing-Year Ref-Sweep SOP

Last revised: 2026-07-01 (rev 2 — fuel_type column, `--sync-db` refresh flag)

A focused, read-only research pass that backfills the **year** on GEM LNG
status-timeline entries that carry a status (`proposed`, `construction`,
`operating`, `idled`, `mothballed`, `retired`, `shelved`, `cancelled`, `FID`)
but have **no year attached**. Each found year is corroborated with verified
source URLs and staged for the user to apply manually.

This is a variant of the Update workflow's `[ref]`-fill (Update SOP §2.1) applied
to the **status timeline** rather than the CSV export — the export only carries
current status + anchor years, so timeline-level gaps are invisible to a normal
Update batch and need the direct Postgres read (`docs/reference/gem_db_schema.md`;
[[status_timeline_readable_via_postgres]]).

Output is a workbook (`missing_year_refsweep_results.xlsx`) plus its CSV/JSON
siblings — one row per timeline point, the found year colored by source
confidence. Like every batch it is **staging only**; the agent never writes to
the live DB.

## §1 When to run this SOP

- The user wants a picture of how many, and which, status milestones lack a year
  (e.g. ahead of a data-team decision on how status is stored).
- A methodology/storage change to the status timeline is under discussion and the
  team needs the backfillable-vs-structural split (see §6).
- As a targeted clean-up when a country/region's timelines are known to be thin.

Not part of the routine quarterly cycle — it's an on-request analysis.

## §2 What it produces

`scripts/refsweep_missing_year.py build` writes, into the batch's staging dir:

- `missing_year_refsweep_results.xlsx` — sheet `missing_year_refsweep` (all points,
  one row each) + a `summary` sheet. The **year** cell is colored by tier:
  green = high (≥2 independent sources), yellow = medium (1 strong/primary),
  red = low (1 weak/proxy), grey = UNRESOLVED. `[ref]` URLs are clickable.
- `missing_year_refsweep_results.csv` / `.json` — same rows, flat.

Columns: `country, terminal, unit, fuel_type, status, substatus, tl_order, year,
class_out, tier, independent, ref1, ref2, ref3, source_language, researcher_notes,
pu_id, st_id`.

- `st_id` = `status_timeline.id` (the specific timeline row).
- `fuel_type` = `lng_unit.fuel` (LNG / Oil / NGL / NH3 / LH2 / combos) — lets the
  legacy oil/NGL terminal rows be sorted apart from LNG. Like `tl_order` it is
  **re-derived fresh from the DB at build time** (by `pu_id`), never trusted from
  a shard copy, so shards written before the column existed still get it.
- `tl_order` = the DB's `status_timeline.order` — a per-unit sort key for the
  milestone within that unit's timeline. **Not a dense index**: most units start
  at 1, a handful at 0, and gaps occur (e.g. 1,2,3,6,9). It is the curated logical
  order and does not always ascend by year. Always trust the DB value, never a
  copy carried through the shard round-trip.

The polished workbook is then copied to `batches/deliverables/` (kept in git);
the CSV/JSON + raw research shards stay in the staging tree as the audit trail.

## §3 The two deterministic scripts steps + the agentic middle

`scripts/refsweep_missing_year.py` wraps the two deterministic ends; the research
in the middle is done by subagents against the shared BRIEF.

### §3.1 Extract (deterministic)

```
python refsweep_missing_year.py extract --shards 16 \
    --output ../batches/staging/ref-sweep-missing-year-<stamp>
```

Runs the canonical query — every non-deleted LNG (`plant.projectType = 8`) status-
timeline entry with `year IS NULL` and a tracked status — splits it into N shard
input files, and writes the shared agent `BRIEF.md` + an `_index.json`. The count
drifts run-to-run as GEM staff edit the live DB (that's expected; §7).

### §3.2 Research (agentic — one subagent per shard)

Hand each `shard_NN.json` to a research subagent (high effort is sufficient; the
first pass used it). Each agent reads `BRIEF.md` and, for every point, finds the
milestone year and corroborates it. The year to find depends on `status`:
proposed → first announced; construction → ground-breaking; operating →
commercial start; idled/mothballed/retired → that event's year; shelved/cancelled
→ that event's year; FID → the FID year.

Hard rules (enforced by the BRIEF, mirror CLAUDE.md):
- **Every URL passes `url_verifier.py`** with the 4-digit **year** + one confirmed
  on-page token, both required. A page that loads but lacks the year is not a source.
- **Never cite gem.wiki / globalenergymonitor.org** (circular), nor theodora.com /
  abarrelfull / any wikidot; anything that merely republishes GEM is not
  independent — chase the primary source.
- **≥2 independent sources** for green; 1 strong/primary = yellow; 1 weak = red;
  none = UNRESOLVED. Mirrors/host-variants of one document count as ONE source
  ([[mirror_urls_not_two_sources]]).
- **Never fabricate a URL.** No defensible year → UNRESOLVED with a reason.
- Search in the country's language when English is thin; record `source_language`.
- Agents write their result file **incrementally** (every ~3 points) so a session
  interruption doesn't lose the research ([[limit_resume_behavior]] — a stalled
  agent can be resumed via SendMessage to flush trapped work to disk).

Each agent writes `shards/<shard>_result.json` (contract in the BRIEF).

### §3.3 Optional second pass on the UNRESOLVED

Split the *researchable* UNRESOLVED points (see §6 — exclude the structural ones)
into new shards under `shards_p2/`, and dispatch agents told these already failed
once. Second-pass tactics that beat the first pass: Wayback (web.archive.org) for
bot-blocked/dead pages, FERC & other regulator dockets, company IR / port-authority
histories, EIA data series, and local-language trade press. `build` overlays these
onto the first-pass records by `st_id` (research fields only).

### §3.4 Build (deterministic)

```
python refsweep_missing_year.py build \
    --dir ../batches/staging/ref-sweep-missing-year-<stamp> [--sync-db]
```

Merges `shards/*.json` (base) + `shards_p2/*.json` (overlay), **re-derives
`tl_order` and `fuel_type` fresh from the DB** (by `st_id` / `pu_id`), normalizes
to one canonical schema, and writes the CSV/JSON/xlsx. It warns (doesn't fail) if
a FILLED row is missing a year (agent contract slip) or a point isn't found in
the DB.

`--sync-db` prunes points that left the extract scope in the live DB — the
`st_id` was deleted; the plant/unit was deleted upstream (year stays NULL but
the record left the tracker); the year is no longer NULL because a backfill was
applied; or the status changed to an untracked value — and prints each drop.
Default **off** so a historical run's staging dir rebuilds exactly as-was; turn
it on for refresh runs against the current DB.

### §3.5 Refreshing a prior run (reuse the research)

To refresh an existing deliverable against the current DB without redoing the
research: extract a **new** staging dir, copy the prior run's `shards/*_result.json`
and `shards_p2/*` into it, refresh each copied record's identity fields
(country/terminal/unit/status/substatus/pu_id) from the fresh extract by `st_id`,
author records for any newly-appeared points, then `build --sync-db`. Third-pass
research files go in `shards_p2/` named `p3_*` — they sort after `p2_*`, so the
newest pass wins the overlay.

## §4 Workflow (linear)

1. `python refsweep_missing_year.py extract --shards 16 --output ../batches/staging/ref-sweep-missing-year-<stamp>`
2. Dispatch one research subagent per `shard_NN.json` (§3.2). Let them run; resume
   any that stall (don't restart from scratch).
3. `python refsweep_missing_year.py build --dir <that dir>` → review counts.
4. (Optional) Second pass on the researchable UNRESOLVED (§3.3), then `build` again.
5. Copy the final `.xlsx` to `batches/deliverables/` with a fresh stamp; leave the
   CSV/JSON + shards in staging as the audit trail.
6. Present the workbook + the backfillable-vs-structural split (§6) to the user.

## §5 What it does NOT do

- **No writes to the live DB** — staging only; the user applies edits.
- **No `[ref]` in a value column** — the year goes in the timeline's year field; its
  citations are the `ref1..3` columns. (There is no orphan-`[ref]` case here because
  the value and its refs are staged together, or not at all.)
- **No coordinates / inferred values** — only real, datable events get a staged year.
- **No FSRU sync, no entity lookups** — those belong to Update/Discovery batches.

## §6 Interpreting UNRESOLVED — the backfillable-vs-structural split

Not every missing year is a research gap. Bucket the UNRESOLVED before reporting:

- **Structural / unsourceable — cannot be fixed by research:**
  - `substatus = inferred N y` (`inferred 2 y` shelved, `inferred 4 y` cancelled):
    GEM auto-classified the project dormant after N years of inactivity. There is
    no real-world dated event to cite — the "year" is an internal inference.
  - `status = FID` + `substatus = planned`: an FID that never happened.
  - These argue for a **storage/methodology** decision, not more searching. A model
    that distinguishes "inferred, no event date" from "real event, date unknown"
    cleanly separates them.
- **Researchable but not found:** genuine gaps (per-train shutdown dates, pre-web
  commissioning of legacy oil/NGL terminals, thin-coverage proposals). Candidates
  for a second pass (§3.3) or manual follow-up.

Also flag **data anomalies** surfaced along the way — e.g. `status = retired` with
`substatus = planned` (a retirement that never happened) is contradictory and worth
a correction, not a year.

## §7 Hard rules

- **Read-only.** Zero edit footprint on the production DB.
- **Re-derive `tl_order` and `fuel_type` from the DB every build** — never trust a
  value carried through the shard files (the raw shard field is `timeline_order`,
  the flat field is `tl_order`; conflating them once silently dropped the value).
- **URL-verify every citation** with the year + a confirmed token (CLAUDE.md gate).
- **The point count drifts** between extract runs as staff edit the live DB — that's
  expected, not a bug; re-extract if the DB has moved materially since the shards.
- **Structural UNRESOLVED are not a research failure** — report them as such (§6).

## §8 Pause-and-ask triggers

- If a whole class of timeline years looks systematically wrong (suggests a schema
  misread, not a data gap) — stop and confirm the query/interpretation first.
- If a large share of points are structural (§6), surface that as the headline —
  it's a methodology signal the user will want to act on before more research.
- If the DB read path is unavailable (`GEM_READONLY_DB_URL` unset/unreachable) —
  stop; there is no CSV-export fallback for timeline-level data.

---

## Quick-reference card

| Step | Command / action |
|---|---|
| Extract | `refsweep_missing_year.py extract --shards 16 --output ../batches/staging/ref-sweep-missing-year-<stamp>` |
| Research | one subagent per `shard_NN.json` against `BRIEF.md`; resume stalls, don't restart |
| Build | `refsweep_missing_year.py build --dir <that dir>` (add `--sync-db` on refresh runs) |
| 2nd pass | researchable UNRESOLVED → `shards_p2/`, re-dispatch (Wayback/FERC/IR/local-lang), re-build |
| Refresh | new extract dir + copy prior results in (§3.5), `p3_*` overlays, `build --sync-db` |
| Keep | copy final `.xlsx` → `batches/deliverables/<slug>_<stamp>.xlsx` |

| Tier | Meaning | Year-cell color |
|---|---|---|
| high | ≥2 independent verified sources | green |
| medium | 1 strong/primary verified source | yellow |
| low | 1 weak/proxy/conflicting source | red |
| (UNRESOLVED) | no verifiable year | grey |
