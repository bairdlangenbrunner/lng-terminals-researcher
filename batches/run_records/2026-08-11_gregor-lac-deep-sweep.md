# 2026-08-11 — deep sweep + discovery, Gregor's Latin America & Caribbean roster

**Workflow:** Regional sweep (`docs/workflows.md` §5) = exhaustive-tier **Update** (Update SOP §2.2)
+ **Discovery** (Discovery SOP), one research subagent per country/cluster.
**Scope slug:** `gregor-lac` — ledger at `batches/staging/gregor-lac/meta.json`.
**Purpose:** package a hand-off deliverable for Gregor Clark, whose roster in the LNG
country-assignments sheet is "Latin America & the Caribbean".

## Scope

21 assigned countries: Antigua and Barbuda, Argentina, Aruba, Bahamas, Brazil, Chile, Dominican
Republic, Ecuador, El Salvador, Guyana, Haiti, Honduras, Jamaica, Mexico, Nicaragua, Panama, Peru,
Suriname, Trinidad and Tobago, Uruguay, Venezuela. **Colombia (Amalia's) and Puerto Rico (Baird's)
are in the same subregion but not on Gregor's roster — excluded.**

Baseline **106 unit rows / 87 terminals**. Discovery scope = `covered ∪ uncovered` (Discovery SOP
§4.0), adding the 13 LAC coastal countries with zero GEM terminals: Barbados, Belize, Bermuda, Costa
Rica, Cuba, Curacao, Dominica, Falkland Islands, Grenada, Guatemala, Saint Kitts and Nevis, Saint
Lucia, Saint Vincent and the Grenadines. 34 countries total in `_build/checked_roster.json`.

Prior coverage was `americas/standard` on 2026-06-04, never re-swept, so an exhaustive pass is
non-duplicative; the 2026-07/08 captive-power passes are a narrower different workflow and do not
refresh general coverage.

## Dispatch

- **Wave 1 — update:** 14 agents / 23 shards. Brazil sharded `brazil_0_north` / `brazil_1_south`,
  Mexico `mexico_0_pacific` / `mexico_1_gulf`. Shard completeness verified only after normalising a
  **non-breaking space (U+00A0)** in the live-DB `State/Province` cell (`São\xa0Paulo` on *Cosan
  FSRU* and *Santos Basin FLNG Terminal*) — staged as a qa item.
- **Wave 2 — discovery:** 8 clusters (`caribbean-gap`, `centralamerica-southatlantic-gap`, `brazil`,
  `mexico`, `southern-cone`, `andean-guianas`, `centralamerica`, `caribbean`).

## Outcome

Deliverables (both built from `_build/staged_*.json` at stamp `20260811_1631_ET`, zero `GUARD:` /
`REF-DROP:` warnings, both clean under `recalc.py`):

- `batches/lng_terminals_batch_20260811_1631_ET_gregor-lac_exhaustive_update.xlsx`
  — updates_summary **332** (204 `[ref]` records, 128 value records, 4 staged deletions) across
  **79 of 87 terminals**; updates_in_database_format 94; status_timeline_additions 9;
  qa_review **137**; wiki_updates 15.
- `batches/lng_terminals_batch_20260811_1631_ET_gregor-lac_discovery.xlsx`
  — new_terminals **1** (Woodbourne LNG Terminal, Barbados — import, operating, Barbados National
  Oil Company); monitor_list **8** new; qa_review 47.

The 8 terminals with no staged edit all carry qa/wiki findings instead (Cosan, Hidrovias do Brasil,
Porto Norte Fluminense, Tepor Macaé, Tergás Rio Grande, Nimofast Antonina, New Fortress Altamira,
Eni/Repsol Perla) — coverage is 87/87 researched.

## Escalations carried into the hand-off (6 high-severity qa items)

- **New Fortress Altamira** (all 5 units) — NFE's 2026 BrazilCo/CoreCo scheme-of-arrangement
  restructuring may change the controlling parent. Reviewer sign-off needed before any Parent edit.
- **Puerto Sandino FSRU** (Nicaragua) — capacity conflict past the SOP §13 20% materiality
  threshold: GEM 5.00 mtpa vs TradeWinds (Aug 2026) "3 million tonnes".
- **GNL Del Plata FSRU** (Uruguay) — two records: after the banned-source removal the existing
  0.10 mtpa rests on a single yellow source, and 2B1st's verified 10 MMm³/d (≈2.68 mtpa) conflicts
  with it by ~27×. Not staged (single non-primary source + a derived conversion); escalated.
- **Delta Caribe Oriental** (Venezuela) — four pre-existing `[ref]` cells cite banned abarrelfull.
- **Pecém FSRU** (Brazil) — Eneva/Ceiba unit may have moved proposed → construction.

## Defects found and fixed permanently

