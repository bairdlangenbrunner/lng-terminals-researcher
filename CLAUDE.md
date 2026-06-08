---
name: lng-terminals
description: Operating scaffolding for the GEM LNG Terminals research project — five workflows; the three doers produce a single staging xlsx per batch for the user to apply to the live GEM database manually. The workflows are (1) update existing terminals (standard or exhaustive tier), (2) discover new terminals, (3) reconcile against the annual GIIGNL report, (4) triage (decide what to work on this batch — memo only), and (5) QC (audit data health and applied edits — memo only). Use this skill whenever the user asks for a terminals batch, a GIIGNL diff, a stale-sweep, a discovery run, a qc pass or link-rot sweep, an FSRU sync check, or any work that produces or modifies the staging xlsx (lng_terminals_batch_YYYYMMDD_HHMM_ET[_scope]_mode.xlsx). Also use this skill when the user mentions "the GEM database", "the terminals tracker", "GGIT", "GIIGNL", "the methodology doc", a country-level sweep, an FSRU vessel-to-terminal sync, the status timeline, the entity tree, or any of the standard GEM tools (entity link, ownership tree, wiki, test database). The skill is the executable scaffolding — the project's research rules live in GEM's published methodology doc (the "LNG Terminals Manual"), which is authoritative for what counts as a terminal, what the lifecycle states mean, and how units are named. The SOPs in this project are operational — they describe how to do the work, citing the methodology rather than restating it.
---

# LNG Terminals — Backend Scaffolding

## What this is

Scaffolding for an agentic research workflow that helps a GEM contractor update the Global Gas Infrastructure Tracker's LNG terminals dataset. The user has direct edit access to the live GEM database but does NOT delegate writes to the agent — every batch produces a staging xlsx that the user reviews and applies manually.

Where things live — **read on demand as the workflow dictates, not at session start**:

- **The GEM LNG Terminals Manual** (Google Doc) — the authoritative methodology ("the methodology doc"). Not in the repo; reference URL in `docs/reference/sop_pointers.md`.
- **SOPs** — `docs/sops/`: `reconciliation.md` (three-way diff vs GIIGNL; generic body + GIIGNL appendix, future IGU SOP reuses the body), `update.md` (annual bread-and-butter; standard/exhaustive tiers; folds in [ref]-fill), `discovery.md`, `triage.md`, `qc.md` (data-health audit; memo only).
- **Workflow recipes** — `docs/workflows.md`: the step-by-step command sequences for every workflow below, plus the FSRU sync rule detail.
- **Reference docs** — `docs/reference/` (`gem_db_schema.md`, `lifecycle_rules.md`, `source_roster.md`, `entity_canonical_map.md`, `unit_conventions.md`, `sop_pointers.md`, `workbook_conventions.md`) and `docs/country_notes/`.
- **Scripts** — `scripts/`; index, invocation order, when-to-read-source, and the GIIGNL deep-dives all in `scripts/README.md`.

## Two batch inputs

1. **Fresh GEM export** (gitignored; pulled at the start of every batch): `python gem_query.py --all-fields lng -o gem_export.csv && python pull_gem_db.py --map-only` → CSV + column-index map (`.colmap.json`). (`gem_all_fields.py` is the library behind `--all-fields`; invoking it directly is a silent no-op — verify the CSV mtime actually changed.) No cookies; the cookie-based `gem_export_via_web.py` (wrapped by a bare `python pull_gem_db.py`, auth from `.env`) is the fallback.
2. **GIIGNL annual reports** — a committed archive of every edition 2020–2026 in `data/` (manifest in `data/README.md`: filenames, page counts, table/fleet page locations, edition→calendar-year map; edition N covers calendar year N−1). All seven are genuine PDFs (v1.4–v1.7) with usable text layers — the `pdftotext` pipeline applies (offsets are 2026-tuned; older editions need re-derivation per `data/README.md`). Current target: `data/GIIGNL-2026-Annual-Report-0526b.pdf`. **`file <path>` before assuming the format** — a future download could arrive as the legacy zip-of-JPEGs (vision pipeline in git history); a `(zip deflate encoded)` tag from `file` is just normal PDF stream compression, not the zip form.

