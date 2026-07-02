# 2026-07-01 — Missing-year ref-sweep refresh (3rd pass + fuel_type + sync-db)

**Trigger:** User asked to review the whole ref-sweep process, refresh the xlsx with
recent information (research sessions had been killed a few times), and add a
`fuel_type` column so oil/NGL/etc. legacy terminals can be sorted apart.

**Deliverable:** `batches/deliverables/missing_year_refsweep_20260701_1758_ET.xlsx`
(supersedes `missing_year_refsweep_20260630_1146_ET.xlsx`).
Staging: `batches/staging/ref-sweep-missing-year-20260701_1724_ET/`.

## Kill-damage audit (came back clean)

Checked every first-pass shard result against its input shard, plus all FILLED rows
for missing refs/years/notes: **no residual damage** from the killed sessions — the
one known casualty (a Bontang contract slip) had already been patched in the p2
overlay. So "needs another pass" reduced to exactly the 12 researchable UNRESOLVED.

## Script changes (`scripts/refsweep_missing_year.py`)

- **`fuel_type` column** — new in extract (`lng_unit.fuel` via `lu.unit_id = pu.id`;
  the `unit_fuel` M2M is empty for LNG units) and **re-derived fresh from the DB at
  build time by `pu_id`** (same principle as `tl_order`), so pre-existing shards
  backfill automatically. Sits after `unit` in the output.
- **`build --sync-db`** — prunes points that left the extract scope in the live DB,
  printing each drop: st_id deleted / **plant-or-unit deleted** / year backfilled /
  status now untracked. The plant-deleted case was added mid-run: the first build
  kept IMTT St. Rose (st 2777) and Phillips 66 Beaumont (st 2781) because their
  timeline rows still exist with NULL years — the plants themselves were deleted
  upstream. `fetch_orders` now joins through unit→plant and returns deleted+status.
  Default **off** so historical staging dirs rebuild as-was (regression: the
  2026-06-30 dir still builds 152 rows, 109 FILLED 50/24/35, 43 UNRESOLVED).
- Refresh recipe documented as SOP §3.5: new extract dir + copy prior results in +
  refresh identity fields by st_id + `p3_*` overlays (sort after `p2_*`, so newest
  wins) + `build --sync-db`.

## DB drift captured (2026-06-30 → 07-01)

- **Dropped 5:** st 1787 North Pars T1-T4 FID (timeline row deleted in the researcher's
  overhaul — see `2026-07-01_north-pars_record-repair.md`); st 3116 Atimonan
  (year 2023 applied upstream) and st 3737 Battery Rock (2005 applied) — two sweep
  backfills already landed; st 2777 IMTT St. Rose + st 2781 Phillips 66 Beaumont
  (legacy oil terminals **plant-deleted** upstream).
- **Added 1:** st 41121 PAWA PNG FSRU cancelled/`inferred 4 y` — structural
  UNRESOLVED (no real dated event; Ref-sweep SOP §6), authored directly.
- Also: 84 units renamed `(default)` → `--` upstream (identity fields refreshed
  from the fresh extract when copying prior results).

## Third pass on the 12 researchable UNRESOLVED (4 parallel agents)

**5 newly FILLED** (all URLs url_verifier PASS, re-verified by the orchestrator):

- **Cameron LNG Import Terminal, mothballed → 2012** (medium): EIA point-of-entry
  series — last import cargoes Jan–Feb 2012, zero thereafter; no formal FERC/DOE
  suspension exists, so the year = last-receipts/de-facto mothball.
- **Bontang Train A, retired → 2013** (medium): Badak LNG's own milestone page via
  Wayback ("2013 January 14 — Long Term Idle (LTI) of Train A") — also the source
  behind Wikipedia's misread "2011".
- **Bontang Train F, idled → 2020** (high): Bloomberg Technoz (president-director
  quote "terakhir beroperasi pada 2020") + Sindonews, independent, Indonesian.
- **Jaigarh Phase II, proposed → 2016** (medium): DNV GL QRA on the MoEFCC EC portal
  + Wayback H-Energy west-coast page — dates the FSRU-first re-phasing that made the
  8 mtpa onshore terminal "Phase II" (caveat in notes: the onshore config was the
  original 2014 proposal).
- **Dunkirk Ammonia Import Terminal, proposed → 2023** (high): EU PCI/PMI list
  adopted 2023-11-28 ("Ammonia reception facility Dunkerque", promoter Dunkerque
  LNG) + Banque des Territoires coverage.

**7 stay UNRESOLVED, notes substantially upgraded** (each now a crisp data-team
brief): Bontang B (operator's own history logs no B shutdown; bound 2013–2018),
Bontang E (rotating "siaga" standby train — a single idle-year is not defined),
Kakinada construction (ECPL's own May-2021 EC compliance letter says construction
"yet to start" → the `construction` status itself deserves review), Valero East
Corpus Christi operating-start (pre-1962 Sinclair-era startup not web-verifiable;
corrected a CITGO-1935 lineage red herring), Fos Cavaou Expansion 2 (no works
kickoff exists; "construction" traces to one IGU 2025 row contradicted by
Elengy/CRE/GIIGNL-2026 → re-verify status), Puerto Brisa Phase 1 and FGEN Batangas
(both `retired`+`substatus=planned` placeholders — flag the contradictory pattern,
no year to find).

## Final counts

148 points → **FILLED 109 (high 49 / medium 26 / low 34), UNRESOLVED 39**.
fuel_type: LNG 112 / Oil 25 / NGL 5 / NH3 3 / LH2 1 / Oil+NGL 1 / Oil+Fuels 1.

Docs updated: `docs/sops/ref_sweep.md` (rev 2 — fuel_type, `--sync-db`, §3.5
refresh recipe), `docs/workflows.md` §8, `scripts/README.md`,
`batches/deliverables/README.md`.
