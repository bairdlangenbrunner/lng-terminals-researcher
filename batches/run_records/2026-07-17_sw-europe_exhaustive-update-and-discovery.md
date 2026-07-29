# 2026-07-17 — Southern + Western Europe exhaustive update + discovery

## Plan

User request: redo the LNG terminals research for the researcher's assigned country list (Western + Southern Europe assignment sheet), "in the same way you did philippines, vietnam, etc."

- **Exhaustive-tier Update** (Update SOP §2.2) + **Discovery** per country, as a scoped multi-country sweep (`docs/workflows.md` §5) under scope slug `sw-europe`.
- Assigned countries (13): Albania, Croatia, Gibraltar, Greece, Italy, Malta, Montenegro, Portugal, Spain, Belgium, France, Germany, Netherlands. Plus 3 coverage-gap discovery-only countries: Slovenia, Bosnia and Herzegovina, Monaco → 16 total.
- 9 research subagents on Sonnet (country groups), each writing `batches/staging/sw-europe/<slug>.<type>.json` (+ `.disc.` variants per the two-book non-overlap rule).
- Merge via `_assemble.py sw-europe` → `build_review_package.py`; discovery build with `--checked-roster` and bracketed by `monitor_store.py seed`/`update`.

## Environment / setup

- Fresh GEM pull at batch start; colmap re-derived (115 cols).
- Tool health verified live: `fetch_timeline.py` (readonly_postgres), `entity_lookup.py --remote`, `url_verifier.py` all healthy. Subagents instructed to STAGE confirmed status changes (never punt) and to skip out-of-scope alt-fuel (LH2/NH3/eLNG) units.
- A fresh scope dir (`sw-europe/`) was used rather than reusing `europe/` — the June sweep files there are already applied and must not re-merge.

## Scope

48 in-scope terminal/unit rows across the 13 assigned countries (the 3 add-on countries have zero GEM rows — discovery-only coverage-gap checks).

## Per-country outcomes

- **Germany** — 3 updates (1 yellow / 2 blue), 5 qa, 1 wiki. Jade Energy rebrand captured; hydrogen/ammonia conversion units correctly skipped as out-of-scope; dormant-revival sites quiet.
- **Portugal / Gibraltar / Malta** — 23 updates (7 green / 1 yellow / 15 blue), 2 qa, 1 wiki. Gibraltar Operator Gasnor→PX Group (green); Sines Google-Maps ref replaced with a real citation; Delimara stable.
- **Croatia / Slovenia / Bosnia and Herzegovina** — Croatia 8 blue ref-fixes, 2 qa, 1 wiki; Slovenia 1 monitor entry (Koper concept watch); Bosnia nothing at Neum (disc.qa only).
- **Greece** — 29 updates (13 green / 3 yellow / 13 blue), 4 qa, 4 wiki, 2 entities. Argo FSRU capacity 4.6→5.2 baseload; Thessaloniki owner Elpedison→Enerwave/HELLENiQ; Thrace environmental approval anchored.
- **Albania / Montenegro** — 9 updates + 1 timeline, 6 qa, 1 monitor. Vlora shelved→**cancelled** (inferred 4-year rule; timeline + anchor year staged); Vlora Integrated Energy Hub staged as a monitor entry with `escalation: true` — orchestrator reviewed and signed off the monitor routing (concept-stage, not stage-able as a new terminal). Bar (Montenegro) stays proposed.
- **Belgium / Netherlands** — 30 updates (18 green / 12 blue), 6 qa, 1 wiki. Zeeland Energy Terminal owner fill VTTI/Höegh Evi 50/50; Antwerp bunkering excluded as out-of-scope; 2 Zeebrugge source-conflict qa items left for reviewer judgment.
- **France / Monaco** — 17 updates (4 green / 4 yellow / 9 blue) + 1 timeline, 5 qa, 2 wiki, 1 monitor. Le Havre FSRU operating→**retired** with timeline (court-ordered shutdown). Dunkirk Parent staleness flagged high-severity in qa but deliberately unedited (ownership chain unresolved). Monaco empty (disc.qa only).
- **Spain** — 37 updates (13 green / 5 yellow / 19 blue), 7 qa, **1 new terminal**. El Musel capacity re-expressed 8.00 bcm/y → 5.10 mtpa (+ paired CapacityUnits). Granadilla Floating LNG Terminal (Endesa, Tenerife, at dead site T100000130537 via AssociatedTerminals) staged — status amended at orchestrator level (see QC gate). giignl.org citations confirmed systematically dead site-wide (matches the standing memory).
- **Italy** — 28 updates (16 green / 8 yellow / 4 blue) + 2 timeline, 9 qa, 2 wiki, 2 monitor. Two non-monotonic status flips staged with Postgres timelines and explicit reviewer flags: Porto Empedocle shelved→proposed and Taranto operating→proposed. Toscana FSRU Snam consolidation to 97.31% (Parent + Parent GEM Entity ID paired records).