## Read the methodology + relevant SOPs first

Before any batch:

1. Confirm the methodology doc is in context (long Google Doc — if not visible, ask the user to re-share). Note its "Last updated" line.
2. View the SOPs relevant to the workflow being run.
3. Check `docs/reference/sop_pointers.md` for a quick rule lookup map.
4. If an SOP cites a methodology section that no longer exists or has changed, flag to the user before proceeding — the methodology is what GEM staff review edits against.

## Workflow router

Full command-by-command recipes live in `docs/workflows.md` — **read the relevant section before starting a batch.**

| Workflow | Trigger phrases | Recipe + rules |
|---|---|---|
| **Reconcile against GIIGNL** (annual, on report release) | "reconcile against GIIGNL", "GIIGNL diff", "compare GEM to the new GIIGNL", "process the [year] GIIGNL report" | `docs/workflows.md` §1 + Reconciliation SOP |
| **Update existing terminals** (most common; tiers: **standard** default / **exhaustive**) | "update terminals in [country/region]", "standard update for [country]", "exhaustive update of [country]", "re-verify everything in [country]", "refresh the [country] entries", "fill blank refs", "annual update for [country]", "check what's stale in [country]" | `docs/workflows.md` §2 + Update SOP (tiers: §2.1 standard / §2.2 exhaustive) |
| **Discover new terminals** | "find new terminals in [region]", "discovery run", "what's missing from GEM in [region]", "catch-up sweep", "any new proposals in [region]" | `docs/workflows.md` §3 + Discovery SOP |
| **Triage** (plan the batch) | "what should we work on this quarter", "what's stale", "plan the [Q] batch", "where are the gaps" | `docs/workflows.md` §4 + Triage SOP; output is a markdown memo, not an xlsx |
| **Quality control** (backward-looking checker) | "qc pass", "check accuracy", "link-rot sweep", "did my edits land", "audit the data quality" | `docs/workflows.md` §6 + QC SOP; output is a markdown memo, not an xlsx; fixes route to a follow-on Update batch |
| **Regional sweep** (scaled multi-country update/discovery, one subagent per country) | "sweep [region]", "update every country in [region]", "audit the whole tracker", "overnight sweep" | `docs/workflows.md` §5; **read `batches/staging/README.md` + `SWEEP_PROGRESS.md` first** to resume a sweep in progress; the dispatch prompt states the tier |

Routing notes that prevent the most common mistakes:

- A GIIGNL-only (`report_only`) row is almost never a missing terminal — **try to match it to an existing GEM terminal under a different name first** (recipe §1 step 6); only genuine misses go to Discovery.
- GIIGNL is one source in a conflict, not automatically authoritative — value-disagreements route to the Update workflow's normal source-search.
- Discovery scope = `covered ∪ uncovered` countries: `completeness_sweep.py`'s `coverage_gap` block adds coastal countries with zero GEM terminals (Discovery SOP §4.0).
- An Update batch runs at the **standard tier by default** — worklist = stale flags ∪ every proposed/construction/shelved unit (the `dev_pipeline` block) ∪ in-scope blank-ref fills; rows off the worklist stay untouched. "Exhaustive" / "re-verify everything" means every field and every existing `[ref]` on every in-scope row (Update SOP §2.1/§2.2).
- QC never edits: it audits data already in GEM (and edits already applied), emits a memo, and routes fixes to an Update batch — "QC detects, Update fixes".

## FSRU sync rule (cross-project)

FSRUs are tracked in both this tracker and (if the user runs it) the LNG carrier project. Carriers own vessel identity/specs; terminals own terminal identity/operations; **vessel name + IMO are the linking fields and must agree in both backends**. Any batch touching an FSRU runs `python fsru_sync_check.py`; mismatches go in the `fsru_sync` sheet. Vessel reassignment (FSRU moves terminals; FSU/FRU; Deepwater Port exclusion) is modeled — field-ownership table and mechanics in `docs/workflows.md` §7. Without a carrier backend the script short-circuits gracefully.

## Scripts

