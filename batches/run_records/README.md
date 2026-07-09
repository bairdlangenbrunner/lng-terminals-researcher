# Run records

One dated markdown file per major run — the durable "what was last done, when, and how
it went" log the user checks between sessions. Write one for every substantive batch,
sweep, repair, or process change; small iterative rebuilds within a session don't need
their own.

**Convention:** `YYYY-MM-DD_<slug>_<sub-slug>.md`, containing (in order): the trigger
(what was asked, verbatim where useful), the plan/scope, what actually happened
(including limits hit, bugs found, script changes made), and the outcome (deliverable
filenames, final counts, open follow-ups). A finished sweep's live ledger
(`batches/staging/SWEEP_PROGRESS.md`) is archived here as `<date>_<slug>_ledger.md`.

**Add a line here when you add a record** (newest first).

| Date | Record | Outcome in one line |
|---|---|---|
| 2026-07-02 | [vietnam exhaustive update + discovery](2026-07-02_vietnam_exhaustive-update-and-discovery.md) | Exhaustive-tier update of all 29 Vietnam terminals (141 updates incl. Vung Ang plant-vs-terminal owner correction) + discovery (4 new terminals, 3 monitor) → `_1852_ET_vietnam_exhaustive_update` + `_1854_ET_vietnam_discovery` workbooks; two usage-limit hits recovered by probe/redispatch; remote entity endpoint down → Postgres entity_history fallback |
| 2026-07-02 | [africa sweep](2026-07-02_africa-sweep_standard-update-and-discovery.md) | Standard-tier Africa update + discovery (25 covered + 14 uncovered coastal countries): 36 updates + 1 new terminal (Freetown LNG) + 22 monitor entries → `_1401_ET_africa_update` + `_1402_ET_africa_discovery` workbooks; two usage-limit wipeouts recovered by test-redispatch |
| 2026-07-01 | [ref-sweep refresh](2026-07-01_ref-sweep_refresh.md) | Ref-sweep 3rd pass + `fuel_type` + `build --sync-db`: 148 points → 109 FILLED / 39 UNRESOLVED; deliverable `missing_year_refsweep_20260701_1758_ET.xlsx` |
| 2026-07-01 | [North Pars record repair](2026-07-01_north-pars_record-repair.md) | Untangled the North Pars (Iran) / Qatar North Field two-project chimera flagged from the ref-sweep; staged repair batch for the post-overhaul record |
| 2026-06-30 | [missing-year ref-sweep](2026-06-30_ref-sweep_missing-year-timeline.md) | New workflow: backfill years on status-timeline milestones with none (152 points); first deliverable + SOP + script |
| 2026-06-24 | [africa discovery corrections](2026-06-24_discovery-followup_africa-three-corrections.md) | Three user-flagged discovery errors (Trident Congo FLNG miss, Dar es Salaam over-inclusion, Durban miss) → fixes staged + three permanent blind-spot safeguards |
| 2026-06-24 | [POIC Lahad Datu follow-up](2026-06-24_discovery-followup_poic-lahad-datu-malaysia.md) | Missed Malaysia FSU terminal staged as NEW terminal at a dead site → dormant-revival-watch safeguard added |
| 2026-06-09 | [recon owner fixes](2026-06-09_recon-owner-fixes_giignl2026.md) | Coworker-flagged factual owner errors in the GIIGNL-2026 recon → two parser fixes (paren-balance head-bleed, spaced-slash co-owners) + rebuild |
| 2026-06-08 | [exhaustive dev-pipeline update](2026-06-08_exhaustive-update_dev-pipeline.md) | Exhaustive-tier update of every proposed/construction/shelved unit, region by region (Middle East → Oceania → Africa) |
| 2026-06-07 | [substatus rule](2026-06-07_substatus-rule_status-logic-and-recon-rebuild.md) | "operating/construction + substatus=planned is effectively proposed" rule codified into normalize/report_diff + recon rebuild |
| 2026-06-04 | [full-tracker re-sweep ledger](2026-06-04_full-tracker-resweep_ledger.md) | Archived live ledger: 06-03 morning sweep + 06-03/04 re-sweep + 06-04 re-verify pass; final 12 `_2140_ET` regional workbooks |
| 2026-06-03 | [full-tracker sweep](2026-06-03_full-tracker-sweep_standard-update-and-discovery.md) | First formal full-tracker standard update + discovery sweep, all 6 regions, one subagent per country |
