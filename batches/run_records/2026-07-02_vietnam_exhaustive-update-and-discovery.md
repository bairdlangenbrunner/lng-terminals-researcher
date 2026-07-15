# 2026-07-02 — Vietnam exhaustive update + discovery

## Plan

Combined batch requested as "now do the discovery and exhaustive update for vietnam specifically":

- **Exhaustive-tier Update** (Update SOP §2.2): every field and every existing `[ref]` on all 29 Vietnam terminals re-verified; four geographic shards (north / central / south-central / south+Mekong), one research subagent each.
- **Discovery** (Discovery SOP): full candidate sweep + the four known blind-spot checks (dormant-revival watch, gem.wiki coverage cross-check, scope gate, upstream-operator sweep) + PDP8 (Decision 768/QD-TTg) reconciliation; one subagent.
- Build two workbooks from `batches/staging/vietnam/` via `_assemble.py` → `build_review_package.py`, discovery bracketed by `monitor_store.py seed`/`update`.

## Status / incidents

1. **Two usage-limit interruptions.** All 5 first-wave subagents died instantly on "session limit resets 6:30pm"; per the limit-resume pattern, a cheap probe agent confirmed the reset message was stale and all 5 were redispatched identically — the 4 update shards completed. The discovery agent then died a second time ("resets 8pm") mid-verification with partial staging files and no done marker; probed again (ok) and dispatched a targeted resume agent enumerating exactly what existed vs. remained. It completed everything including the done marker.
2. **Remote entity endpoint degraded.** `entity_lookup.py --remote` (Heroku) returned an empty response for every query all session. Working fallback: read-only Postgres via `GEM_READONLY_DB_URL`, table `entity_history` (entity names live in `"entityJSON"->>'name'`; use a `distinct on (entity_id) … order by entity_id, modified desc` latest-row pattern). All entity dispositions below were verified through that path.
3. **`fetch_timeline.py` still down** (known stale Heroku host) — all status-change findings routed to `qa_review` category `status_timeline`, no timeline edits staged.

## Key research outcomes

- **Vung Ang plant-vs-terminal correction (high severity, caught in review).** Shard 1 originally staged the Vung Ang III *power plant* consortium (PV Power 51% / B.Grimm 34% / Lilama, COD 2031) as terminal Owner. The GEM record is the LNG *terminal*, separately approved to PV Gas (VND 26.7tn / ~$1.01bn, phase 1 target 2029–2030). Patched: Owner → "PetroVietnam Gas" (green, 3 refs), LatestPlannedStartYear → 2029, Parent → "Vietnam Oil and Gas Group Co [100%]" (yellow); high-severity qa note documents the correction.
- **JAPEX exited Nam Dinh** → Owner → ITECO JSC.
- **Quynh Lap**: owner → PV Power / SK Innovation / NASU; construction began 2026-05-18 (qa, timeline down).
- **Ca Na revival**: Trung Nam–Sideros River contract 2026-04-10, start 2030.
- **Son My phase 1** capacity 2.4 → 3.6 mtpa; **Long Son** 4.4 → 3.5 (yellow, high qa gate); **Bac Lieu** start 2027 → 2030 + stale ConstructionYear=2024 deletion; dead GIIGNL-2024 ref repaired across 8 cells (south shard).
- **4 new terminals staged**: Cong Thanh (re-staged, entity corrected to existing 100000120281, capacity left blank), Quang Trach II (EVN, Hon La EZ), Dung Quat (4.5 mtpa, Van Tuong Energy), Nam Van Phong (cancelled-historical, Petrolimex, AssociatedTerminals → Khanh Hoa). **3 monitor**: Vung Tau FSRU (carried forward), Sumitomo Van Phong 2, T&T Quang Tri conversion.
- **Blind-spot checks all clean**: dormant-revival on all 10 dead sites (no revivals); gem.wiki 29↔29 exact match to export CSV (no Durban-class gap); PDP8 768/QD-TTg reconciliation clean.

## Flags for reviewer (in qa_review)

- **HIGH — Haiphong FSRU**: GEM holds construction, but Vingroup proposed (2026-03-25) abandoning LNG for renewables+BESS. Status verification needed before annual publication.
- **Nam Dinh vs "Northern Vietnam LNG"** — probable duplicate pair; recommend user adjudication.
- **Province mergers (July 2025)**: Vietnam's administrative consolidation makes many State/Province values stale tracker-wide; needs a convention decision, not per-row edits.
- **Quang Trach II tension**: own-terminal vs Vung Ang-terminal-supplies-it — staged as own terminal with qa note.
- **Long Son 3.5 mtpa** is single-sourced (yellow) with an explicit qa gate.
- `country_universe.py` coverage_gap: botswana/turkmenistan absent from the universe list (noted during worklist derivation; not Vietnam-scoped).

## Entity dispositions (all via Postgres entity_history)