- **`staging_qc.py` was not a real gate.** It echoed `build_review_package._validate_records`'
  warnings without counting them and printed `GATE CLEAN` anyway — so a whole shard
  (`argentina.qa.json`, 13 records) reached the build with `description`/`field_name` instead of
  `issue`/`gem_field` and would have rendered as blank qa rows. `_validate_records` now **returns a
  count**; the gate adds it to `findings`.
- **New `check_ids()` in `staging_qc.py`** — verifies every staged `terminal_id`/`unit_id` against
  the fresh export and checks that a `[ref]` record's `old_value` URLs actually appear in the live
  cell. It caught the **Uruguay shard staged against a nonexistent `terminal_id` with a fabricated
  `old_value`** (including a 404 URL) and **three ref merges computed against the wrong baseline**
  (Jamaica ×2, Trinidad ×1). Placeholder ids (`multiple`, `n/a`, …) are tolerated on prose sheets
  only, never on `updates`.
- **False `REF-DROP:` on `?cf-view` canonicalisation** — `warn_ref_url_drops._norm` now strips
  session/tracker/view query params (`_JUNK_QUERY_PARAMS`, mirroring `audit_ref_drops`) before
  comparing two URLs for identity.
- **Liveness taxonomy applied, not assumed:** ppiaf.org (403 Cloudflare) and centralamericalink.com
  (521 origin down) had been declared dead by their agents and were restored; only a DNS-failing
  host, a 404, and a bare domain stayed declared.
- **Two would-be duplicate entities** (`XRG` → 100002018879; `Barbados National Energy Company` →
  existing BNOCL 100002005362) — both staged because `entity_lookup.py --remote` returned
  `skipped_no_base_url`, an environmental skip two agents read as a not-found. Permanent fix:
  `entity_lookup.py --pg`, an authoritative `entity_history` check against the read-only Postgres,
  now the documented second check.
- **New `dropped_urls_banned` declaration key** — a banned page is usually still live, so declaring
  it under `dropped_urls_dead` was a false declaration; `audit_ref_drops.py` now classifies
  `dropped_banned_domain` before any liveness probe and never restores one.
- **`ActualStartYear [ref]` does not exist** — the schema pairs `ActualStartYear` with
  **`StartDate [ref]`**. The Barbados new-terminal record was re-keyed (same trap as
  `ProposalYear`/`ProposalMonth` + `ProposalDate [ref]`).

## Limitation — WebSearch budget starvation

The session's WebSearch budget (**200 calls, shared across ALL subagents, not per-agent**) was
exhausted partway through a 22-agent fan-out. `WebFetch` is uncapped, so starved agents degraded to
direct fetches plus DuckDuckGo/Bing HTML scraping (frequently CAPTCHA-blocked).

**Nine `coverage_verdict` records were downgraded to `coverage_verdict_search_limited`** with an
explicit "UNVERIFIED — RE-SWEEP NEEDED" prefix rather than being allowed to pass as checked-and-empty
(a false checked-and-empty poisons every future sweep): `centralamerica` (Panama, El Salvador,
Honduras, Nicaragua) and `andean-guianas` (Peru, Ecuador, Venezuela, Guyana, Suriname). Verified NOT
starved and left as genuine verdicts: `southern-cone`, `mexico`, `caribbean`, and both `*-gap`
clusters. Open leads named in the deliverable: **Honduras Amapala / Gulf of Fonseca**, **Nicaragua
"Puesta del Sol"**, **Guatemala** (highest-prospect uncovered country). The §4.0b gem.wiki
cross-check was not completed for Peru, Ecuador, Venezuela, Guyana, Suriname.

Fix for next time: raise `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION` **before** dispatching a wide
sweep — it is read at session start and cannot be raised mid-session.

## Scope ruling: bunkering is OUT

The discovery dispatch brief wrongly told agents that a marine LNG bunkering terminal receiving LNG
by ship is in scope. `docs/sops/discovery.md` excludes bunkering twice; the SOP governs. A facility
whose **primary function** is bunkering is `monitor` at most, never a staged new terminal; a terminal
that imports LNG for regasification into onward supply stays in scope even if it also bunkers.
Affected: **Panama — Kanfer Shipping / C.B. Fenton / Melones Oil Terminal** stays in `monitor`
(correct outcome); the `caribbean` agent was corrected mid-run (Bahamas Freeport, Trinidad Point
Fortin leads re-evaluated).

## Still open after this batch

- 4 terminals with bare-domain `[ref]` citations in the live DB not repaired by this batch
  (`orchestrator.qa.json`): Gato Negro Manzanillo, Manzanillo Gas & Power, Pecém, Porto Norte
  Fluminense. Six others were repaired in-batch.
- Argentina live-DB ref contamination (Argent LNG URLs on Argentina LNG `CaptiveGasPower` refs),
  re-flagged as `wrong_ref`.
- A supplementary discovery pass with fresh search budget for the nine search-limited countries.
