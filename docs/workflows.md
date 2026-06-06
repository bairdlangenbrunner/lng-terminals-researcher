# Workflow recipes

Step-by-step command sequences for the workflows routed from `CLAUDE.md`. The methodology doc is authoritative for research rules; the SOPs (`docs/sops/`) are the operational rules; this file is the glue — which commands, in which order. Read the section for the workflow you're running, plus the relevant SOP(s).

**Fresh-pull shorthand used throughout:** `python gem_all_fields.py -o gem_export.csv && python pull_gem_db.py --map-only` → fresh CSV + derived column-index map (`.colmap.json`). No cookies; the cookie-based `gem_export_via_web.py` (wrapped by a bare `python pull_gem_db.py`, auth from `.env`) is the fallback. **Re-derive the colmap on every run** — the schema can drift between GEM database revisions.

**How the workflows fit together.** Triage is the forward-looking chooser — it reads signals and produces a *memo* recommending what to do next. The doers turn a chosen scope into a staging *xlsx*: Update (standard or exhaustive tier — §2), Discovery, and Reconciliation. QC (§6) is the backward-looking checker — it audits the data already in GEM and the edits already applied, produces a *memo*, and routes fixes back into an Update batch ("QC detects, Update fixes" — the same split as Reconciliation→Update). The Regional sweep (§5) is a scaling wrapper that runs Update/Discovery one-subagent-per-country. So: **Triage (memo) → Update / Discovery / Reconciliation (xlsx) → QC (memo → back to Update)**.

**Batch artifact conventions.** Per-batch staging JSON lives under `batches/staging/` — `recon/<report><year>/` for reconciliation batches, `<scope-slug>/` for ad-hoc single-scope batches, `<region>/` for sweeps (see `batches/staging/README.md`). Every xlsx deliverable is named `batches/lng_terminals_batch_<YYYYMMDD>_<HHMM>_ET[_<scope>]_<mode>.xlsx` — the `<mode>` token (`update` / `discovery` / `reconciliation`) is always present; the `<scope>` slug (lowercase, hyphenated: a country, region, or report edition like `giignl2026`) appears whenever the batch is scoped. The name says what it is; only genuinely global batches omit the scope.

## §1 Reconcile against GIIGNL (annual, triggered by report release)

1. Pick the edition from the committed archive in `data/` (every edition 2020–2026 is there — see `data/README.md`); the current target is `data/GIIGNL-2026-Annual-Report-0526b.pdf`. `file <path>` to confirm format (all archived editions are real PDFs v1.4–v1.7 with text layers; a future download could still arrive as the legacy zip-of-JPEGs whose vision pipeline lives in git history). Note the edition year (edition N covers calendar year N−1).
2. Confirm scope per Reconciliation SOP §2 (which GIIGNL tables — terminal-list, capacity-by-country, country-summary; which lifecycle states to include).
3. Fresh pull (shorthand above).
4. `python scripts/giignl_extract.py data/GIIGNL-2026-Annual-Report-0526b.pdf --output batches/staging/recon/giignl2026/giignl_extracted.csv` → flat CSV with GEM-aligned column names per Reconciliation SOP §3 (Appendix A for GIIGNL-specific table parsing). The CSV's `status` column carries any in-table non-op tag ("Bontang Train E (Mothballed)"). (For a non-2026 edition the page/column offsets need re-derivation — see `data/README.md`.) **All of this edition's working artifacts — extracted CSV, diff, prose corrections, narrative findings, staged_*.json — live together in `batches/staging/recon/giignl<YEAR>/`** (§1 commands here are repo-root-relative; agent-authored JSON there is committed as the audit trail, derived artifacts are gitignored).
   4a. **§3.2.1 narrative pass** (agent-driven; default yes): read the narrative pages (2026: liq pp.28-31, regas pp.48-52). Forward-looking findings (proposed/construction/expansion) → Discovery/Update routing. **Operating-status corrections** — where the prose says a train listed *untagged* in the operating table isn't actually operating (Bontang p.31: "only Trains G and H currently in operation" ⇒ Train F idled) — go in an agent-authored `giignl_prose_corrections.json` next to the extracted CSV (i.e. in `batches/staging/recon/giignl<YEAR>/`), which `report_diff.py` auto-applies.
   4b. `python scripts/giignl_fsru_fleet.py data/GIIGNL-2026-Annual-Report-0526b.pdf --output batches/staging/recon/giignl2026/giignl_fsru_fleet.json` → parses the GIIGNL **FSRU fleet table** (2026: PDF p.43, 54 vessels; older editions move it — p.20/p.11/p.23/p.33/p.29/p.43 for 2020–2025, pass `--page`). **Run this BEFORE step 5** — `report_diff.py` auto-discovers it and uses it so a GEM FSRU absent from the country regas tables but present in the fleet table is NOT flagged "report doesn't list it" (Tema LNG / "Torman", Aqaba / "Energos Force"). The build also cross-checks it against GEM's floating-vessel fields in a `giignl_fsru_fleet` sheet, flagging GEM FSRU terminals missing the "FSRU" naming convention + vessel-name / vessel-owner deltas. Auto-discovered beside the diff.