- **Genuinely new (5 staged)**: NASU (Nghe An Sugar), Sideros River, Trungnam Group (annotated — subsidiary Trung Nam Wind Power 100002002611 exists), Van Tuong Energy JSC, Petrolimex.
- **Reuse, dropped from entity staging (qa notes added)**: Kyuden International 100000003449, Truong Thanh Vietnam Group 100000001336, Lilama = Vietnam Mechanical Assembly 100002016754, Cong Thanh Thermal Power 100000120281.

## Outcome

- Assembled totals: **141 updates, 81 qa, 15 wiki, 5 entity, 3 monitor, 4 new terminals, 0 new units**, 28 scope terminals.
- URL gate honest: every staged URL through `url_verifier.py` with the claimed value as token; random spot-check (seed 20260702, 8 records) all PASS. No gem.wiki/GEM citations anywhere (grep-verified).
- `fsru_sync_check.py` run: gem_only mode (carrier export absent), graceful short-circuit.
- Workbooks:
  - `batches/lng_terminals_batch_20260702_1852_ET_vietnam_exhaustive_update.xlsx` (recalc OK)
  - `batches/lng_terminals_batch_20260702_1854_ET_vietnam_discovery.xlsx` (recalc OK; monitor store: 3 new candidates, 22 prior rolled forward, 25 total, 0 promoted)
- Staging committed under `batches/staging/vietnam/`; done markers deleted post-build per lifecycle.

## Follow-up 2026-07-09 — timeline punts resolved

Prompted by the question "you said Thai Binh broke ground but staged no status change — why?". Root cause: incident #3 above — the whole batch routed confirmed status changes to `status_timeline` qa notes because `fetch_timeline.py` was still the dead Heroku scraper on 2026-07-02 (the read-only-Postgres read path and the never-punt rule both postdate this batch, and were added partly in response to it; Quynh Lap is the named canonical miss). Re-checked all 5 `status_timeline` findings against a fresh export + Postgres:

- **Thai Binh FSRU** — user applied it live during the check: Status=construction, ConstructionYear=2025/ConstructionMonth=October, ConstructionDate [ref]=GIIGNL groundbreak URL, timeline construction/actual/2025-October (st_id 41217). Date is green (2 independent: GIIGNL news + SoutheastAsiaInfra). qa note closed.
- **Quynh Lap** — already applied 2026-07-09 (construction, 2026/May). No action.
- **Ca Na** — re-verified still pre-FID (FID expected Q4 2026); correctly stays `proposed`. Its punt was really "construction not independently confirmed", not the timeline outage — reclassified to low, qa note closed.
- **Hai Lang / Bac Lieu** — no status change (already so noted).

Net: nothing left to re-stage — every confirmed transition is applied in the live DB. Only qa-note hygiene updated (vietnam_0.qa.json, vietnam_2.qa.json).

## Follow-up 2026-07-09 — Quang Trach II withdrawn (power-plant ≠ terminal)

Prompted by the user pointing out (via en.vcci.com.vn/…/116362) that Quang Trach II is supplied by the existing Vung Ang LNG Terminal, so the staged "Quang Trach II LNG Terminal" is not a separate import terminal — it's a GOGPT power plant fed by piped regas from Vung Ang (T100000131060, ~30 km north). Root cause: the batch staged a power project's bundled `kho, cảng LNG` component as an independent marine terminal without confirming a ship berths there (tank/berth specs never verified — a red flag), AND flagged the exact supply-chain tension in a qa note yet kept the candidate anyway (stage-with-doubt violation).

Corrections:
- Removed "Quang Trach II LNG Terminal" from `vietnam.disc.newterminals.json` (4 → 3 new terminals); reassembled `_build`.
- Rewrote the cross_reference qa note → `correction` (terminal_id T100000131060): withdraw candidate, route `PowerPlantsSupplied += Quang Trach 2/3` to the existing Vung Ang row (ref: vcci 116362, verified PASS), and — if the 2026-07-02 discovery workbook was already applied — DELETE the erroneous live-DB terminal row. Fixed the PDP8-reconciliation note mapping (LNG Quang Trach II → Vung Ang + GOGPT, not a new terminal).
- Staged the withdrawn candidate's research as Vung Ang **wiki fodder** (per user: a power-plant candidate's research is useful Background on the supplier terminal, not wasted) — `vietnam_1.wiki.json` topic "Downstream LNG supply to the Quang Trach power complex", [CONFIRMED] on vcci 116362 + theinvestor d17112 (both PASS "Quang Trach").
- Rebuilt discovery workbook (final): `batches/lng_terminals_batch_20260709_1757_ET_vietnam_discovery.xlsx` (recalc OK; Quang Trach absent from new_terminals; correction qa note + Vung Ang supply-wiki entry present; wiki_updates 15 → 16). Supersedes the `_1718_` interim rebuild.
- Encoded the lesson: Discovery SOP §3 rev 3 "Power-plant ≠ terminal" (incl. the wiki-fodder guidance) + §11 hard rule; CLAUDE.md scope-gate routing note; memory `power_plant_not_terminal`.
