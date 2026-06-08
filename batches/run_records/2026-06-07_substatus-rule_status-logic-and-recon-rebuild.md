# Run record — planned/actual substatus rule + recon rebuild (2026-06-07)

One md per major run lives in `batches/run_records/` so you can see at a glance what was last done, when, and with what scope.

## What this run is

- **Date:** 2026-06-07 (afternoon/evening ET)
- **Trigger:** Tilbury Island investigation (GEM showed operating capacity inflated to 0.93 mtpa). Root cause turned out to be a GEM **status-data model** issue the tooling didn't honor, which the user articulated as a rule.
- **Methodology doc:** already documents this exact derivation (`lifecycle_rules.md` "Why ordering matters": current status excludes `planned` timeline entries). The bug was that the flat export *can* surface a `planned` entry and the diff tooling trusted bare `Status == "operating"`.

## The rule (user-stated, now enforced)

A non-`proposed` status on the advancement ladder (`proposed` → `construction` → `operating`) only counts as the unit's official status when **substatus = `actual`**. A **`planned` substatus** means the milestone is merely projected, so the unit is **effectively `proposed`**. (Dormant/terminal states — `shelved`, `cancelled`, `retired`, `idled`, `mothballed` — use the separate `confirmed`/`inferred N y` substatus axis and are NOT affected.)

## What changed

**Code (permanent repo fix):**
- `scripts/normalize.py` — new `effective_status(status, substatus)` helper (+ `_ADVANCING_STATUSES`).
- `scripts/report_diff.py` — reads `Substatus` and applies `effective_status` at the single GEM-row read in `_build_gem_project_table`, so a `planned` unit never inflates the operating-capacity total. Stores `raw_status`/`substatus` on each unit dict for audit.
- `scripts/add_effective_status.py` — NEW. Appends an `EffectiveStatus` (+ `StatusRuleApplied`) column to a handoff/archive export, leaving the raw 115-col schema intact.
- `docs/reference/lifecycle_rules.md` — corrected the false claim that "the export only ever emits `actual`"; added an "Effective status" subsection.
- `scripts/README.md` — indexed the new helper + script.

**Live-DB data errors (the agent never edits the DB — these are for the user):**
- **Tilbury Island (T100000131044):** Phase 1b (operating/planned) + Phase 2 (construction/planned) — **user corrected both to `proposed` on 2026-06-07.** ✔ Operating total now 0.28 (Original 0.03 + Phase 1a 0.25), matching GIIGNL 0.3 within rounding.
- **LNG Canada Terminal (T100000130358), Phase 2 (T3-T4), 14 mtpa:** still `operating`/`planned` in the live DB, with NO ConstructionYear/ActualStartYear (never built). **FLAGGED to the user** (qa_review, severity=warning) to correct exactly as Tilbury was. The code now demotes it automatically, so it does not inflate the reconciliation. This is the **only** remaining operating/planned (or construction/planned) unit in the LNG dataset after the Tilbury fix.
- (Benign: Suizhong LNG Terminal Phase 2 is `proposed`/`planned` — already proposed, no effective change.)

## Artifacts

- **Fresh export pulled** 2026-06-07 ~15:52 ET (1,275 unit rows) → `scripts/gem_export.csv` (working file, pristine 115-col).
- **Timestamped snapshot archived:** `data/gem_export_20260607_1857_ET.csv` (117 cols = raw 115 + `EffectiveStatus` + `StatusRuleApplied`; *.csv is gitignored so it's a local archive). 1 row downgraded planned→proposed (LNG Canada T3-T4).
- **Recon rebuilt** on the fresh post-correction export + substatus-aware code:
  - diff regenerated → `batches/staging/recon/giignl2026/giignl_diff.json`
  - Tilbury verdict updated (now "no action — corrected 2026-06-07"); LNG Canada qa_review flag appended (qa_review now 9 entries).
  - workbook: `batches/lng_terminals_batch_20260607_1901_ET_giignl2026_reconciliation.xlsx` — recalc clean.

## Outcome

Tilbury reconciles within rounding; LNG Canada is now a clean 14.0 = 14.0 match instead of a +14 inflation. The planned/actual rule is enforced in code, documented, and produces a backup `EffectiveStatus` column in handoff CSVs. One live-DB correction remains for the user (LNG Canada T3-T4). Git: working tree left dirty for the user to commit (no commit requested).
