# 2026-07-02 — Africa regional sweep (standard update + discovery)

## Plan

User request: "run the update and discovery for Africa" — regional sweep (workflows §5),
**standard tier**, two workbooks (`_africa_update` + `_africa_discovery`). Scope: all 25
GEM-covered Africa countries (Egypt excluded — swept with `middleeast`) + 14 uncovered
coastal countries from `completeness_sweep.py`'s `coverage_gap` block. June-2026 africa
staging (already applied by the user — visible in the fresh export) archived to
`batches/staging/africa/_archive_pre20260702/` so `_assemble.py` couldn't re-merge it.

## Outcome

**Deliverables (user to review + apply manually):**

- `batches/lng_terminals_batch_20260702_1401_ET_africa_update.xlsx` — 36 staged updates,
  92 qa_review items, 8 wiki updates, 22 monitor entries, 1 entity addition. Recalc clean.
- `batches/lng_terminals_batch_20260702_1402_ET_africa_discovery.xlsx` — 1 new terminal
  (Freetown LNG, Sierra Leone) + 1 new unit, 22 monitor entries, same qa/wiki/entity
  sheets. Recalc clean. Monitor store updated (22 durable entries, batch 20260702_1402_ET).

**Update-wave headlines:**

- Mozambique richest country: Coral North capacity 3.4→3.6 mtpa + ownership (Eni 50%,
  ExxonMobil out); Rovuma start 2027→2030; Mozambique LNG force majeure lifted Nov 2025 →
  shelved→construction routed as `status_timeline` qa (fetch_timeline endpoint down);
  Coral North proposed→construction qa.
- Botswana Serowe: 4 green edits (start→2027, FID H2 2026).
- Nigeria: NLNG Train 7 at 92%; OKLNG revival confirmed by NNPC (stays proposed).
- Mauritania: BirAllah abandoned by TotalEnergies. Gabon: Cap Lopez FLNG startup watch.
- Most blank-ref targets region-wide were GEM-inferred statuses → correctly left unfilled
  with qa notes rather than manufactured refs.

**Discovery-wave headlines:**

- ONE new terminal staged: Freetown LNG Terminal, Sierra Leone (CECASL/AG&P, DFC-backed,
  MoU 25 Jun 2025).
- Banga Kayo (Wing Wah, Republic of the Congo) demoted to monitor — no ship-export
  evidence yet (scope gate, not staged-with-doubt).
- EG-27/Ebano LNG HoA (possible Fortuna revival); Namibia ×3 monitor (Helios/NMPP Walvis
  Bay revival, Lüderitz Angra Point, Orange Basin FLNG); Yakaar-Teranga revival routed to
  Update qa; Dangote LNG + UTM FLNG-2 monitored.
- Wiki-only pages correctly rejected: Gassi Touil = Arzew duplicate; Tendrara, Greenville,
  Virginia = domestic-only out-of-scope. Olokola coords plot ~400 km east of the actual
  site (qa item).

**Escalation items for the user (flagged in qa/entity sheets, none blocking):**

1. XRG (ADNOC subsidiary, 10% Coral North) missing from the GEM entity system.
2. CECA SL entity reuse-vs-create: staged "CEC Africa (Sierra Leone) Limited" has a
   Postgres near-match "CECA SL Generation" (entity id 100000002571, active) — same
   corporate family; reviewer decision annotated in the entity_additions sheet.
