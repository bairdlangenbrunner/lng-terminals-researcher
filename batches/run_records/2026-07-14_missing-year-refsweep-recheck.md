# Missing-year ref-sweep — re-check (2026-07-14)

**Workflow:** missing-year ref-sweep (workflows §8 / SOP `docs/sops/ref_sweep.md`)
**Ask:** "redo the missing years analysis and tell me if any are still missing."
**Deliverable:** `batches/deliverables/missing_year_refsweep_20260714_1505_ET.xlsx`
**Staging:** `batches/staging/ref-sweep-missing-year-20260714_1502_ET/`

## Plan
Re-extract every LNG status-timeline entry with `year IS NULL` from the read-only
Postgres and compare to the 2026-07-01 run (148 points → 109 filled / 39 unresolved).

## Status / outcome
Fresh extract returned **6** missing-year points (down from 148) — the user applied
~142 of the previously staged years to the live DB since 2026-07-01. Breakdown of
the 6 that remain:

| st_id | terminal | status | resolution |
|---|---|---|---|
| 41176 | Porto Empedocle LNG Terminal (IT) | shelved `inferred 2 y` | **UNRESOLVED — structural.** New since last run; inferred-dormancy, no datable event (SOP §6). |
| 2718 | Blue Marlin Offshore Port (US) | proposed | **2020** (high) — CORRECTED from prior run's 2019 |
| 2249 | Bluewater Texas T1 (US) | proposed | 2019 (medium) |
| 2250 | Bluewater Texas T2 (US) | proposed | 2019 (medium) |
| 2240 | Sea Port Oil Terminal SPOT (US) | proposed | 2019 (high) |
| 2721 | Texas GulfLink Deepwater Port (US) | proposed | 2019 (high) |

- The 5 US points are all `fuel_type = Oil` — crude-oil export **deepwater ports** in
  projectType=8, not LNG. All were FILLED in the 2026-07-01 run but never applied
  (the user backfilled the LNG points, correctly left the legacy oil rows). Sources
  are federal-register DWPA license-application notices + trade press, re-verified
  2026-07-14 (federalregister.gov PASS).
- **Blue Marlin correction:** prior run staged 2019 from a single tank-storage article
  that now returns HTTP 500. Evidence points to **2020** — MARAD/USCG DWPA application
  received Oct 1 2020 (FR notice 2020-11-05), trade press "proposes development"
  Dec 7 2020. No 2019 public proposal is supported. Corrected to 2020, high tier
  (FR + Tank News International, independent).

## Bottom line
No researchable **LNG** missing-year gap remains — the backfill is effectively
complete. What's left is 1 structural (unsourceable) inferred-shelved point and 5
non-LNG crude-oil deepwater ports (years found/verified, but out of the LNG
backfill lane — apply only if desired).
