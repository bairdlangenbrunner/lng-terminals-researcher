# 2026-07-17 — missing-year ref-sweep recheck (extract-only)

**Ask:** one more look at all status entries (including FID) for units missing a year.

**Plan:** fresh GEM export pull + fresh `refsweep_missing_year.py extract` against the
read-only Postgres (refresh of the 2026-07-14 run), plus an export-level anchor-year
cross-check.

**Status:** complete — nothing to research or build.

## Outcome

- Fresh pull: 1,272 unit rows (`gem_export.csv`, colmap re-derived, 115 cols).
- `extract` returned **zero** missing-year points ("nothing to extract"; no staging dir
  created). Sanity-checked directly in Postgres: 3,447 non-deleted LNG status-timeline
  rows, **zero with `year IS NULL` across ALL statuses** (not just the tracked nine) —
  the 2026-06-30 / 07-01 / 07-14 sweep backfills have all been applied upstream.
- Export-level anchor-year cross-check (status vs its anchor column + FIDStatus vs
  FIDYear): FID clean (no `FID` status with blank FIDYear). Only two rows lack the
  status-matching anchor year, and both are the known `operating` + `substatus=planned`
  anomaly (effectively proposed — see [[substatus_planned_means_proposed]]), i.e. a
  status-storage issue, not a researchable year gap:
  - LNG Canada Terminal — Phase 2 (T3-T4), unit G100002035803 (already flagged;
    also carries FIDStatus `Pre-FID` with FIDYear `2026` — expected-FID usage?)
  - Tilbury Island LNG Terminal — Phase 1b Expansion, unit G100002104403 (new
    instance of the same class; ConstructionYear 2027 = future/planned)

## Broadened check (user follow-up): every ACTUAL milestone needs its export anchor year

Per user: not just `substatus=planned` — every actual-substatus status entry must have
a year. Verified in two layers:

- **Timeline layer:** every status×substatus combination (incl. FID/actual, all
  confirmed/inferred dormant states) has zero NULL years — fully clean.
- **Export-anchor layer:** joined every actual/confirmed timeline milestone (by
  `pu_id` = digits of GEM UnitID) to its export anchor column
  (proposed→ProposalYear, FID/actual→FIDYear, construction/actual→ConstructionYear,
  operating/actual→ActualStartYear, retired/actual→StopYear,
  shelved→ShelvedYear, cancelled→CancelledYear). **Zero gaps** in all those lanes.

**One systematic gap found — currently-idled units missing `StopYear`:** the schema
(`gem_db_schema.md` col 52) says StopYear covers mothballed/retired/**idled**;
mothballed (15/15) and retired (29/29) rows all have it, but **0 of the 13
currently-idled units do** — while the idled year already sits in the status
timeline for every one of them. The 13 (latest idled year → candidate StopYear):

| Country | Terminal / unit | UnitID | idled year(s) |
|---|---|---|---|
| Argentina | Bahia Blanca GasPort FSRU | G100002053800 | 2018, **2024** |
| Indonesia | Bontang E | G100002027805 | 2019 |
| Indonesia | Bontang F | G100002027806 | 2020 |
| Australia | Darwin LNG T1 | G100002033101 | 2023, **2026** |
| Türkiye | Dörtyol FSRU (MOL FSRU Challenger) | G100002061800 | 2021 |
| Israel | Hadera FSRU | G100002058900 | 2022 |
| Russia | Marshal Vasilevskiy FSRU | G100002083100 | 2022 |
| Kuwait | Mina Al-Ahmadi (Explorer FSRU) | G100002059200 | 2014 |
| United States | Northeast Gateway FSRU | G100002063200 | 2022 |
| Brazil | Terminal Gás Sul FSRU | G100002093800 | 2025 |
| Russia | Vysotsk Expansion | G100001094540 | 2025 |
| Russia | Vysotsk T1 | G100002070801 | 2025 |
| Russia | Vysotsk T2 | G100002070802 | 2025 |

(Historical idled entries on units that later resumed operating are NOT gaps — the
flat export's StopYear describes the current stoppage; the history lives in the
timeline.)

**Follow-up offered:** a small Update batch staging `StopYear` (+ verified
`StopYear [ref]`) for the 13 — years are known from the timeline; refs need the
normal ≥2-independent-source verification.

The two `operating`+`substatus=planned` anomaly rows above remain live-DB status
questions for the user.