5. `python scripts/report_diff.py --extracted batches/staging/recon/giignl2026/giignl_extracted.csv --report giignl --gem-csv scripts/gem_export.csv --output batches/staging/recon/giignl2026/giignl_diff.json` → three-way diff (matches, GIIGNL-only, GEM-only, value-disagreements). Auto-discovers `giignl_prose_corrections.json` and `giignl_fsru_fleet.json` (from step 4b) beside the extracted CSV (or pass `--prose-corrections` / `--fsru-fleet <path>`); a gem_only FSRU matched in the fleet table is tagged `gem_only_in_fsru_fleet` ("no action — GIIGNL lists it in the fleet table") instead of `gem_only_operating`.
6. Route findings per Reconciliation SOP §4:
   - GIIGNL-only (`report_only`) → **first try to match it to an existing GEM terminal under a different name** before routing to Discovery. Most orphans are name-mismatches, NOT missing terminals (TRSP=Cosan FSRU, GDLNG=Guangdong Dapeng, Caofeidian=Tangshan PetroChina, Kaliningrad=Marshal Vasilevskiy). Compare capacity / owner / location / FSRU vessel against GEM AND web-search the GIIGNL name for an acronym/alias. A confirmed match → author a `staged_report_only_resolutions.json` entry in `batches/staging/recon/giignl<YEAR>/` (`resolution: name_mismatch`, the GEM `terminal_id`, and `suggested_othernames`); the build re-routes the row to "add to OtherNames" and tags the mirror `gem_only` row. Only genuine misses (`resolution: discovery`) go to Discovery.
   - GEM-only → log in `giignl_to_action` sheet, usually no action (GIIGNL has known gaps per the methodology FAQ)
   - Value-disagreement → Update workflow (GIIGNL is one source in a conflict, NOT automatically authoritative — the methodology FAQ says a more specific or current source takes priority)
   - Match → confidence bump on the GEM record
7. **DO NOT auto-apply GIIGNL values to the GEM record.** Every value-disagreement requires resolution through the Update workflow's normal source-search and confidence-labeling process.
8. `python scripts/build_review_package.py --mode reconciliation --report giignl --year <YEAR> --inputs-dir batches/staging/recon/giignl<YEAR> --gem-csv scripts/gem_export.csv --extracted-csv batches/staging/recon/giignl<YEAR>/giignl_extracted.csv --output batches/lng_terminals_batch_<YYYYMMDD>_<HHMM>_ET_giignl<YEAR>_reconciliation.xlsx` → staging xlsx with `giignl_diff_operating`, `giignl_diff_nonoperating`, `giignl_to_action`, and `giignl_fsru_fleet` sheets in addition to the standard sheets. Stamp via `TZ=America/New_York date "+%Y%m%d_%H%M_ET"`.
9. `python scripts/recalc.py batches/lng_terminals_batch_<…>_giignl<YEAR>_reconciliation.xlsx`, then `present_files`.

(A future IGU reconciliation SOP will reuse this workflow body with `igu_extract.py` and `--report igu`.)

## §2 Update existing terminals (most common)

