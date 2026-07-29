# 2026-07-28 — Puerto Rico exhaustive update + discovery

## Plan

- User request: "do a full research pass, like you've done for other LNG terminal
  countries, for puerto rico now" → exhaustive-tier Update + full Discovery,
  singapore-thailand pattern (ad-hoc single-scope dir `batches/staging/puerto-rico/`).
- Fresh pull 2026-07-28 22:30 ET (1,274 unit rows, 115 cols, colmap re-derived).
  Scope: 3 terminals — Aguirre GasPort FSRU (cancelled 2019, Excelerate),
  Peñuelas LNG Terminal (operating, EcoEléctrica JV), San Juan LNG Terminal
  (operating, New Fortress Energy). Methodology doc confirmed in context
  ("Last updated: Baird and Rob, May 2026").
- Completeness sweep: 8 blank_ref cells + 2 missing `FloatingVesselName`;
  `dormant_revival_watch` flagged Aguirre (dead 7y, high priority).
  `stale_sweep`: **zero** flagged units and zero dev-pipeline units in Puerto Rico.

## Status

- 2 subagents (PR update, PR discovery — Sonnet) dispatched ~22:35 ET, both complete
  with done markers (pruned after close-out).
- Merge-time QC gate (workflows §5 step 3a) run by orchestrator ~23:00 ET.
- Built 23:04 ET; monitor store rolled forward (38 prior, 0 this batch);
  meta.json `built`/`status` set.

## Outcome

**Deliverables (apply these):**

- `batches/lng_terminals_batch_20260728_2304_ET_puerto-rico_exhaustive_update.xlsx`
  — 26 updates (15 green / 9 yellow / 2 blue), 1 timeline append, 1 entity addition,
  8 qa, 2 wiki. Zero GUARD warnings; recalc clean.
- `batches/lng_terminals_batch_20260728_2304_ET_puerto-rico_discovery.xlsx`
  — 0 new terminals, 0 new units, 0 new monitor candidates, 5 discovery qa.
  Built despite `_assemble.py` reporting `discovery_mode_needed: False` (that flag
  only tracks new/monitor candidates) so the 5 substantive findings land in a
  deliverable rather than only in staging JSON.

**Headline findings:**

- **No status changes anywhere.** All three terminals' statuses re-verified unchanged
  (Peñuelas + San Juan operating, Aguirre cancelled 2019). The bulk of the batch is
  citation work: 17 of 26 records are `[ref]` fills/merges on an exhaustive re-verify.
- **Peñuelas 2.5% owner corrected:** `EcoElectrica LP [2.5%]` → **`OCO Partners [2.5%]`**
  (yellow; GIIGNL 2024/2025/2026 all name OCO Partners; the 2021 edition narrative
  records GE Capital selling that share). GEM had been using the JV itself as a
  placeholder for the unknown minority holder. New entity staged for OCO Partners.
- **Peñuelas `Parent` was a 197.5% cell** — duplicated the Naturgy/ENGIE/Mitsui block
  with *two different* Mitsui entities (`Mitsui Group` E100000134078 and
  `Mitsui & Co Ltd` E100000000651). Deduped to 100%, deliberately keeping
  `unknown [2.5%]` (not OCO Partners) so `Parent` stays in lockstep with
  `Parent GEM Entity ID` = E100000132388, which is GEM's literal "unknown" placeholder.
  Reviewer must re-pick the entity ID in the picker; the two Mitsui entities may
  warrant a tracker-wide merge (qa, medium).
- **San Juan `Offshore`/`Floating` = True CONFIRMED, not wrong.** Orchestrator initially
  pushed the update agent to flip these to False on the strength of GIIGNL "Onshore" +
  no PR vessel in the FSRU fleet table; the agent pushed back with FERC's show-cause
  order (174 FERC ¶61,207, Docket CP20-466) describing an FSU "semi-permanently moored
  at San Juan Harbor". Re-read the 2026 PDF directly: the type cell actually reads
  **"Onshore + FSU"** (wraps across two `pdftotext -layout` lines — the earlier grep
  missed it). GEM's own convention corroborates: across the export the two flags are
  only ever set together (352 True/True, 12 True/blank, 909 blank/blank, **zero
  False/True**). Staged blue with a source note; **the agent was right.**
- **San Juan `PowerPlantsSupplied` = `San Juan Power Plant; Palo Seco Power Plant`**
  (green) — NFEnergia's 15 Mar 2024 NGSPA with PREPA names both as delivery points.
  Cambalache (NEPR docket MI-2024-0004) and Mayagüez (Feb-2025 conditional approval)
  are *pending* and deliberately NOT staged (qa, medium).