3. CI-GNL (Côte d'Ivoire) owner field possibly stale (Total exit 2021) — not independently
   verifiable; qa note only.
4. `entity_lookup.py --remote` is BROKEN: `DEFAULT_BASE_URL` is the stale
   `internal-project-db-host` host (same dead host as `fetch_timeline.py`), so remote
   returns `no_remote_match` for everything. Read-only Postgres `company` table (86k rows)
   is the working alternative for entity-system checks.

**Process notes:** BOTH agent waves were wiped by account usage limits before writing
anything; both "resets at" messages proved stale within minutes. Fix both times:
test-redispatch one group synchronously (U4, then D6), fan out the rest on success.
25/25 update + 39/39 discovery done markers verified against the worklist roster before
build; markers deleted after archive per staging README lifecycle.

---

# Archived ledger (verbatim)

## Sweep: Africa update + discovery — started 2026-07-02

- **Scope:** whole Africa region — 25 GEM-covered countries (Egypt EXCLUDED — it belongs to the
  `middleeast` region roster, swept there) + 14 uncovered coastal countries from `coverage_gap`
  (cape verde, comoros, dr congo, eritrea, gambia, guinea-bissau, liberia, madagascar,
  sao tome and principe, seychelles, sierra leone, somalia, togo, tunisia).
- **Tier:** `standard` (user said "update and discovery for Africa"; no exhaustive request).
- **Fresh export:** pulled 2026-07-02 09:48 ET — 1,288 unit rows, 115 cols, colmap re-derived.
- **Methodology doc:** confirmed in context, "Last updated: Baird and Rob, May 2026". SOPs update rev 2 / discovery rev 2.
- **Prior africa staging:** the June-2026 sweep + follow-up files were MOVED (not deleted) to
  `batches/staging/africa/_archive_pre20260702/` so `_assemble.py` can't re-merge already-applied
  June findings into this batch. (The user's apply is visible in the fresh export — e.g. Durban is
  now a GEM row, LastUpdated 2026-06-22.)
- **Worklists:** per-country `batches/staging/africa/_worklists/<slug>.json`
  (gem_rows, dev_pipeline, stale_flags, blank_refs, other_gaps, dormant_revival_watch).
  Region totals: 51 dev-pipeline units, 3 stale flags, 74 blank-ref targets, 25 dormant sites.
- **fetch_timeline.py is DOWN** — status changes route to qa notes (category `status_timeline`), per the brief.

## Status table

| Wave | Group | Countries | Status |
|---|---|---|---|
| update | U1 | nigeria | DONE (1/1 marker) |
| update | U2 | mozambique | DONE (1/1 marker) |
| update | U3 | south-africa, namibia, botswana | DONE (3/3 markers) |
| update | U4 | algeria, libya, morocco, western-sahara | DONE (4/4 markers) |
| update | U5 | senegal, mauritania, guinea | DONE (3/3 markers) |
| update | U6 | ghana, cote-divoire, benin | DONE (3/3 markers) |
| update | U7 | cameroon, equatorial-guinea, gabon, republic-of-the-congo | DONE (4/4 markers) |
| update | U8 | angola, kenya, tanzania, djibouti, sudan, mauritius | DONE (6/6 markers) |
| discovery | D1 | nigeria | DONE (1/1 disc marker) |
| discovery | D2 | mozambique, madagascar, comoros | DONE (3/3 disc markers) |
| discovery | D3 | south-africa, namibia, botswana | DONE (3/3 disc markers) |
| discovery | D4 | algeria, libya, morocco, western-sahara, tunisia | DONE (5/5 disc markers) |
| discovery | D5 | senegal, mauritania, guinea, gambia, guinea-bissau, cape-verde, sierra-leone, liberia | DONE (8/8 disc markers) |
| discovery | D6 | ghana, cote-divoire, benin, togo | DONE (4/4 disc markers) |
| discovery | D7 | cameroon, equatorial-guinea, gabon, republic-of-the-congo, democratic-republic-of-the-congo, sao-tome-and-principe | DONE (6/6 disc markers) |
| discovery | D8 | angola, kenya, tanzania, djibouti, sudan, mauritius, somalia, eritrea, seychelles | DONE (9/9 disc markers) |

Build steps (after both waves): fsru_sync_check → `_assemble.py africa` → `--mode update` build →
recalc → monitor_store seed → `--mode discovery` build → recalc → monitor_store update → run record.

## Run log

- 2026-07-02 ~09:45 ET — fresh pull, dedup_index, stale_sweep, completeness_sweep run; worklists written.
- 2026-07-02 ~10:00 ET — June staging archived to `_archive_pre20260702/`; update wave dispatched.
- 2026-07-02 ~09:55 ET — ALL 8 update agents killed by account usage limit before writing anything
  (staging dir empty; the "resets 1:30pm" message proved stale).
- 2026-07-02 ~10:02 ET — test-redispatch of U4 (Maghreb) SUCCEEDED — 4/4 done markers, Nador FSRU
  blue re-verify staged. Remaining 7 update groups re-dispatched concurrently ~10:05 ET.
- 2026-07-02 ~10:20 ET — UPDATE WAVE COMPLETE: 25/25 done markers verified against the worklist
  roster. Headlines: Mozambique (6 edits; Moz LNG FM lifted → construction qa, Coral North FID/
  capacity/owner), Botswana Serowe (4 edits, start→2027), Nigeria (T7 92%, OKLNG revival confirmed),
  BirAllah abandoned by Total, Cap Lopez startup watch. XRG entity missing from GEM (qa, user call).
  Discovery wave dispatched ~10:22 ET.
- 2026-07-02 ~10:30 ET — ALL 8 discovery agents killed by a SECOND usage limit (said resets 2:50pm),
  nothing written. Test-redispatch of D6 succeeded again (~10:45 ET): 4/4 disc markers, 0 new
  terminals, 4 monitor entries (World Bank PRIME-GAS Lomé + Benin compact FSRU the live story).
  Remaining 7 discovery groups re-dispatched ~10:50 ET.
- 2026-07-02 ~13:55 ET — DISCOVERY WAVE COMPLETE: 39/39 disc done markers verified (25 covered +
  14 uncovered coastal). ONE new terminal staged: Freetown LNG Terminal, Sierra Leone (CECASL/AG&P,
  DFC-backed, MoU 25 Jun 2025) + 22 monitor entries. Notables: Banga Kayo (Wing Wah, Congo) demoted
  to monitor (no ship-export evidence — scope call); EG-27/Ebano LNG HoA (possible Fortuna revival);
  Namibia ×3 monitor (Walvis Bay revival, Lüderitz Angra Point, Orange Basin FLNG); Yakaar-Teranga
  revival routed to Update qa; Dangote LNG + UTM FLNG-2 monitor. Wiki-only pages correctly rejected
  (Gassi Touil = Arzew duplicate; Tendrara/Greenville/Virginia = domestic out-of-scope). Olokola
  coords ~400 km off (qa). Sierra-leone entity staging ANNOTATED with Postgres near-match
  CECA SL Generation (id 100000002571) — reviewer reuse-vs-create decision surfaced in the workbook.
  entity_lookup.py --remote confirmed BROKEN (stale internal-project-db-host host, same as
  fetch_timeline.py) — read-only Postgres `company` table used instead.
- 2026-07-02 ~14:02 ET — BUILD COMPLETE: fsru_sync_check (gem_only, 337 FSRUs, carrier backend
  absent → graceful skip) → _assemble.py africa (updates 36, qa 92, wiki 8, entity 1, monitor 22,
  newterminals 1, newunits 1, scope_terminals 20) →
  `batches/lng_terminals_batch_20260702_1401_ET_africa_update.xlsx` (recalc OK) → monitor seed (0
  prior) → `batches/lng_terminals_batch_20260702_1402_ET_africa_discovery.xlsx` (recalc OK) →
  monitor store update (22 durable entries, batch 20260702_1402_ET). Ledger archived to
  `batches/run_records/2026-07-02_africa-sweep_standard-update-and-discovery.md`; done markers deleted.

## Resume recipe (cold session)

1. Done markers are authoritative: `ls batches/staging/africa/*.done.json` — update agents write
   `<slug>.done.json`, discovery agents `<slug>.disc.done.json`. A country without its marker was
   never finished → re-dispatch just that group (briefs: `_country_agent_brief.md` /
   `_discovery_brief.md`; worklists in `_worklists/`; region `africa`; tier standard).
2. When all markers present: run the build steps above (commands in `batches/staging/README.md`).
3. Do NOT re-merge `_archive_pre20260702/` — it is the June batch, already applied by the user.