1. Fresh pull (shorthand above).
2. Confirm batch scope per Update SOP §2 — which terminals/countries, **which tier (`standard` default, or `exhaustive` — Update SOP §2.1/§2.2)**, whether [ref]-fill is in scope, whether status updates are in scope.
3. `python dedup_index.py` → builds project/unit indexes per Update SOP §3. **Derive the tier worklist** (Update SOP §11.5): `python stale_sweep.py` (dormancy flags + the `dev_pipeline` block — every proposed/construction/shelved unit, recency-annotated) and `python completeness_sweep.py` (in-scope `blank_ref` fill targets). Standard tier works that worklist; exhaustive works every row in scope.
4. For each terminal in the worklist (standard) or in scope (exhaustive):
   a. Pull the unit-level timeline from the live DB (`python fetch_timeline.py <UnitID>`) if any status changes are anticipated — the export does NOT contain timeline history, only anchor years and current status.
   b. Source-search per Update SOP §4 — using `docs/reference/source_roster.md` for tier selection and `docs/country_notes/` for country-specific tips.
   c. Apply lifecycle state machine per `docs/reference/lifecycle_rules.md` — especially the planned-vs-actual sub-status logic and the "closest non-planned-non-FID status to bottom" rule for deriving current status.
   d. For [ref]-fill: identify blank `[ref]` columns paired with **filled** data values (the equivalent of carrier-project Rule F — no orphan citations).
   e. Stage findings as `staged_*.json` in `../batches/staging/<scope-slug>/` (e.g. `../batches/staging/japan/staged_updates.json`) — the build's `--inputs-dir`. Agent-authored staging there is committed as the audit trail.
5. `python url_verifier.py <url> <expected1> <expected2> ...` on every URL before it goes in the xlsx. Or import as a module — see the script's docstring.
6. `python capacity_normalize.py` on any capacity changes — mtpa/bcm/y/m³ conversions, range handling per methodology ("record max in spreadsheet, range in wiki Background").
7. `python entity_lookup.py "<owner name>" "<country>"` before staging any new owner/operator — the methodology is emphatic about not creating duplicate entities.
8. **If any FSRU terminal is touched**: `python fsru_sync_check.py` — see §7.
9. `python build_review_package.py --mode update --inputs-dir ../batches/staging/<scope-slug> --output ../batches/lng_terminals_batch_<YYYYMMDD>_<HHMM>_ET_<scope>_update.xlsx` → staging xlsx. Stamp via `TZ=America/New_York date "+%Y%m%d_%H%M_ET"`; scope slug per the naming convention above (omit `_<scope>` only for a genuinely global batch).
10. `python recalc.py ../batches/lng_terminals_batch_<YYYYMMDD>_<HHMM>_ET_<scope>_update.xlsx` → confirm zero formula errors.
11. `present_files`.

## §3 Discover new terminals