`scripts/README.md` is the index: per-script purpose, typical invocation order, when to read each script's source, and the **deep-dives for `giignl_extract.py`, `report_diff.py`, and `giignl_fsru_fleet.py` — read the relevant deep-dive before editing those** (they're heavily edge-case-hardened; the fixes look like over-engineering until you hit the PDF layout they defend against). Trust the scripts by default — versioned scaffolding, not throwaway code. If you fix something, the fix is permanent repo improvement for the next batch.

Known issue: `fetch_timeline.py`'s default Heroku host is stale (404) — set `GEM_PROJECT_DB_BASE_URL`; until reachable, route status changes to qa notes rather than staging blind timeline edits.

## Output workbook

One combined xlsx per batch at `<repo-root>/batches/lng_terminals_batch_<YYYYMMDD>_<HHMM>_ET[_<scope>]_<mode>.xlsx` (stamp via `TZ=America/New_York date "+%Y%m%d_%H%M_ET"`).

- **The name says what it is:** the `<mode>` token (`update` / `discovery` / `reconciliation`) is ALWAYS present; the `<scope>` slug (lowercase, hyphenated — a country, region, or report edition like `giignl2026`) is present whenever the batch is scoped. Omit `_<scope>` only for a genuinely global batch. (Triage and QC produce memos, not workbooks: `batches/triage_<stamp>_ET.md` / `batches/qc_<stamp>_ET.md`.)
- **Path caveat:** the `../batches/` shorthand in recipes assumes CWD is `scripts/`. From the repo root use `--output batches/…` — `../batches/` would silently create a stray dir outside the repo. Confirm the written file is under `<repo-root>/batches/` after building.
- **Never overwrite an existing batch file** — every (re)build gets a NEW file with a freshly-generated timestamp, even small iterative rebuilds in one session. The user prunes old ones.
- **Staged inputs live under `batches/staging/`, never loose in the repo root or `scripts/`** — `recon/<report><year>/` for reconciliation batches, `<scope-slug>/` for ad-hoc batches, `<region>/` for sweeps (layout in `batches/staging/README.md`). Agent-authored staging JSON is committed (audit trail); derived artifacts are gitignored.
- Sheet-by-sheet definitions and the full color semantics: `docs/reference/workbook_conventions.md`. When adding a sheet builder to `build_review_package.py`, also add its `SHEET_DESCRIPTIONS` entry.

Color conventions (per cell, not per row — in `updates`, `new_units`, `audit_operating`, and the recon paste view `edits_to_gem`): **green** = primary/regulatory source or two independent corroborations; **yellow** = entity confirmed but value implied/contested/single non-primary source; **red** = single weak source (prefer blank + `qa_review` entry); **blue** = unchanged but re-verified this batch. **The reconciliation `audit_*` sheets override these semantics** (red = GIIGNL-vs-GEM conflict, graded light/dark by <5%/≥5% capacity delta; light red in `audit_nonoperating` = "GEM has, GIIGNL doesn't") — full rules in `docs/reference/workbook_conventions.md`. In `edits_to_gem` the colors keep their normal source-confidence meaning (green/yellow/red), since that sheet carries the agent's *researched* resolved values, not raw diff flags.

## Hard requirements (these override anything below)