- **`FloatingVesselName` unresolved after real research** (qa, high): FERC describes the
  San Juan FSU but never names the vessel. "Coral Encanto" was chased and **rejected** —
  AIS shows it trading in the West Mediterranean as of Nov 2025. Left blank rather than
  guessed.
- **Discovery: zero missing terminals.** Aguirre revival check negative (no new sponsor,
  charter, permit, or renamed project since Nov 2019 — PREPA/Genera's current gas
  conversions are fed by the *existing* San Juan terminal, not a revived offshore
  GasPort). Mayagüez/Yabucoa ship-based import terminals from the 2019 Siemens IRP were
  **rejected by PREB in the 2020 IRP order**; Yabucoa's peakers are being decommissioned
  for a 40 MW battery — scope doubt resolved *before* staging, per the never-stage-with-
  doubt rule. gem.wiki coverage cross-check clean.
- Wiki Background: Peñuelas (Crowley/Naturgy's US-flagged newbuild "American Energy",
  ~130,400 m³, service from March 2025) and San Juan (USACE San Juan Harbor dredging,
  explicitly refusing the trade-press "6× vessel capacity" figure as unverified).

**QC gate results:**

- **field_name validity: 3 defects caught + repaired.** Two records targeted
  **`Offshore [ref]` / `Floating [ref]` — columns that do not exist** in the 115-col
  schema (only `FloatingVesselName [ref]` does); retargeted to the value columns as
  blue re-verifications. One record staged `ProposalYear` = 2013 with `ref_urls` but no
  ref-column record, so the value would have landed **uncited** — inserted a
  `ProposalDate [ref]` record (the schema has no `ProposalYear [ref]`; `ProposalDate`
  is the anchor's ref column) citing the Federal Register CP13-193-000 notice.
  Both defects logged as qa (`schema_limitation`, low).
- Citation scans: 0 gem.wiki/globalenergymonitor, 0 abarrelfull, 0 bare domains, 0
  GEM-derivative sources across 102 URL occurrences (21 distinct). Two IEEFA pieces
  *were read* during the discovery sweep — the disc-qa prose was edited to state
  explicitly that they are search leads only and never citable (IEEFA footnotes GEM).
- Ref merges: `audit_ref_drops.py` → 0 undeclared drops. Both declared-dead URLs
  independently re-confirmed dead (`en.aguirreoffshoregasport.com` HTTP 000,
  lngworldnews HTTP 404). Confirmed the merges preserve prior URLs: Peñuelas
  Status/StartDate IGU → IGU + ccj-online; San Juan Status/StartDate
  utilitydive + spglobal → those two + FERC.
- url_verifier: 8/8 spot-checks PASS with page-matched tokens. GIIGNL capacity tokens
  are inherently weak (bare numbers), so the Peñuelas and San Juan table rows were read
  out of the PDF directly instead of substring-matched.
- Entity re-check: **"OCO Partners" absent from Postgres `entity_history`** (only
  "Sunoco Partners" substring hits) → genuinely new, not a duplicate.
  `entity_lookup.py --remote` had silently returned `skipped_no_base_url`
  (no `GEM_PROJECT_DB_BASE_URL` in the non-interactive shell), so the Postgres check
  was the real gate — as the standing memory says it should be.
- Aguirre status refs correctly downgraded green → **yellow**: offshore-energy.biz and
  lngworldnews are the same publisher network (Navingo — offshore-energy.biz is the
  rebranded lngworldnews), so they are ONE source, not two.
- fsru_sync_check.py: gem_only mode (no carrier backend), graceful skip.

**Process notes / traps hit:**

- **`_assemble.py` is mandatory.** First build pointed `--inputs-dir` at the staging dir
  itself and produced an *empty* workbook (README + giignl_recon only):
  `build_review_package.py` reads only canonical `staged_*.json` filenames, which
  `python batches/staging/_assemble.py <region>` creates from `<slug>.<type>.json`.
  Empty workbook deleted, rebuilt from `_build/`. (Also: `_assemble.py` has no argparse,
  so `--help` created a junk `batches/staging/--help/` dir — removed.)
- **wiki record key schema:** the agent wrote `section`/`content`/`confidence`; the
  schema wants `topic`/`wiki_text`/`verification_status` (an enum, not a colour).
  4 GUARD warnings and an empty wiki sheet. Remapped in both `_build` **and** the
  committed staging source so a rebuild doesn't regress.
- **Global sweep leaked into a scoped `_build`:** the copied `stale_sweep.json` was the
  unscoped global run (15 flagged units across 9 other countries, dev_pipeline 464),
  which would have put out-of-scope units in a Puerto Rico workbook. Filtered to
  Puerto Rico → 0, with an `_orchestrator_note` recording that zero is the real finding.
- `fetch_timeline.py` silently returns zero rows for a `T…` TerminalID (it derives
  `pu_id` from the digits) — use the `G…` UnitID.
