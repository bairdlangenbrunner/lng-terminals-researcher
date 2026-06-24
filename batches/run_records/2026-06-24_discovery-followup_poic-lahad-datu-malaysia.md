# 2026-06-24 — Discovery follow-up: POIC Lahad Datu LNG Terminal (Malaysia)

**Trigger:** User flagged a terminal missed in the 2026-06 Asia discovery sweep —
`https://energy-analytics-institute.org/2026/05/26/lng-alliance-and-gob-and-to-develop-fsu-based-lng-import-terminal-in-malaysia/`

## Plan
Verify the project, decide new-terminal vs revive-existing, stage it into the existing
Asia discovery batch, rebuild + recalc the workbook.

## What it is
FSU-based LNG **import** terminal at **POIC (Palm Oil Industrial Cluster) Lahad Datu, Sabah, Malaysia**.
- Sponsors: **Green Oscasaba Sdn Bhd (GOSB)** — local developer, holds Sabah state govt approval + key regulatory permits — and **LNG Alliance Pte Ltd** (Singapore), strategic co-developer providing a 135,000-cbm LNG FSU + long-term US-sourced LNG supply.
- Design: LNG FSU at a mooring jetty + onshore modular regasification, plus LNG truck loading + fueling stations. Phased: initial **0.6 mtpa → 1.2 mtpa** total.
- Status: **proposed**, ProposalYear 2026 (announced 2026-05-26).

## Key decision — dead-and-revived vs new
Co-located with GEM-cancelled **Lahad Datu Sabah LNG Terminal** (`T100000130287`; Petronas 80% + Sabah Energy 20%; onshore terminal feeding a 300 MW CCGT; **cancelled 2016**).
- `dedup_index.py match` → `update_dead_and_revived` (score 0.749, 0.0 km, revived flag).
- **Overridden** per `docs/reference/lifecycle_rules.md` "Dead-and-revived": *significantly different proposal* (different sponsor, different design — FSU vs onshore, 10-yr gap) → **create a NEW terminal; old record stays cancelled.** Discovery SOP §6.6 (matcher is a gate, not an oracle) + §12 (5+ yr cancellation may be a new project at the same site) both support this. `AssociatedTerminals=T100000130287` links the two.
- Threshold (SOP §3): sponsor ✓ location ✓ concrete step (state approval + permits) ✓ — all met.

## Verification
- `url_verifier.py` **PASS** on both URLs for every asserted value:
  - LNG Prime (`/lng-alliance-in-malaysian-move/187960/`): Lahad Datu / Green Oscasaba / LNG Alliance / Malaysia / 1.2 / 0.6 / FSU / 135,000.
  - Energy Analytics Institute (user link): Lahad Datu / LNG Alliance / Malaysia / 0.6.
- Two **independent** publishers → green-grade corroboration. No gem.wiki / GEM-derivative citations.
- `entity_lookup.py` (local + `--remote`; auth env vars `GEM_PROJECT_DB_SESSIONID`/`CSRFTOKEN` were set this session):
  - **LNG Alliance Pte Ltd — ALREADY IN GEM.** Owner/operator of the shelved `LNG Alliance Mangalore FSRU` (India, `T100000131054`). **Reuse the existing entity ID** (likely `E100002005163`, the Singapore-HQ ID on that row — confirm in the entity system); do NOT create a duplicate. (An earlier local lookup with `--country Singapore` falsely returned not-found because the country filter excluded the India terminal — corrected.)
  - **Green Oscasaba Sdn Bhd — NEW.** Local + remote both no-match → staged in `entity_additions`.
- FSU vessel not yet named → `Floating=TRUE`, `FloatingVesselName` blank; FSRU/FSU sync **N/A** until a vessel is identified.

## Why it was missed (genuine miss, not timing)
Both sources were live well before the sweep: Energy Analytics Institute 2026-05-26, **LNG Prime 2026-05-29** — i.e. ~6-9 days before the 2026-06-04 Asia discovery sweep ran. LNG Prime is a Ring B trade-press workhorse the sweep is supposed to cover, so this was reachable. The June-4 Malaysia agent did engage Sabah (it wrote a `monitor_list` note on a broad "Sabah LNG hub" political aspiration and name-checked the cancelled Lahad Datu terminal) but its trade-press queries surfaced the large peninsular projects (RGT Yan/Pulau Bunting, Lumut, Kemaman) and treated Sabah only through that political lens — never catching the specific LNG Alliance/GOSB POIC deal. Exact queries aren't reconstructable (per-agent search logs aren't committed).

