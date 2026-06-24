# Exhaustive dev-pipeline update — progress ledger

**Scope:** every GEM LNG unit with Status ∈ {proposed, construction, shelved} — 473 units
(proposed 270 / construction 104 / shelved 99), frozen at the 2026-06-08 GEM pull (`WORKLIST.json`).
**Tier:** exhaustive (re-verify every populated field + every existing `[ref]`; pile on all verified URLs;
unchanged cells = blue re-verify). **Status changes → qa note** (`fetch_timeline` host down).

This is the fine-grained in-flight ledger. The durable per-run summary is
`batches/run_records/2026-06-08_exhaustive-update_dev-pipeline.md`. Resume any time with
`python batches/staging/devpipeline_exhaustive/_state.py` — done-markers (`<slug>.done.json`) are authoritative.

## "Other units/terminals" (to come back to later)
Everything NOT in this worklist: operating / idle / mothballed / cancelled / retired units. Those are a
separate future batch; this effort touches only the three development-pipeline statuses.

## Region order (chosen 2026-06-08): middleeast first, then **STOP and hand the xlsx to the user to iterate.**
Remaining order TBD after iteration (default ascending by size: oceania → africa → europe → americas → asia).

| Region | Units | Countries | Status | Workbook |
|---|---|---|---|---|
| **middleeast** | 18 | 9 | **DONE 2026-06-08** (handed off; re-checked) | `batches/lng_terminals_batch_20260608_1938_ET_middleeast_devpipeline_exhaustive_update.xlsx` |
| **oceania** | 29 | 4 | **DONE 2026-06-08** | `batches/lng_terminals_batch_20260608_1958_ET_oceania_devpipeline_exhaustive_update.xlsx` |
| **africa** | 51 | 17 | **DONE 2026-06-08** | `batches/lng_terminals_batch_20260608_2121_ET_africa_devpipeline_exhaustive_update.xlsx` |
| europe | 73 | 18 | PENDING | — |
| americas | 130 | 19 | PENDING | — |
| asia | 172 | 16 | PENDING | — |

### middleeast countries (18 units) — all DONE 2026-06-08 (first pass + re-check)
First-pass result, then the **re-check** delta (Wayback ref recovery + unsourced-value resolution/deletion):
| Country | slug | units | done | result (first pass → re-check) |
|---|---|---|---|---|
| Egypt | egypt | 3 | ☑ | 42 blue; 16 refs added; 7 qa → **+5 Wayback refs**; Ertugrul Capacity 4.10 now sourced (**yellow**); 0 deletes |
| Iran | iran | 3 | ☑ | 40 blue; 2 Owner refs; 14 qa → **+3 Wayback refs** (PowerPlantsSupplied "Tonbak", yellow); **6 green-empty deletions** (T1+T2 Cost/CostUnits/CostYear $5B/2017 unsupportable — false-positive PASS) |
| Iraq | iraq | 2 | ☑ | 29 blue; **1 green** (Khor Al-Zubair start 2025→2026); 5 qa → **+1 Wayback ref** (Bloomberg, 12 cells); 0 deletes; Al-Faw Owner/Parent stay unknown |
| Israel | israel | 1 | ☑ | 18 blue; 2 refs replaced; 5 qa → **+1 Wayback ref group** (Nasdaq Location, 5 cells); Cost $435M upgraded single-soft → **green** (Rystad primary) |
| Jordan | jordan | 1 | ☑ | 16 blue; 9 refs; 3 qa → **+1 Wayback ref** (fananews Financing, now 3 independent); 0 deletes |
| Lebanon | lebanon | 2 | ☑ | 17 blue; 5 qa → **+1 Wayback ref** (Zahrani MoEW PDF); PowerPlantsSupplied yellow → **green** (2 independent); 0 deletes |
| Oman | oman | 1 | ☑ | 11 blue; 3 refs; 3 qa → **+1 Wayback ref** (S&P Operator, 4-URL set); 0 deletes; Owner/Parent legitimately unknown |
| Qatar | qatar | 3 | ☑ | 59 blue; **1 green** (NFW start 2030→2031); 6 qa → **+4 Wayback refs** (Reuters $12.5bn / S&P / offshore-tech / nsenergy); 0 deletes |
| United Arab Emirates | united-arab-emirates | 2 | ☑ | 36 blue; 4 qa → **+2 Wayback refs** (S&P Owner, offshore-tech FID, 6 cells); **2 green-empty deletions** (T1+T2 Pipelines = Dolphin; feedgas is Habshan, no substitute) |