Discovery: 1 genuinely new terminal (Granadilla, Spain); everything else resolved to existing GEM records or monitor entries (5 monitor candidates: Koper, Vlora hub, France, 2 Italy).

## Guardrails / QC (merge-time gate)

- Marker completeness: all 29 done markers present (13 update + 16 discovery).
- gem.wiki / globalenergymonitor.org: zero citations. **Caught: Wikipedia padding** — 2 Croatia Krk `Owner [ref]` records cited Wikipedia alongside the lng.hr operator page; Wikipedia stripped (derivative, not independent), records re-tiered primary-single.
- Entity dedup vs read-only Postgres `entity_history` (remote endpoint false-negatives expected per memory): **caught 2 duplicates** — Tokyo LNG Tanker exists (100002024855) and Asterion exists as "Asterion Industrial Partners SGEIC" (100001010765) → `france.entity.json` deleted, qa note points reviewer to the existing ID. Stolt-Nielsen (Italy) dropped — relationship unconfirmed and no staged edit references it (genuinely absent though; recorded in italy.qa). Greece's 2 (Enerwave; HELLENiQ GmbH, distinct from existing HELLENiQ ENERGY Holdings 100000000473) both stand.
- Field-name validation: **caught 9 invalid `field_name`/`ref_field` values** — compound names split per-field (Belgium ProposalYear/ConstructionYear refs → `ProposalDate [ref]` + `ConstructionDate [ref]`; Netherlands Gate compound blue records split with old=new=CSV values); nonexistent `Parent [ref]` column (Parent has no ref in the schema) → Italy Adriatic records converted to Parent blue re-verifies, Toscana phantom ref_field cleared + paired Parent display records added.
- Status-inference audit: **caught Granadilla staged as proposed despite ~3y dormancy** (last activity Aug-2023; orchestrator web-searches confirmed nothing 2024–2026) → amended to shelved (inferred 2-year rule), ShelvedYear 2025 + port-authority ref, confidence yellow — same logic as the Vlora cancellation.
- Build GUARD: null `confidence_note` key on a Spain Mugardos record popped; rebuilt with fresh stamp.
- URL spot-check (9 verifier runs, actual claimed values as tokens): all PASS.
- Timelines (4): all pulled the Postgres timeline first with legal-transition checks (Vlora cancelled inferred-4y; Le Havre retired; Porto Empedocle + Taranto non-monotonic flips flagged for reviewer).
- FSRU sync: `fsru_sync_check.py` gem_only mode (338 GEM FSRUs), carrier backend absent → graceful short-circuit.

## Assembled totals & deliverables

- Assembled: **184 updates (75 green / 22 yellow / 87 blue), 4 timeline, 46 qa (+21 disc.qa), 12 wiki, 2 entity, 5 monitor, 1 new terminal, 0 new units**, 48 scope terminals.
- Workbooks (recalc OK, zero formula errors):
  - `batches/lng_terminals_batch_20260717_0051_ET_sw-europe_exhaustive_update.xlsx`
  - `batches/lng_terminals_batch_20260717_0051_ET_sw-europe_discovery.xlsx` (monitor store: 33 prior + 5 new = 38 total, 0 promoted; prior entries filtered from the sheet by checked-roster)
- Open reviewer-judgment items: Taranto + Porto Empedocle non-monotonic status flips; Dunkirk Parent staleness; 2 Zeebrugge source conflicts; Vlora Integrated Energy Hub monitor entry; Granadilla shelved inference.
- Staging committed under `batches/staging/sw-europe/`; done markers pruned now the run is recorded here.