1. Confirm parameters per Discovery SOP §2 (region/country scope, gap window if any, whether to include early-stage proposals that may not meet the "sufficient information to add" threshold from the methodology FAQ).
2. Fresh pull (shorthand above); `python dedup_index.py` → indexes used for matching candidates against existing records; `python completeness_sweep.py` → its `coverage_gap` block lists coastal countries with ZERO GEM terminals — **add those to the discovery scope** so the run covers `covered ∪ uncovered`, not just countries already in GEM (Discovery SOP §4.0).
3. **Country-level regulatory sweep** — Discovery SOP §4 lists per-country regulators (FERC/DOE for US, EU PCI portal + national TSOs for Europe, METI/JOGMEC for Japan, MOTIE for Korea, CNPC/Sinopec/CNOOC IR for China, etc.). Use `docs/country_notes/` to seed the search and contribute findings back.
4. **Trade press sweep** — per Discovery SOP §5, using `docs/reference/source_roster.md`. LNG Prime, Reuters, S&P Global Commodity Insights, Argus, Upstream are the workhorses.
5. **Sponsor IR sweep** — for known LNG developers (Cheniere, Venture Global, TotalEnergies, Sempra, Adnoc Gas, QatarEnergy, Petronas, NLNG, NextDecade, etc.) — per Discovery SOP §6 and `docs/reference/entity_canonical_map.md`.
6. **Dedup the leads** (Discovery SOP §6): write the gathered leads to a JSON list and run `python dedup_index.py match <candidates.json>` → per-candidate `recommended_route`. Route `update_existing`/`update_dead_and_revived` to the Update workflow (don't stage as new); judge `manual_review` by hand; only `discovery_new` proceeds.
7. For each `discovery_new` candidate: apply the "sufficient information to add" threshold from the methodology FAQ (sponsor identified + approximate location + concrete step taken). Candidates that don't meet the threshold go in a `monitor_list` sheet, not `new_terminals`. Stage findings as `staged_*.json` in `../batches/staging/<scope-slug>/` (the build's `--inputs-dir`).
8. `python url_verifier.py` on all URLs; `python entity_lookup.py` on every new owner/operator/parent.
9. **If any candidate is an FSRU**: `python fsru_sync_check.py` against both the GEM terminals and (if available) the LNG carrier project's backend.
10. **Seed the monitor roll-forward** (Discovery SOP §5): `python monitor_store.py seed ../batches/staging/<scope-slug>` (writes `prior_monitor_list.json` so the build merges the durable watch-list).
11. `python build_review_package.py --mode discovery --inputs-dir ../batches/staging/<scope-slug> --output ../batches/lng_terminals_batch_<YYYYMMDD>_<HHMM>_ET_<scope>_discovery.xlsx` → staging xlsx (Eastern timestamp via `TZ=America/New_York date "+%Y%m%d_%H%M_ET"`; scope slug per the naming convention above).
12. `python recalc.py`; **update the durable store**: `python monitor_store.py update ../batches/staging/<scope-slug> --batch <stamp>` (folds this batch's monitor candidates into `monitor_list/current.json`, drops any promoted to `new_terminals`); then `present_files`.

## §4 Triage (decide what to work on this batch)

1. Fresh pull (shorthand above).
2. `python stale_sweep.py` → for each terminal/unit, compute LastUpdated age and lifecycle-rule-driven flags:
   - Proposed/Construction units with LastUpdated > 12 months → due for refresh
   - Proposed units with no updates > 2 years → candidates for inferred shelved (per methodology)
   - Shelved units with no updates > 4 years → candidates for inferred cancelled (per methodology)
   - Operating units with LastUpdated > 18 months → due for refresh (lower priority than active development)
   - The output also carries a `dev_pipeline` block — EVERY proposed/construction/shelved unit, annotated `recently_updated` (≤3 months) — which is the standard-tier Update worklist (Update SOP §2.1); use its per-country counts to size standard-update options.
3. Pull triage inputs per Triage SOP §3:
   - Stale-sweep results (above)
   - Recent news scan (last quarter) for activity in countries that haven't been touched recently
   - GIIGNL reconciliation backlog (any unprocessed findings from a prior reconciliation batch)
   - User priorities (existing GEM team commitments, upcoming publications)
   - Whether a fresh GIIGNL/IGU report has dropped since the last reconciliation
4. Produce a triage memo (markdown, not xlsx) with recommended batch composition — each option names the workflow and, for Update options, the tier (`standard` or `exhaustive`, Update SOP §2.1/§2.2); a QC pass (§6) is a recommendable option type too. The user decides scope before any batch starts.

## §5 Regional sweep (scaled multi-country Update / Discovery)

The full-tracker pass runs Update (and Discovery) at continental scale by fanning out **one research subagent per country**, then merging per region into one staging workbook. This is the *scaled form* of §2/§3 — the per-country work still obeys every SOP rule. The operational detail and the **live resume ledger** live under `batches/staging/`; **read `batches/staging/README.md` and `batches/staging/SWEEP_PROGRESS.md` first** to resume a sweep in progress.

1. Fresh pull (shorthand above). `python completeness_sweep.py` → field gaps + the `coverage_gap` worklist, so the sweep covers `covered ∪ uncovered` countries (Discovery SOP §4.0), not only those already in GEM.
2. **Per country, dispatch a subagent** that reads `batches/staging/_country_agent_brief.md` (update) or `_discovery_brief.md` (discovery), researches per the relevant SOP **at the tier stated in its dispatch prompt** (default `standard` — worklist-driven; a full re-verification sweep runs `exhaustive` — Update SOP §2.1/§2.2; verify every URL; status changes → qa note while `fetch_timeline` is down), and **writes** `batches/staging/<region>/<slug>.<type>.json` (`updates`/`qa`/`wiki`/`entity`/`monitor`/`newterminals`/`newunits`), returning only a terse summary to keep the main loop's context small.
3. `python batches/staging/_assemble.py <region>` → merges the per-country JSON into `batches/staging/<region>/_build/staged_*.json`.
4. `python scripts/build_review_package.py --mode update --inputs-dir batches/staging/<region>/_build --gem-csv scripts/gem_export.csv --output batches/lng_terminals_batch_<stamp>_<region>_update.xlsx`, then `python scripts/recalc.py <xlsx>`. **If the region produced monitor/new candidates**, also do a `--mode discovery` build bracketed by the monitor roll-forward: `python scripts/monitor_store.py seed batches/staging/<region>/_build` → the discovery build → `python scripts/monitor_store.py update batches/staging/<region>/_build --batch <stamp>` (seeds `prior_monitor_list.json`, then folds the region's monitor candidates into `monitor_list/current.json` and drops any promoted to `new_terminals`).
5. **Checkpoint `SWEEP_PROGRESS.md` after each country/region** so a compaction or rate-limit can resume.

The staging tree (`batches/staging/**`) is committed as the diffable audit trail; only the `*.xlsx` deliverables and the derived `staged_*.json` are gitignored. Durable knowledge graduates out of staging: country findings → `docs/country_notes/`, tooling fixes → `scripts/`, cross-batch monitor state → `monitor_list/`.

## §6 Quality control (QC pass)

Backward-looking data-health audit. Output is a **markdown memo only**; QC stages no edits and produces no xlsx — fixes route to a follow-on Update batch. Full rules in the QC SOP (`docs/sops/qc.md`). The four passes:

1. Fresh pull (shorthand above) — for the post-apply check the pull must postdate the user's apply.
2. **Mechanical integrity** (QC SOP §3.1): `python completeness_sweep.py`, `python stale_sweep.py`, `python dedup_index.py` → blank/orphan refs, missing required fields, enum/consistency defects, dormancy flags + the `dev_pipeline` worklist counts, and project-key collisions (possible duplicate terminals).
3. **Citation link-rot sweep** (QC SOP §3.2): `python citation_qc.py [--country "<C>"] [--status <status>] [--max-urls N]` → re-verifies existing `[ref]` URLs from the export via `url_verifier.py`; writes `work/citation_qc.json`. Verdicts: dead (hard rot) / blocked (bot-wall — verify manually) / name-miss (advisory). **>25% dead in a country → recommend an exhaustive Update there.** Shard big scopes; never report a truncated run as full coverage.
4. **Accuracy spot-check** (QC SOP §3.3, agent-driven): stratified ~20–30 unit sample (recently-edited, high-capacity operating, dev-pipeline); re-verify Status / Capacity / Owner-Operator / start years against the cited refs + one fresh corroboration each. **>10% of sampled cells unsupported → systemic flag, stop and discuss.**
5. **Post-apply check** (QC SOP §3.4): `python apply_check.py --batch ../batches/<applied batch>.xlsx` → classifies each staged edit applied / not_applied / diverged (transcription-error catcher) against the fresh export.
6. Draft the QC memo (QC SOP §2), save to `../batches/qc_<YYYYMMDD>_<HHMM>_ET.md` (stamp via `TZ=America/New_York date "+%Y%m%d_%H%M_ET"`), `present_files`, and **stop and ask** before spinning up any recommended follow-up batch.

## §7 FSRU sync rule (cross-project)

FSRUs are tracked in both the GEM terminals tracker and (if the user is also running it) the LNG carrier project. Each project owns its own fields:

| Field type | Owned by | Examples |
|---|---|---|
| Vessel identity & technical specs | Carriers | IMO, builder, hull, m³ LNG capacity, propulsion, delivery year, vessel owner, vessel operator |
| Terminal identity & operations | Terminals | Country, port, terminal name, sendout capacity (mtpa/bcm), terminal operator, lifecycle status, location, sponsor |
| Linking fields (both records must agree) | Sync rule | Vessel name, IMO |

**Sync rule mechanics:**

1. When a terminals batch adds or updates an FSRU terminal, the FloatingVesselName + (IMO if known) go in the staging xlsx with a sync-touchpoint flag.
2. When a carriers batch updates an FSRU vessel that's deployed, the terminal name + country go in the carrier xlsx with the same flag.
3. `fsru_sync_check.py` diffs both backends on (IMO ↔ terminal name) pairs and surfaces mismatches. Mismatches go in a `fsru_sync` sheet of whichever xlsx is the current deliverable.
4. **Vessel reassignment** (FSRU moves from terminal A to terminal B) is a real and observed pattern — at least one terminal in the export has three FSRUs in sequence. The script handles it by modeling: terminal A's prior FSRU gets an "Idled" or "Retired" status timeline entry on the unit-row; terminal B (or a new unit on terminal A) gets the new FSRU. The carrier record's deployment field updates correspondingly.

Edge cases:
- **FSU / FRU** (floating storage only / floating regas only) — same rule applies.
- **Deepwater Port LNG terminals** (offshore but not floating) — terminals only, no vessel record, no sync needed. The script skips them.

If the user isn't running the carrier project, `fsru_sync_check.py` short-circuits to "skipped — no carrier backend available" and logs the FSRU entries for future cross-check.
