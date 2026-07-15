# Philippines — standard-tier Update

**Date:** 2026-07-09 (ET)
**Workflow:** Update existing terminals (standard tier) → Discovery, per Workflow router / `docs/workflows.md` §2.
**Scope this run:** Philippines. **Update leg + Discovery leg** (user approved continuing to Discovery after the Update pause). Discovery threshold: **tight**.

## Deliverable

`batches/lng_terminals_batch_20260709_1529_ET_philippines_update.xlsx` (recalc: no formula errors).
Sheets: README, updates_summary, updates_in_database_format (paste view, 7 terminals), status_timeline_additions, qa_review, wiki_updates.
Staged inputs committed at `batches/staging/philippines/` (6 `<slug>.research.json` + `bataan-manila.research.json` + assembled `staged_*.json`).

## Worklist (standard tier: stale ∪ dev_pipeline ∪ in-scope blank-ref fills)

6 dev_pipeline terminals researched (one subagent each, sonnet) + Bataan-Manila blank-ref fill + batch-level orphan-ref data-health note.

## Outcomes

- **Mariveles LNG (G100002030700):** proposed → **shelved (inferred 2 y), ShelvedYear 2024** (real status change; Status+Substatus+ShelvedYear + shelved timeline entry). Newest project news Jan 2024 (PNOC–Samat JV), ~2.5y dormant. Yellow (single non-primary). Scope confirmed in-scope (ship-borne marine import).
- **Filipinas LNG Gateway FSRU (G100002090600):** no confirmed status change; **construction-status doubt reopened** (yellow) — IGU-2024 citation is an inventory table not a construction assertion, GIIGNL 2026 silent; 'operating' ruled out. Capacity 4.4 / Owner re-verified (blue). Vessel left blank (Excelerate Sequoia confirmed in Brazil, not PH). → qa_review ×3 (status doubt, vessel, IGU-2025 [ref] link-rot 404).
- **Quezon LNG (G100002116700):** re-verified unchanged (proposed; Owner EGCO 100% green; ProposalYear 2024). EGCO's Jul 2026 POWER4 omits it. mtpa uncorroborable → qa_review. Ruled out MGen-EGCO JV false lead (that's San Buenaventura coal).
- **Pagbilao Grande Island (G100002030800):** stays shelved (blue). Filled blank Status/ShelvedYear/**StopYear** [ref] (3 independent sources, 2 via Wayback). EWC's Jun 2026 turbine sale to Hallador ($350m, $285m impairment) → wiki Background.
- **Tabangao FSRU (G100002097600):** stays shelved. Resolved the construction/shelved contradiction (both 2024 construction + 2025 operating timeline entries are substatus=planned, never actualized). Strengthened Status [ref] to 2 sources; added ResearcherNotesProject lifecycle note. Vessel blank (never chartered).
- **FGEN Batangas onshore (G100002061000):** blue re-verify. Nov 2025 Prime Infra 60% acquisition applies only to the operating FSRU (already updated 2026-07-02), NOT this shelved onshore permit → ownership split correctly retained. spglobal [ref] bot-block noted (qa_review).
- **Bataan-Manila LNG (G100002030500):** cancelled, unchanged. Filled 4 blank refs (Status/Shelved/Cancelled/Stop) at yellow with 2 independent 2017 dormancy-onset sources (Araneta–PNOC lease stall). Caveat noted: sources predate 2018/2020 anchors, document dormancy not the specific years.

## Gate

- Every staged URL (24 unique) url_verifier-PASSED this batch (subagents; main-loop cross-check confirmed). No gem.wiki / GEM-derived citations.
- No new entities → `staged_entity_additions.json` = []. No URL-in-data-column leaks (build GUARD clean).
- FSRU sync: gem_only mode (no carrier backend); both touched FSRUs have blank vessel names — nothing to mismatch.
- `capacity_normalize` not needed (no capacity changes/ranges).

## Discovery leg (tight threshold)

**Deliverable:** `batches/lng_terminals_batch_20260709_1548_ET_philippines_discovery.xlsx` (recalc: no formula errors). Sheets: README, new_terminals, new_units, entity_additions, monitor_list, qa_review. Staged inputs at `batches/staging/philippines-discovery/` (3 `discovery-*.research.json` + assembled `staged_*.json`).

**Method:** 3 parallel sonnet subagents — (A+B) regulators (DOE/ERC/PNOC) + trade press; (C+D) sponsor IR incl. upstream oil + broader + gem.wiki coverage cross-check; (dormant-revival) all 10 dead/dormant PH sites. Seeded with the 14-terminal covered roster for dedup. Scope gate (marine LNG by ship) applied before the tight sufficiency threshold.

**Result — 1 new terminal staged:**
- **BESTC Bataan FSRU LNG Terminal (NEW, proposed, yellow):** dormant-revival of the cancelled Bataan-Manila LNG / "Energy City" site (linked via `AssociatedTerminals` → T100000130305). Distinct sponsor (BERGS Energy Solutions and Technology Corp / BESTC, new entity) + PNOC (existing), distinct design (FSRU + ~1,800 MW gas CCPP). Concrete step: 10 Feb 2026 PNOC-BESTC 2-year MOU. Yellow = project maturity (exploratory MOU), NOT source weakness — corroborated by PNOC primary + Tribune, both url_verifier-PASS (re-verified in main loop). Capacity/vessel blank (undisclosed). Kept distinct from nearby Mariveles LNG (Samat, T100000130307). Cross-tracker: the 1,800 MW plant → GOGPT (captive-power colocation qa note).

**Nothing else cleared the bar:** all active PH projects (San Miguel/Ilijan, Linseed, AG&P PHLNG, Excelerate/Filipinas, Shell Tabangao, Energy World Pagbilao, Samat/Mariveles, Vires) map 1:1 to the 14 covered (documented duplicates). gem.wiki category = exactly the 14 pages, zero wiki-only gaps. No out-of-scope finds. 9 of 10 dead sites confirmed still dead.

**Monitor list (1, below tight threshold):** unnamed "pre-development" PH terminal proposal (DOE Sec. Garin, Oct 2025 — no sponsor/site/step); the two agents' variants merged. Folded into the durable monitor store (`monitor_list/current.json`, 25→26; first PH entry).

**Gate:** both new-terminal URLs url_verifier-PASS (main-loop re-verified). BESTC = genuinely new entity (bare + --remote, local + remote both empty); PNOC reused. No URL-in-data leaks (build GUARD clean). No FSRU vessel named → nothing to sync.

## Open / next

- Data-health follow-on (route to a future Update): 12 PH terminals carry orphan `StartDate [ref]` (Rule F); off-worklist cancelled ones (Atimonan, PNOC Batangas, Vires, Tanglawan) untouched this batch.
- **Update-territory finding (not staged this batch):** the ~$3.3bn Meralco PowerGen / Aboitiz Power / San Miguel Global Power JV acquiring the AG&P/Linseed Ilijan terminal ("Philippines LNG Terminal", operating) is an ownership change on a covered terminal — route to a follow-on Update.
- **Cross-tracker handoff:** BESTC's ~1,800 MW Bataan gas CCPP → GOGPT / captive-power colocation matcher (qa_review note in the discovery workbook).
