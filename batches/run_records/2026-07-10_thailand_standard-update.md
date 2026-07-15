# Thailand — standard-tier Update

**Date:** 2026-07-10 (ET)
**Workflow:** Update existing terminals (standard tier) → Discovery, per Workflow router / `docs/workflows.md` §2–§3.
**Scope this run:** Thailand. **Update leg + Discovery leg** (Discovery threshold: **tight**). Mirrors the 2026-07-09 Philippines run.

## Deliverables

- `batches/lng_terminals_batch_20260710_1328_ET_thailand_update.xlsx` (recalc: no formula errors).
  Sheets: README, updates_summary, updates_in_database_format (paste view), status_timeline_additions, qa_review, wiki_updates.
- `batches/lng_terminals_batch_20260710_1329_ET_thailand_discovery.xlsx` (recalc: no formula errors).
  Sheets: README, monitor_list (0 new terminals → only these two sheets).
- Staged inputs committed at `batches/staging/thailand/` (6 `<slug>.research.json` + assembled `staged_*.json`) and `batches/staging/thailand-discovery/` (2 `discovery-*.research.json` + assembled `staged_*.json` + `prior_monitor_list.json`).

## Worklist (standard tier: stale ∪ dev_pipeline ∪ in-scope blank-ref fills)

All 8 Thailand terminals touched (one subagent each on the dev-pipeline/FSRU set; blank-ref fills elsewhere): MTP1(+Expansion), MTP2/Nong Fab, MTP3 (Phase I+II), Surat Thani FSRU, Chana LNG, Gulf of Thailand FSRU, Songkhla FSRU. 32 staged field records / 1 timeline / 2 wiki / 18 qa.

## Outcomes

- **Map Ta Phut LNG Terminal 3, Phase I (G100002089400): proposed → construction (green).** The headline — a confirmed status change, staged not punted (the "never punt" rule): EPCC contract signed **1 Jul 2025** (Gulf MTP LNG Terminal Co, Gulf 70% / PTT Tank 30%) with the PEC-CAZ consortium (POSCO E&C + CAZ); FID reached Apr 2025; THB60bn (~US$1.83bn) investment approved by EGM 24 Jun 2025; land-reclamation substructure done Mar 2025; superstructure start Q4 2025; COD Q1 2029. Status + ConstructionYear 2025 (green) + FIDStatus/FIDYear/Cost/Owner re-verified (blue) + a `construction (actual)` Q4 2025 timeline entry.
- **MTP3 Phase II (G100002089401):** stays **proposed** (blue). Project-wide FID (Apr/Jun 2025) covers the expansion to 10.8 mtpa, but no separate Phase II construction start is stated. No standalone Phase II cost (the THB60bn is the whole-project figure, carried on Phase I).
- **MTP1 / MTP1 Expansion (T100000130321):** re-verified operating, PTT LNG 100%, ~11.5 mtpa (blue). Blank-ref fills on Capacity/FacilityType/Status/Owner/Location; Expansion Capacity 1.5 / Cost yellow (single source).
- **MTP2 / Nong Fab (T100000130322):** re-verified operating, 7.5 mtpa (blue, 3 sources); Cost yellow (single source).
- **Surat Thani FSRU (G100002107100):** stays **shelved (inferred)** — no revival step (no FID / FSRU charter / EIA advance); dropped from Draft PDP 2024; ~2y silence, not >4y → not cancelled. Filled blank ShelvedYear/StopYear [ref] (2025 anchors) with the dormancy evidence.
- **Chana LNG (G100002089300):** stays **cancelled** (blue; strengthened Status [ref] to 2 independent sources). **Fixed a mis-citation:** FacilityType [ref] and Location [ref] both held a bogus DOI (`10.2523/10452-ms`, an unrelated 2005 SPE petroleum-geology paper) — replaced with proper sources; filled the AssociatedTerminals [ref] (Songkhla Chana power station, green, 3 sources) and the previously-blank Location value.
- **Gulf of Thailand FSRU (G100002089600) & Songkhla FSRU (G100002089800):** stay **cancelled** (blue); owner refs re-verified (EGAT / PTT; the egat.co.th owner ref 404s with no Wayback → re-cited to 2 working sources).