**Batch totals (post re-check):** 284 update records (268 blue / 3 green / 5 yellow / **8 green-empty deletions**) ·
65 qa entries · 12 terminals in scope ·
workbook `batches/lng_terminals_batch_20260608_1938_ET_middleeast_devpipeline_exhaustive_update.xlsx` (recalc clean).
First pass: 271 records (268 blue / 2 green / 1 yellow) / 52 qa.
**Cross-cutting finding:** GEM Middle East dev-pipeline is current and accurate — almost no value drift.
The dominant action is **ref-rot repair**; the re-check showed most "dead" refs were live-but-bot-blocked and
**recovered via Wayback** (~19 distinct URLs reinstated), and resolved the genuinely-unsourced values: 8 cells
deleted (green-empty, value unsupportable + no alternative), 3 confidence upgrades. Two status leads (Jordan,
Qatar NFW) and the Damietta capacity discrepancy remain the human-review items; all routed to qa, none auto-staged.

### oceania countries (29 units) — all DONE 2026-06-08
Fan-out was 8 agents (Australia + PNG sharded on clean terminal boundaries; one agent each for Timor-Leste, New Zealand).
Workflow `wf_74359dc1-cdc` (Task `wewavxgez`), 8/8 returned.
| Country | slug | units | terminals | done | result |
|---|---|---|---|---|---|
| Australia | australia (1/2/3) | 9 | 9 | ☑ | 164 blue; **1 green change** (Ichthys T3 Parent equity restated — INPEX bought Tokyo Gas's 1.575%); 39 refs added; 26 qa; 0 deletes |
| Papua New Guinea | papua-new-guinea (1/2/3) | 18 | 3 | ☑ | 241 blue; **8 green changes** (Papua LNG T1-T4 Owner+Parent equity: ExxonMobil 38.1→37.04%, Santos 22.8→22.83%, ENEOS Xplora 2→2.58%); 94 refs added; 48 cells left blank-unsourced (PAWA multi-town concept); 27 qa (incl. 2 HIGH) |
| Timor-Leste | timor-leste | 1 | 1 | ☑ | 12 blue; 3 refs; 1 blanked (FIDYear=2021 unsupportable); 4 qa |
| New Zealand | new-zealand | 1 | 1 | ☑ | 11 blue; 4 refs; 3 qa |

**Batch totals:** 443 update records (**434 blue / 9 green** value changes / 0 yellow / 0 deletions) ·
60 qa entries (2 high / 13 medium / 45 low) · 14 terminals / 29 units / 4 countries ·
workbook `batches/lng_terminals_batch_20260608_1958_ET_oceania_devpipeline_exhaustive_update.xlsx` (recalc clean).
Unchanged cells normalized to blue per convention (agents had colored 18 unchanged-but-strongly-sourced cells
green/yellow; recolored to blue at shard source so source-strength lives in the ref count, not the cell color).
**Cross-cutting finding:** like the Middle East, GEM's Oceania dev-pipeline is largely current — the only value
drift is two equity restatements (Ichthys T3, Papua LNG). Dominant action again = ref-rot repair / blank-ref fill.
**Human-review items (qa, not auto-staged):** PNG **T5 Kumul FLNG** Source/Location/Capacity conflate two concepts
(HIGH — needs disentangling); Australia **NTLNG** "shelved" basis is editorial on-hold (status lead, fetch_timeline down);
**Pluto** Location Perth→Karratha; **Port Phillip Bay** Capacity 4.70 mtpa + Tasmania **Cost** $6.28B unsourced;
**Timor Sunrise** still modeled floating but the live concept is now onshore (Bayu-Undan→Beaço).

### africa countries (51 units) — all DONE 2026-06-08
Fan-out was 23 agents (Nigeria → 5 shards, Mozambique → 3 shards, others one each), recovered from a mid-run
session limit via probe + two throttled waves. **First region with new entities + monitor leads** — exposed and
fixed a latent assembler gap (`_merge_recheck.py` never merged `*.entity.json` / `*.monitor.json`; `build_review_package.py`
update mode never loaded `staged_monitor_list.json`). Both now fold those inputs; entities carry a yellow "RUN
entity_lookup before creating" flag because the remote lookup endpoint was degraded this batch.
| Country | slug | units | terminals | done | result |
|---|---|---|---|---|---|
| Nigeria | nigeria (1–5) | 16 | 8 | ☑ | 239 blue; **0 green**; 138 refs added/replaced; 10 blanked-unsourced; 28 qa (incl. NLNG dead igu.org ref, **Olokola wrong State/Province + coords** HIGH) |
| Mozambique | mozambique (1–3) | 9 | 6 | ☑ | 121 blue; **5 green** (Coral North FID-reshaped Owner/Parent/ParentHQ + Capacity 3.40→3.6; Matola FSRU Owner→Beluluane Gas Co); 59 refs; 28 qa (4 HIGH status leads); 2 new entities (XRG, Beluluane) |
| South Africa | south-africa | ~5 | — | ☑ | blue; **3 green** (Ngqura Operator SFF→Ukwanda LNG + start 2029→2035; Richards Bay Transnet FSRU FIDYear 2026→2028); 2 new entities (Ukwanda LNG, Tamasa Energy Group) |
| Senegal | senegal | — | — | ☑ | **2 green** (Yakaar-Teranga Owner/Parent Kosmos exit → Petrosen 100% + FIDYear 2025→2026); Capacity 10 mtpa unsupported → qa |
| Kenya | kenya | — | — | ☑ | 15 cells single-sourced → **yellow→blue** (re-verified, fragility kept in qa) |
| + Cameroon, Côte d'Ivoire, Congo, Botswana, Ghana, Tanzania, Angola, Benin, Togo, Morocco, Namibia, Eq. Guinea | — | — | — | ☑ | mostly blue re-verify + ref repair; watch-leads → monitor_list |

**Batch totals:** 743 update records (**732 blue / 11 green** value changes / 0 yellow / 0 deletions) ·
149 qa entries (**13 high / 50 medium / 86 low**) · 35 terminals / 51 units / 17 countries ·
**4 new entities** (XRG, Beluluane Gas Company, Ukwanda LNG, Tamasa Energy Group — all yellow-flagged for
entity_lookup re-verify) · **4 monitor leads** (Côte d'Ivoire CI-GNL/Abidjan FSRU revival, Mozambique Nacala FSRU +
Matola FID, Botswana LNG intent) · workbook `batches/lng_terminals_batch_20260608_2121_ET_africa_devpipeline_exhaustive_update.xlsx` (recalc clean).
**Cross-cutting finding:** more value drift than Middle East / Oceania — 11 genuine changes, all FID/ownership
reshapes (Coral North Oct-2025 FID, Yakaar-Teranga Kosmos exit, Ngqura operator change). Several dev-pipeline units
have moved up the lifecycle since GEM's last touch — **the 13 HIGH qa items are dominated by status leads** the
agent could not stage (fetch_timeline down): Mozambique LNG T1/T2 force-majeure lifted (shelved→construction),
Coral North post-FID (proposed→construction), Rovuma FLNG revived as Coral North, Eni Congo FLNG II (Nguya) now
operating (Dec 2025), Karmol Dakar FSRU now operating (May 2025). Plus the Olokola location error (wrong
State/Province + coordinates) and Yakaar-Teranga 10 mtpa capacity now unsupported.