## Outputs
- Committed source: `batches/staging/asia/malaysia.disc.newterminals.json`, `batches/staging/asia/malaysia.disc.entity.json`
- Re-assembled `asia/_build` (new_terminals 2→3; entity_additions: +1 net = Green Oscasaba only, since LNG Alliance is an existing GEM entity; Bali + Cong Thanh preserved). Note: re-assemble also refreshed the stale 06-04 `_build` from all committed per-country source files (incl. india/vietnam entity files).
- Workbook: **`batches/lng_terminals_batch_20260624_1140_ET_asia_discovery.xlsx`** — recalc OK, 0 formula errors. Row colors: data cells green, TerminalName yellow (constructed name). (An earlier `1133` build was superseded/removed — it had staged LNG Alliance as a duplicate entity before the `--remote` check corrected that.)

## Safeguards added (so the next sweep catches this class)
Two errors in this follow-up — (a) the dead site at POIC Lahad Datu was never revival-checked, and (b) the
`--country` entity lookup falsely reported LNG Alliance as new — were each hardened against:

**A. Dormant-revival watch (catches a new project at a dead GEM site).**
- `scripts/completeness_sweep.py` — new `compute_dormant_revival_watch()` + a `dormant_revival_watch` block in
  the JSON/CLI output: every wholly cancelled/shelved in-scope terminal, priority-ranked by years-dead
  (`high` = dead 5+ y), as a Discovery revival-check worklist. The cancelled Lahad Datu site (T100000130287)
  now sits at the top of the Malaysia list (`high`, 10 y). New flags: `--no-dormant-watch`, `--today`.
- Wired into Discovery SOP §4.0a (+ §10/§11), QC SOP §3.1/§5, CLAUDE.md routing note, `docs/workflows.md`
  §3 + §5 (regional sweep), `scripts/README.md`, `sop_pointers.md`, and the discovery subagent brief
  (`batches/staging/_discovery_brief.md` Method step 1). Also FIXED the briefs' over-routing that called ALL
  `update_dead_and_revived` an Update (not a discovery) — corrected to the lifecycle dead-and-revived branch
  (same fundamentals → Update; different sponsor/design → NEW terminal).

**B. entity_lookup `--country` false-negative (catches the duplicate-entity trap).**
- `scripts/entity_lookup.py` — `lookup_local()` now ALWAYS scans every row; `--country` only annotates
  (in-country vs. elsewhere) and emits a loud `cross_country_warning` when matches exist only outside the
  filter, instead of returning a false `not_found`. Verified: `"LNG Alliance" --country Singapore` now returns
  `found` + warning (was `not_found`).
- Mandated bare + `--remote` lookups in Update SOP §8, Discovery SOP §9/§11, CLAUDE.md hard requirement,
  `docs/workflows.md` (§1/§2/§3), `scripts/README.md`, `sop_pointers.md`, and BOTH dispatch briefs
  (`_discovery_brief.md`, `_country_agent_brief.md`) — which previously hard-coded the `--country` form.

No workbook rebuild needed (doc/script-only). Verified: both scripts import cleanly, full `completeness_sweep`
run emits both blind-spot blocks, `sweep_worklist_split.py` (the only JSON consumer) unaffected by the additive key.

## Caveats / open items
- Built against existing `data/gem_export_20260607_1857_ET.csv` (no fresh pull) — targeted append to the 2026-06 Asia discovery batch, and the only GEM record it interacts with (`T100000130287`) is immutably cancelled-2016. Re-pull if a full fresh batch is preferred.
- `monitor_store` seed/update intentionally NOT run (no monitor-list change from this addition).
- The pre-existing `malaysia.disc.monitor.json` "Sabah LNG hub" watch entry is a *different*, broader political aspiration — left as-is.