## Gate

- Every value-changing citation url_verifier-PASSED in the main loop (MTP3 construction ×3, Chana Location/AssociatedTerminals ×3); subagents verified all others per brief. No gem.wiki / GEM-derived citations.
- No new entities → `staged_entity_additions.json` = []. Build GUARD clean (no URL-in-data-column leaks, no bad ref targets). Normalization: `[ref]`-suffixed research records mapped to base-field + ref_field; FIDStatus routed to `FIDYear [ref]` (no dedicated FIDStatus ref column).
- FSRU sync: `gem_only` mode (no carrier backend). The 3 touched FSRUs are all cancelled/shelved with no chartered vessel → nothing to mismatch.

## Discovery leg (tight threshold)

**Method:** 2 parallel sonnet subagents — rings A+B (ERC/EPPO/DMF/PDP-2024/Gas-Plan + trade press) and rings C+D (sponsor IR + upstream/broader + gem.wiki coverage cross-check); each also ran the dormant-revival watch on all 4 dead Thai sites. Scope gate (marine LNG by ship) applied before the tight threshold.

**Result — 0 new terminals.** Every 2024–2026 lead resolves to an existing record or is out of scope:
- The only new-build in the pipeline is **MTP3** (= "Gulf MTP LNG Terminal") — already roster #3; the Apr–Jul 2025 EPCC/POSCO progress is the Update above, not a Discovery add. (Both agents independently reached this, confirming the Update headline.)
- The ERC **LNG-shipper licences** (Gulf LNG 6.4 mtpa first cargo Jan 2025, Hin Kong/Ratch, B.Grimm, GPSC, Siam Gas) and PTT's **Alaska/Corpus Christi offtakes** are licences / supply contracts, not terminals — they import through the existing Map Ta Phut terminals; the plants they feed are GOGPT (Quang-Trach class). Out of scope.
- No FLNG/export idea (Thailand is a declining Gulf-of-Thailand producer / net importer).

**Dormant-revival:** all 4 dead sites STILL DEAD — Songkhla FSRU (cancelled 2018), Gulf of Thailand/Samut Prakan FSRU (cancelled 2021), Chana (cancelled 2025), Surat Thani FSRU (shelved). The southern-FSRU concept migrated Songkhla → Gulf of Thailand → Surat Thani (each *replaced*, never revived); no different-sponsor new project at any site.

**gem.wiki cross-check:** 7 Thai LNG-terminal pages found, all map 1:1 to the roster → 0 wiki-only (Durban-class) gaps.

**Monitor list (1, below tight threshold):** "Thailand ASEAN LNG re-export / trading hub (aspiration)" — policy vision (PTT/EGAT/Gulf; Bangkok Post, energytracker.asia), no distinct new-build facility (re-export would run through MTP1/2/3). Folded into the durable store `monitor_list/current.json` (26→27; first Thailand entry).

## Open / next

- **Data-health follow-on (route to a future Update):** MTP1 Expansion Capacity/Cost and MTP2 Cost are single-source (yellow); MTP3 Phase II 5.8 mtpa split not independently sourced; a few orphan StartDate refs on never-operated units. The GEM owner spelling "Gulf **MPT** LNG Terminal Co Ltd" is a typo for "Gulf **MTP**" (left unchanged this batch; qa note).
- **Parent rebrand:** Gulf Energy Development → **Gulf Development PCL (2025)** — flagged in qa; apply on a follow-on if GEM's parent field still reads the old name.
- **Cross-tracker:** the Songkhla Chana ~1.7 GW power station and the Surat Thani ~1,400 MW plant are GOGPT matters (both project sides dead); no LNG-side action.