- **Never modify the live GEM database.** Every batch produces a staging xlsx; the user applies edits manually. The agent's edit footprint on the production DB is exactly zero.
- **Every URL passes `url_verifier.py` before going in the xlsx** — no exceptions, even URLs that worked in prior batches. Verification is not just "the page loads": the specific data value the cell asserts (capacity, owner, status, year, vessel) MUST appear explicitly on that page/PDF. Pass the actual claimed value as the verifier token; a URL that loads but doesn't contain the value is a failed citation, not a source.
- **NEVER cite gem.wiki or globalenergymonitor.org as a source or `[ref]` URL — anywhere, in any sheet.** It is GEM's own publication; citing it as evidence for the GEM database is circular. This is absolute: not in `updates`, `wiki`, `new_terminals`, `new_units`, `monitor`, or `qa`. Any source that merely derives from or republishes GEM (IEEFA/Wikipedia/news footnoting GEM) is likewise NOT independent evidence — chase the primary source it points to and cite THAT. If the only finding is on gem.wiki, treat the value as unsourced (leave blank + qa note), never citable.
- **Corroborate every staged value with ≥2 independent working URLs that each explicitly contain it (3 when findable); a single source is the disfavored exception, not the norm.** Independent = different publishers/origins, not two pages of the same outlet and not a primary + its own press echo. Green requires ≥2 independent corroborations (or one primary/regulatory source); a lone non-primary source is yellow and a lone weak source is red — and a red single-weak-source value should usually be left blank with a `qa_review` entry instead of staged.
- **Pull a fresh GEM CSV at the start of every batch** — the user and other GEM staff edit between batches.
- **Re-derive the column-index map from the fresh header row every run** — don't hard-code offsets; the 115-col schema can drift.
- **Never auto-apply GIIGNL or IGU values.** A reconciliation finding is a candidate for Update, not an applied edit.
- **A GEM `researcher_notes` cell can document a DELIBERATE divergence the reconciliation must defer to — never override it with an automated capacity/value bump.** Canonical case (issue #6, Corpus Christi): GIIGNL counts trains as operating that GEM deliberately holds as `construction` ("commercial operations not declared"). The diff still flags the delta (no tolerance band); only the *recommendation* defers — verify status, don't overwrite capacity. See Reconciliation SOP §5.8 and `build_review_package.py`'s `_nonop_explains_shortfall`.
- **Project-level field changes apply to ALL unit-rows of a multi-unit project** — the export duplicates project-level fields across unit-rows; updates must too.
- **No orphan `[ref]` cells** — never fill a `[ref]` without a paired data value (carrier-project Rule F).
- **A URL belongs ONLY in a `[ref]` column; a data/enum column holds a VALUE, never a link.** `Status` reads `proposed`/`construction`/`operating`/`idle`/`mothballed`/`shelved`/`cancelled`/`retired` (its citation goes in `Status [ref]`); `Capacity` is a number; `Owner`/`Operator` are names. Never put an http(s) URL in `Status`, `Capacity`, `Owner`, `FacilityType`, `Location`, etc. A staged update record fills a `[ref]` column by setting `field_name` to that `<field> [ref]` with the URL as `new_value`; the optional `ref_field` only ever names another `[ref]` column. The build script enforces this — it routes URLs to `[ref]` columns only and refuses (with a `GUARD:` warning) any URL aimed at a non-`[ref]` column (free-text `ResearcherNotes*`/`Wiki` excepted).
- **Status timeline updates require pulling the existing timeline first** via `fetch_timeline.py` — the export only has current status + anchor years.
- **Don't create duplicate entities.** Run `entity_lookup.py` before staging any new owner/operator/parent — entities are shared across all GEM trackers.
- **Out-of-scope fields are read-only:** LH2, NH3, SyntheticLNG, RetrofitProposed, AltFuelPrelimAgreement, AltFuelCallMarketInterest, AltFuelNotes, PCINotes, PCI3-PCI6 — "no longer updated as of 2026" per the methodology. The build script must NEVER write to these columns.

## When to escalate to the user

Pause and ask before proceeding when:

- A whole class of GEM values looks systematically wrong (suggests a schema misunderstanding, not a research finding)
- A methodology rule and an SOP rule conflict
- A discovery batch surfaces more than ~5 candidate clusters in one country (systematic gap — worth a conversation before generating 5+ new records)
- The "sufficient information to add" threshold is genuinely ambiguous on a candidate
- A reconciliation batch finds disagreement on more than ~10% of matched rows — judged by *material* capacity/owner conflicts, not the raw `matches_with_disagreement` count, which inflates because any non-zero delta flags (see Reconciliation SOP §6)
- A QC pass trips a systemic threshold — >10% of sampled spot-check cells unsupported, or a batch's apply_check shows multiple diverged edits (QC SOP §6)
- An entity that should exist in the GEM entity system isn't found
- The GIIGNL report file isn't in either expected format (real PDF with text layer, or legacy zip-of-JPEGs)
- FSRU sync surfaces a reassignment that can't be cleanly resolved (vessel moved to a terminal not yet in GEM)
