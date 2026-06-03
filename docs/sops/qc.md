# LNG Terminals QC SOP

Last revised: 2026-06 (rev 1, initial draft)

Operational rules for the quality-control pass — the **backward-looking checker** of the workflow family. Where Triage looks forward ("what should we research next?"), QC looks backward: it audits the data already in GEM and the edits already applied, then routes anything that needs fixing into a follow-on Update batch. **QC detects, Update fixes** — the same split as Reconciliation→Update.

QC's output is a **memo** (markdown, not xlsx). QC stages no edits, builds no workbook, and never touches the live database. This is deliberately the second-lightest SOP after Triage: all the actual fixing happens through the Update SOP's normal discipline.

## §1 When to run this SOP

Trigger conditions:
- Periodic data-health check — quarterly is a good default cadence, complementing triage (triage at cycle start to choose work; QC at cycle end to check it)
- **After the user applies a large batch** (especially a regional sweep) — confirm the manual edits landed correctly (§3.4)
- Suspected link-rot debt (old citations failing during unrelated batches, or no citation sweep in recent memory)
- User phrases: "qc pass", "check accuracy", "link-rot sweep", "did my edits land", "audit the data quality"

QC is NOT a precondition for any other batch and never blocks one. Update/Discovery/Reconciliation carry their own in-batch verification gates (URL verification, entity lookups, recalc); QC is the periodic audit on top, not a substitute for those gates.

## §2 What QC produces

A single markdown memo with five sections:

1. **Mechanical-integrity summary** — counts and notable patterns from `completeness_sweep.py`, `stale_sweep.py`, and `dedup_index.py` (§3.1)
2. **Citation link-rot summary** — dead / blocked / name-miss counts from `citation_qc.py`, by country and by [ref] column (§3.2)
3. **Accuracy spot-check findings** — the sampled units and the supported / unsupported / stale verdict per checked cell (§3.3)
4. **Post-apply check results** — applied / not_applied / diverged counts from `apply_check.py`, with every diverged edit listed (§3.4)
5. **Recommended follow-ups** — concrete batch options, each naming the workflow and (for Update) the tier, e.g. "standard Update, scope = the 14 dead-ref rows in Indonesia" or "exhaustive Update, Argentina (31% link-rot)"

The memo gets saved to `../batches/qc_<YYYYMMDD>_<HHMM>_ET.md` (stamp via `TZ=America/New_York date "+%Y%m%d_%H%M_ET"`) and presented to the user. No xlsx is produced by QC itself.

## §3 The four passes

Run all four for a periodic health check; a targeted QC run (e.g. "did my edits land") can run a single pass — say which passes ran in the memo.

### §3.1 Mechanical integrity

Existing tools, no web traffic, minutes to run:

- `python completeness_sweep.py` — blank `[ref]` cells with populated data (the [ref]-fill worklist, Update SOP §3.1), orphan refs (citation without data — Rule F violations already in the DB), missing required fields per status, project-level fields inconsistent across unit-rows, enum values outside the schema catalog, plus the country `coverage_gap` block
- `python stale_sweep.py` — dormancy flags (lifecycle thresholds) plus the `dev_pipeline` block (every proposed/construction/shelved unit with recency annotation — sizes the standard-tier Update worklist, Update SOP §2.1)
- `python dedup_index.py` — project-key collisions that could indicate duplicate terminals

The memo reports counts, concentrations (e.g. "orphan refs cluster in pre-2023 Brazil rows"), and deltas vs the previous QC memo where one exists.

### §3.2 Citation link-rot sweep

`python citation_qc.py [--country "<C>"] [--status <status>] [--max-urls N]` — batch re-verification of EXISTING `[ref]` URLs from the export via `url_verifier.py`. This is the scope-wide, read-side complement to Update SOP §7.2 (which re-verifies only rows a batch touches).

Verdict grading (see the script docstring):
- **dead** — hard link-rot (404/410/5xx, DNS failure, soft-404, scanned-PDF-no-text). These count toward the §6 escalation threshold.
- **blocked** — bot-wall/paywall (HTTP 401/403/429, Cloudflare interstitials, members-only). Probably fine for a human; the memo lists them as "verify manually", NOT as rot.
- **name-miss** — page is live but doesn't contain the terminal name. Advisory only (names are often suffixed or translated).

Whole-DB runs are thousands of URLs: shard by country or status band across QC cycles rather than forcing one giant run, and say in the memo which shard ran (`--max-urls` truncation is recorded in the JSON — never report a truncated run as full coverage).

### §3.3 Accuracy spot-check (agent-driven)

A stratified sample of ~20–30 units per QC pass, weighted toward where errors matter or accumulate:
- **Recently-edited rows** (newest `LastUpdated`) — checks our own latest applied work
- **High-capacity operating terminals** — the rows external users most depend on
- **Development-pipeline units** (from the `dev_pipeline` block) — where status churn makes stale values likeliest

For each sampled unit, re-verify the key fields — `Status`, `CapacityinMtpa`, `Owner`/`Operator`, `ActualStartYear`/`LatestPlannedStartYear` — two ways:
1. **Against the cited `[ref]`** — does the cited source actually contain and support the GEM value (cluster coherence, Update SOP §5)?
2. **One fresh corroboration search** per unit — does a current source agree?

