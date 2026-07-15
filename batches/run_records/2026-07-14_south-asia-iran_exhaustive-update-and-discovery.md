# 2026-07-14 — Bangladesh / India / Iran / Pakistan / Sri Lanka exhaustive update + discovery

## Plan

User request (Warda's Asia coverage): "do the same update, but for … Bangladesh, India, Iran, Pakistan, Sri Lanka" — i.e. the same pattern as the same-day gulf-turkiye run: **exhaustive-tier Update + Discovery per country**, one **Sonnet** research subagent each, merged into combined workbooks. Scope slug `south-asia-iran`.

- India (28 terminals) sharded into two coastal halves per the "shard big countries" convention: **india-west** (Gujarat/Maharashtra/Karnataka/Kerala/Mangalore, 14 terminals/22 units) + **india-east** (Andhra/Odisha/Tamil Nadu/Puducherry/West Bengal, 14/17). india-west also owned the India-wide discovery cross-checks (gem.wiki coverage, coverage-gap, oil-operator sweep); india-east did east-coast candidates + its own dormant-revival.
- Other four countries: one subagent each (Bangladesh 12, Iran 7, Pakistan 11, Sri Lanka 4).

## Environment / setup

- Fresh GEM pull at batch start: **1,267 unit rows**, colmap re-derived (115 cols).
- **Tooling verified LIVE this session** (unlike the stale `_country_agent_brief.md`): `fetch_timeline.py` reads read-only Postgres (`source: readonly_postgres`, confirmed on a real Indian unit); `url_verifier.py` works. Subagent prompts explicitly **OVERRODE the brief's stale "timeline is DOWN → punt status to qa" rule** and instructed the never-punt path: a confirmed status change stages Status + Status [ref] + anchor-year field + a `<slug>.timeline.json` entry.
- **entity_lookup `--remote` is UNRELIABLE this session** (false negatives — see Mitsubishi below). Postgres `entity_history` (42,130 entities) used as the authoritative entity check, same fallback as the 2026-07-02 Vietnam batch.

## Per-country outcomes

- **Bangladesh** — 38 updates (~30 green / 5 yellow), 8 qa, 3 wiki, **2 timeline** (Payra FSRU proposed→cancelled Oct-2024; RPGC Matarbari cancelled-year refinement). Confirmed the Oct-2024 cancellation wave (Payra FSRU, Summit Matarbari FSRU, RPGC Matarbari). Two ownership corrections: Moheshkhali now Excelerate-owned under BOOT (not Petrobangla); Summit FSRU has an undisclosed **Mitsubishi Corp 25%** stake since 2018. Citation-rot repairs on ACWA / Matarbari GE / Summit Matarbari.
- **India (west)** — 10 updates (4 green / 6 blue), 20 qa, 2 wiki, **1 timeline: Dahej Phase 2 commissioned, 17.5→22.5 mtpa, operating 31-Mar-2026** (staged per never-punt). India-wide gem.wiki/PNGRB/oil-operator discovery sweep found no new candidates. Mundra ownership % and Jafrabad FSRU vessel left as qa (genuinely ambiguous).
- **India (east)** — 10 updates (all green), 7 qa, 3 wiki. Fixed a **citation-contamination bug on Dhamra** (Status/StartDate [ref] pointed at Cyprus Vasiliko articles). Added Excelerate to Haldia FSRU owner/parent (reused existing entity). Crown Kakinada FID 2025→2026. Crown Kakinada ↔ Krishna Godavari FSRU cross-referenced as the revived project (kept separate + a qa merge-question for methodology; not auto-merged). No new east-coast candidates (GAIL Paradip EoI confirmed dead since 2015).
- **Iran** — 5 blue re-verifies, 3 qa (**escalation: true**). See below. No status edit staged.
- **Pakistan** — 16 updates (1 green status reversal + blank-ref fills + blue), 5 qa, 1 wiki, **1 timeline** (LNG Easy shelved→proposed, flagged non-monotonic for reviewer sign-off), 2 monitor. Headline: **LNG Easy was stale as inferred-shelved** — the Economic Survey shows it's still an active pre-FID licensee. No new terminals.
- **Sri Lanka** — 31 updates (22 blue / 5 green / 4 yellow), 10 qa, 1 wiki, 1 monitor (Mannar Basin upstream gas, too early). Almost entirely dead-link remediation (manifoldtimes/ceylontoday/thecitizen/dailynews all rotted) via Wayback + alternate outlets, plus one genuine blank-fill (SK Group capacity 1.0 mtpa, single-source yellow).

## ESCALATION — Iran NIOC LNG Terminal (surfaced to user, NOT staged)

GEM holds **Iran NIOC LNG Terminal (T100000130583, T1/T2/T3) as `construction`**. This Tombak/Assaluyeh project has been physically stalled since ~2012 (sanctions; no liquefaction trains ever delivered). The subagent found **no project-specific news since GEM's Jan-2024 citation**, and the exact area has been an **active war zone since 18-Mar-2026** — the same 2026 Israel/US–Iran conflict that hit Qatar's Ras Laffan (gulf-turkiye batch), here striking the adjacent Assaluyeh gas-treatment plants and South Pars field (~12% of Iran's gas output offline; fighting ongoing 13-Jul-2026). No source confirms the plant was damaged, halted, resumed, or abandoned. Per never-punt + resolve-doubt-before-staging, the agent correctly left `construction` untouched, flagged **HIGH-severity qa**, and set `escalation: true`. **Needs user verification against ground truth before any live edit.** (Second Iran-conflict flag of the day, consistent with the Qatar one.)

## Guardrail fix — Mitsubishi entity false-negative (caught in orchestrator QC)

Bangladesh staged **"Mitsubishi Corp" as a NEW entity** citing `entity_lookup --remote = no_remote_match`. Cross-check against Postgres `entity_history` found **30 Mitsubishi entities** (incl. bare `Mitsubishi` 100000000650 and `Summit-Mitsubishi-GE JV` 100000004125), and the exact string **"Mitsubishi Corp" is already the Owner/Parent on ~48 LNG rows** (Gorgon, LNG Canada, Brunei, Donggi-Senoro …). This is a definitive false negative — the remote endpoint is degraded this session. **Corrections:** removed `bangladesh.entity.json` (no duplicate entity created); KEPT the well-sourced Owner/Parent value "Mitsubishi Corp [25%]" (it matches GEM's canonical string); added an `entity_dedup` qa note instructing the reviewer to reuse the existing entity. Net batch entity additions = **0**. (The gulf-turkiye trio — AD Ports Group, Nimex Terminals, Önal Kardeşler — were re-checked against Postgres and confirmed genuinely absent, so that delivered batch's 3 additions stand.)

## Guardrail / QC

- **No gem.wiki / globalenergymonitor.org citations** anywhere (programmatic scan of all URL-bearing fields = 0 violations).
- **All 6 done markers present.** India-west scope coverage confirmed complete (all 14 terminal_ids touched).
- **URL spot-check** (seed 20260714, 6 non-blue records): all PASS via `url_verifier.py`. The "United States, United States" ParentHQCountry on Moheshkhali is NOT a bug — it mirrors GEM's own two-parent convention (Payra FSRU uses the identical string).
- **Timeline**: 4 append entries (Bangladesh ×2, India-west ×1, Pakistan ×1) — the never-punt pipeline (and the `_assemble.py` `timeline` type added in the gulf-turkiye batch) exercised end-to-end for the first time. Pakistan's shelved→proposed carries an explicit non-monotonic reviewer flag.
- **giignl.org dead-ref pattern** recurred (Kuwait/Türkiye earlier today; here Bangladesh + India) — reinforces the tracker-wide citation-QC sweep candidate. NOTE: the Dahej GIIGNL *news* URL (giignl.org/news/…) is live and PASSed — it's the legacy report/PDF paths that are rotted.

## Deliverables

- Assembled totals: **110 updates · 4 timeline · 55 qa · 10 wiki · 0 entity · 3 monitor · 0 new terminals · 34 scope terminals.**
- Workbooks (recalc OK, zero formula errors):
  - `batches/lng_terminals_batch_20260714_1537_ET_south-asia-iran_exhaustive_update.xlsx`
  - `batches/lng_terminals_batch_20260714_1538_ET_south-asia-iran_discovery.xlsx` (monitor store: 28 prior + 3 new = 31 total, 0 promoted)
- Staging committed under `batches/staging/south-asia-iran/`.

## Rebuild 2026-07-14 (16:23 ET) — de-dup + monitor roster filter

User flagged that the discovery book duplicated the update book (identical `status_timeline_additions`/`wiki_updates`/`qa_review`) and that `monitor_list` listed 23 out-of-region countries. Fixed the tooling (permanent, not a one-off): `_assemble.py` now pass-splits `qa`/`entity` via the `.disc.` infix, and `build_review_package.py` makes the two books non-overlapping (discovery = new/potential-terminal only; monitor filtered to `--checked-roster`). See workbook_conventions.md non-overlap rule. **Superseding workbooks** (recalc OK):
  - `…_20260714_1623_ET_south-asia-iran_exhaustive_update.xlsx` — updates + timeline + wiki + 46 update-pass qa.
  - `…_20260714_1623_ET_south-asia-iran_discovery.xlsx` — monitor (Pakistan 2 + Sri Lanka 1 only) + 9 discovery-pass qa; 0 new terminals.
  - The 1537/1538 pair is superseded and can be pruned. (monitor store already rolled forward in the original build — NOT re-run.)