Verdict per checked cell: **supported** (citation backs the value), **unsupported** (citation doesn't contain/support the value — possible transcription or cluster-coherence error), or **stale** (citation supports it but a newer credible source contradicts — a candidate Update finding, not an error). The memo lists every unsupported and stale cell with the evidence.

### §3.4 Post-apply check

`python apply_check.py --batch ../batches/<applied batch>.xlsx` — reads the applied batch's `updates` sheet and compares each staged edit against the fresh export, classifying applied / not_applied / **diverged** (fresh value matches neither old nor new — the manual-transcription-error catcher) / not_found / reverify_only.

Run this against any batch the user reports having applied since the last QC pass. Caveats: the fresh pull must postdate the user's application; formatting the DB re-renders server-side (dates, rounding) can read as benign diverged — equal-float values are auto-normalized, anything else is reviewer judgment.

## §4 Workflow (linear)

1. Fresh pull: `python gem_all_fields.py -o gem_export.csv && python pull_gem_db.py --map-only` — QC against a stale export is meaningless, and §3.4 specifically needs a pull that postdates the user's apply
2. `python completeness_sweep.py`, `python stale_sweep.py`, `python dedup_index.py` (§3.1)
3. `python citation_qc.py` with the cycle's scope shard (§3.2)
4. Accuracy spot-check (§3.3) — draw the sample, verify cells, record verdicts
5. `python apply_check.py --batch …` for each batch applied since the last QC pass (§3.4); skip if none
6. Draft the QC memo with sections per §2
7. Save to `../batches/qc_<YYYYMMDD>_<HHMM>_ET.md`
8. `present_files` the memo
9. **Stop and ask the user** which recommended follow-up batch(es), if any, to spin up

QC doesn't run any other batch's workflow. After the user picks, the Update (or Discovery) SOP takes over — at the tier the memo recommended.

## §5 What QC does NOT do

- **No xlsx output.** The xlsx scaffolding belongs to Update/Discovery/Reconciliation batches.
- **No staged edits and no fixes.** Even a trivially obvious fix (dead URL that should be blanked) routes to an Update batch — that batch's gates (URL verification, confidence labeling, qa_review logging) are what make the fix safe.
- **No live-database writes.** Ever.
- **No external-report reconciliation.** Diffing GEM against GIIGNL/IGU is the Reconciliation SOP — QC checks GEM against *its own citations* and *its own staged batches*.
- **No new-terminal hunting.** A coverage gap surfaced by `completeness_sweep.py` is reported and routed to Discovery, not researched in-pass.

## §6 Escalation thresholds / pause-and-ask

- **>10% of sampled spot-check cells come back unsupported** → systemic flag. That error rate suggests a methodology or process problem (cluster-coherence drift, transcription pattern), not isolated mistakes. Stop and discuss before recommending routine follow-ups.
- **>25% dead link-rot in a single country** (dead only — blocked doesn't count) → recommend an **exhaustive** Update for that country; its citation base has decayed past patch-level.
- **apply_check returns multiple `diverged` edits from one batch** → flag a possible apply-process error (e.g. wrong column pasted); list every diverged cell and ask before assuming later-edit explanations.
- **`dedup_index.py` shows new project-key collisions** since the last QC pass → possible duplicate terminal created; surface to the user (entities and terminals are shared across GEM trackers).
- **The export shows obvious schema drift** (colmap derivation fails, enum catalogs full of new values) → stop; data-source issue precedes any QC verdict.

## §7 Hard rules

- **Pull a fresh GEM CSV at the start of every QC run** — every pass compares against current data.
- **Every URL re-check goes through `url_verifier.py`** (directly or via `citation_qc.py`) — no bare curl checks; the soft-error and PDF handling are the point.
- **QC never writes** — not the live DB, not an xlsx, not staged JSON. Memo only.
- **Always present the memo and stop** — follow-up batches start only on the user's pick.
- **Never report partial coverage as full** — a truncated or sharded citation sweep says so in the memo.

---

## Quick-reference card

| Pass | Tool | QC uses it to... |
|---|---|---|
| Mechanical integrity (§3.1) | `completeness_sweep.py` + `stale_sweep.py` + `dedup_index.py` | Find blank/orphan refs, missing fields, bad enums, project-field inconsistency, dup-key collisions |
| Citation link-rot (§3.2) | `citation_qc.py` (wraps `url_verifier.py`) | Grade every existing [ref] URL in scope: dead / blocked / name-miss |
| Accuracy spot-check (§3.3) | Agent research on a ~20–30 unit stratified sample | Verify key field values against their cited sources + one fresh corroboration |
| Post-apply check (§3.4) | `apply_check.py` | Confirm manually-applied batch edits landed (catch transcription errors) |

| QC output | Where |
|---|---|
| Markdown memo with findings + recommended follow-ups | `../batches/qc_<YYYYMMDD>_<HHMM>_ET.md` |
| Tool JSON artifacts | `work/*.json` (scratch — re-derivable, gitignored) |
| (No xlsx) | QC never produces a workbook; fixes route to an Update batch |
