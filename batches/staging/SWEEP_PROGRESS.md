# LNG country sweep — progress ledger

Autonomous overnight sweep (user directive, 2026-06-03, "go to bed" run): update existing GEM
LNG terminals country-by-country — start South America (after Colombia), then another continent
(my choice). Findings are STAGED review batches (human applies; never touch the live DB). Branch:
`country-notes-from-chatgpt-audit`. User commits.

## Method (token-efficient — REQUIRED)
- ONE general-purpose subagent per country. It: dedups + matches the country's GEM terminals,
  web-researches updates (prioritize last 12–24 mo; **verify EVERY URL** via `url_verifier.py`;
  PDF? use curl+pdftotext), and checks for missing terminals (discovery dedup).
- The subagent **WRITES** its staged JSON to `batches/staging/<region>/<country>.<type>.json`
  (`updates`, `qa`, `wiki`, `entity`, `newterminals`, `newunits`, `monitor`) and returns ONLY a
  terse summary (counts + headline + escalation flags). This keeps the main loop's context small.
- Merge a region with `batches/staging/_assemble.py <region>` → builds region staged dirs →
  `build_review_package.py` (update mode; discovery mode if new/monitor present) → `recalc.py`.
- **Checkpoint this ledger after each country.**

## Rules (from CLAUDE.md — enforce in every subagent)
- Never write read-only/out-of-scope cols (LH2/NH3/SyntheticLNG/RetrofitProposed/AltFuel*/PCI*/CCS/
  computed Capacity*/Cost* totals/Wiki/TerminalID/UnitID). Capacity = baseload/nameplate.
- Confidence colors green/yellow/red/blue; no orphan [ref]; entity_lookup before any new entity.
- Status change → qa note (fetch_timeline endpoint is DOWN, 404) — do NOT stage a timeline edit.
- >5 genuine NEW candidates in one country → monitor_list + escalation flag, do NOT mass-generate.
- Findings are leads, NOT pre-trusted; conservative matching; ambiguous → qa, never a guessed edit.

## Restart / loop
If rate-limited or context-compacted, resume by reading THIS file and continuing the next PENDING
item. A ScheduleWakeup continuation prompt points back here.

## Queue / status
- [DONE] Audit-import UPDATE batch (US/Algeria/Australia + wiki_updates sheet added to
  build_review_package.py) → batches/lng_terminals_batch_20260603_0030_ET.xlsx
- [DONE] South America — 11 countries / 61 terminals → batches/lng_terminals_batch_20260603_0913_ET_southamerica.xlsx
  (19 updates, 36 qa, 16 wiki, 2 entity; 0 new/monitor). Per-country JSON in sweep/southamerica/;
  merged via _assemble.py → sweep/southamerica/_build/.
- [DONE] Europe — 25 countries / 139 terminals → batches/lng_terminals_batch_20260603_0927_ET_europe.xlsx
  (21 upd, 91 qa, 29 wiki, 1 entity) + ..._0927_ET_europe_discovery.xlsx (1 new unit Türkiye Dörtyol Ph2; 4 monitor).
  EU highlights: Italy Snam ownership consolidations (Adriatic VTTI70/Snam30, OLT Snam100, Piombino vessel→Snam,
  Ravenna now operating); Germany Stade vessel→Energos Force + Mukran vessel churn; France Le Havre FSRU demobilized
  (Nov 2025, qa); Spain Puerto de la Luz cancelled + El Musel rebrand; Ireland SGER sited (Cahiracon, Clare);
  Greece/Türkiye/Cyprus timeline corrections; Russia all sanctions-status qa (0 edits). Entities to dup-check: VTTI BV,
  Floating LNG Terminal Finland Oy.
- [DONE] Africa — 19 countries / 55 terminals → batches/lng_terminals_batch_20260603_0938_ET_africa.xlsx
  (31 upd, 60 qa, 22 wiki, 6 entity) + ..._0938_ET_africa_discovery.xlsx (8 monitor).
  Highlights: Mozambique LNG force majeure LIFTED (status qa) + Coral North ownership FIX (Eni50/CNPC20/Kogas10/
  ENH10/XRG10 — ExxonMobil NOT a partner) + Rovuma first-LNG 2030; Nigeria Olokola state fix + NLNG Train 7 ~92%;
  Egypt FSRU vessel-owner fills + export→import pivot; GTA Gimi vessel + Senegal Kosmos-exit→Petrosen 100% +
  Karmol/Nguya FLNG operating; Cameroon Hilli→Golar 100% (charter ends 2026, vessel→Argentina); Ghana Tema
  "operating" likely overstated (qa). Entities to dup-check: XRG/ADNOC, Ukwanda LNG, Tamasa, Azule Energy.
  Morocco/Libya deferred audit items verified (0 edits).
- [DONE] South America DISCOVERY (proper sweep) → batches/lng_terminals_batch_20260603_1045_ET_southamerica_discovery.xlsx
  (2 NEW terminals: Puerto Drummond LNG/Colombia [ANLA license ~Jun 2026]; LNG del Plata FLNG/Argentina [Camuzzi/Vitol
  MoU Apr 2026]; 1 new unit; 7 monitor; 2 entity [Drummond Energy, Camuzzi]; 35 qa). The proper discovery sweep found
  2 real gaps the update-pass dedup missed — validates running it. Routes-to-Update noted: Guyana LNG enrichment,
  Suriname Petronas FLNG Sloanea milestones, Brazil TGS reactivation.
- [DONE] Middle East → batches/lng_terminals_batch_20260603_1045_ET_middleeast.xlsx (13 upd, 25 qa, 3 wiki, 3 entity)
  + ..._1045_ET_middleeast_discovery.xlsx (2 monitor). Highlights: Iraq's FIRST FSRU Khor Al-Zubair (Excelerate,
  proposed→construction); Qatar NFW T7-8 EPCC awarded (start→2031) + Iran-strike force-majeure risk; UAE Das Island
  debottleneck revival + Jebel Ali/Ruwais FSRU vessel-owner fills; Oman Qalhat T4; Jordan Aqaba vessel change
  (Energos Eskimo→Force) + Sheikh Sabah construction; Saudi confirmed NO LNG terminal.
- [DONE] Asia — 18 countries / 312 terminals → batches/lng_terminals_batch_20260603_1137_ET_asia.xlsx
  (48 upd, 124 qa, 22 wiki, 3 entity; 39 scope terminals) + ..._1137_ET_asia_discovery.xlsx (3 monitor; 0 new).
  Wave A (China 4 shards / Japan 2 / S Korea / Taiwan / Sri Lanka / Hong Kong) + Wave B (India, Vietnam, Indonesia,
  Philippines, Malaysia+SG+Brunei, Bangladesh+Pakistan, Myanmar+Thailand+Cambodia). Highlights: India Gopalpur
  FSRU→land-based pivot (stale Offshore/Floating flags) + Dahej Ph2 online Mar-2026; Vietnam Vung Ang owner
  unknown→PV Gas; Indonesia West Papua/Genting FLNG proposed→construction (FID 2024, first LNG Q3-2026) + Tangguh
  UCC FID + Bontang Train F revival; Philippines Linseed/Ilijan now Meralco PowerGen+AboitizPower+SMGP 100% (qa);
  Malaysia PFLNG Tiga 25% = SMJ Energy not Govt + Lumut RGT-3 advanced (MISC FSRU); Singapore SLNG2 ShelvedYear
  stale (actually in construction, FSRU keel laid May-2026); Bangladesh Payra term-sheet terminated (likely shelved);
  Pakistan GasPort VesselOwner truncated "Mitsui &". Entities to dup-check (3): SMJ Energy, MOL, +1 Malaysia.
  Myanmar/Thailand/Cambodia essentially current (post-coup stall confirmed; MTP3 re-verify).
- NOTE: discovery review delivered + approved (plan file proud-cuddling-sunrise.md). Cheap wins folded into
  _discovery_brief.md (dev-bank/master-plan/orderbook sources, anti-circularity, carrier-only FSRU leads).
- [DONE] Remnants — comprehensive enumeration vs the full export found 26 uncovered countries / 94 terminals
  (more than the original ledger list; earlier continental waves had skipped several singletons). Split into 3 buckets,
  stamp 20260603_1151_ET:
  * americas (14 countries: Canada, Mexico + Caribbean Trinidad/Jamaica/PuertoRico/DomRep/Bahamas/Haiti/Antigua/Aruba
    + Central Am Panama/ElSalvador/Honduras/Nicaragua) → ..._1151_ET_americas.xlsx (7 upd, 34 qa, 8 wiki) +
    ..._1151_ET_americas_discovery.xlsx (2 monitor). Highlights: Canada Woodfibre start→2027 (green); Mexico Vista
    Pacífico CANCELLED (Sempra-CFE pact terminated Dec-2025) + Amigo T1 FID→2026; Trinidad Atlantic "2.0" ownership
    (Shell47.15/bp47.15/NGC5.7) + Train 1 decommissioning Q4-2026; Jamaica Excelerate buy of NFE CLOSED 14-May-2025;
    DR Manzanillo FSRU (Energos Freeze) construction→operating; Bahamas Clifton Pier proposed→construction; El Salvador
    Acajutla + Honduras Puerto Cortés FSU vessel-field fills; Sinolam(Panama)/Puerto Sandino(Nicaragua) status hardening.
    Data-quality flags (qa): Puerto Rico Peñuelas owner "Naturgy [TO BE DELETED]" dup-entity placeholder; several
    "0.00 mtpa"/anomalous-capacity artifacts (Coatzacoalcos II, Antigua, San Juan).
  * oceania (Papua New Guinea, New Zealand, Timor-Leste) → ..._1151_ET_oceania.xlsx (4 upd all blue, 6 qa, 3 wiki).
    PNG LNG T3/P'nyang revival (qa, GEM holds T3 "cancelled"); GEM "Papua LNG T5" is really Kumul standalone FLNG
    (mis-modeled) + "Kumal"→"Kumul" typo (qa); Timor Sunrise Woodside-MPRM Sep-2025 cooperation agmt. NB: ADNOC/XRG
    Santos takeover WITHDRAWN Sep-2025 → no XRG entity needed for PNG (revisit the SA-wave XRG flag).
  * straggler (Botswana, Guinea, Sudan, Mauritius, Western Sahara, Georgia, Gibraltar, Montenegro, Turkmenistan —
    singletons the Africa/Europe/Asia waves missed) → ..._1151_ET_straggler.xlsx (1 upd, 12 qa, 1 entity) +
    ..._1151_ET_straggler_discovery.xlsx (1 monitor). Gibraltar operator Gasnor→px (Gibraltar) Ltd (yellow) + px entity
    dup-check; Botswana Botala FID slip H2-2026; Montenegro Bar LNG inferred-shelved; rest verified-current.

## ✅ SWEEP COMPLETE + CONSOLIDATED BY REGION (2026-06-03) — every country in the GEM export update-swept.
FINAL deliverable set = 6 consolidated regional batches (stamp 20260603_1241_ET), each an update xlsx + (where
monitor/new present) a discovery xlsx: americas, europe, africa, middleeast, asia, oceania. These SUPERSEDE all
earlier per-wave batches (0030/0913/0927/0938/1045/1137/1151) — prune those.
- US/Australia/Algeria CATCH-UP (previously only audit-import-covered, never properly swept): US = 94 LNG terminals
  (Fuel==LNG; the 41 oil/NGL/NH3 rows in the US export are excluded) sharded 6 ways (TX, LA-a, LA-b, SE-gulf, NE,
  West/Alaska) → all verified CURRENT, 0 confident field edits (GEM already reflects Golden Pass first cargo, Corpus
  Christi Stage 3, Rio Grande T4/T5 FIDs, Plaquemines ramp; findings are status/wiki/qa context). Australia (28t,
  2 shards) + Algeria (2t/11u) clean → folded into oceania / africa.
- REGIONAL REORG (per user): egypt moved africa→middleeast; stragglers redistributed (Botswana/Guinea/Sudan/
  Mauritius/WesternSahara→africa; Georgia/Gibraltar/Montenegro→europe; Turkmenistan→asia); BOTH south america dirs
  (update + discovery) merged into AMERICAS (file collisions concatenated, no data loss). The straggler / southamerica
  / southamerica_discovery dirs were dissolved. _prior/{audit_import,egypt} kept as superseded archive.
- TOOLING: build_review_package.py README now lists "Countries checked in this region" split into "Changes found" vs
  "Verified, no changes" (country resolved via terminal_id→GEM export; no-GEM-terminal discovery countries like
  Bolivia/Paraguay surface in qa/monitor, not the breakdown). .gitignore now TRACKS batches/staging/** (ignores only
  the *.xlsx deliverable binaries + the derived staged_*.json).
All escalation flags false. Status changes routed to qa (fetch_timeline down all run).
Cross-cutting follow-ups for the user: dup-check entities flagged across waves (SMJ Energy, MOL, px Gibraltar,
Glenfarne [verify in GEM], VTTI BV, Floating LNG Terminal Finland Oy, Paradise Oil, Camuzzi, Drummond Energy, Ukwanda,
Tamasa, Azule; XRG/ADNOC now moot — Santos takeover withdrawn Sep-2025); Puerto Rico Peñuelas "Naturgy [TO BE
DELETED]" placeholder → Ownership Team.

## Pattern recap (for the resuming agent)
Per sub-region: dispatch parallel subagents (each reads _country_agent_brief.md, REGION=<region>, writes
batches/staging/<region>/<slug>.<type>.json, returns terse) → `python batches/staging/_assemble.py <region>` →
`build_review_package.py --mode update --inputs-dir batches/staging/<region>/_build --gem-csv scripts/gem_export.csv
--output batches/lng_terminals_batch_<stamp>_<region>.xlsx` → recalc → (discovery build from _build_disc if
monitor/new present) → checkpoint ledger → ScheduleWakeup again. fetch_timeline is DOWN (status→qa only).

## SA findings (carry forward)
- Argentina: export project reshuffle — Shell exited "Phase 2" (Dec 2025); XRG/ADNOC into Eni-led
  "Phase 3" (JDA 12 Feb 2026). XRG NOT in GEM entity system (flagged).
- Brazil: Energos Winter FSRU relocated Brazil→Egypt (~Oct 2025) → stale on 3 rows; Pecém-Eneva
  advanced (Ceiba acq + Mar-2026 auction) to ~2030. GEM otherwise solid.
- Suriname: Petronas FLNG Declaration of Commerciality 14 Nov 2025 → 80/20 Petronas/Paradise Oil,
  first gas 2030 (NB: it's Block 52/Sloanea, NOT Block 58/GranMorgu). Paradise Oil dup-check needed.
- Colombia: all audit candidates already in GEM; only Cartagena start-year lag + 400-vs-450 baseline.
- Chile/Peru/Ecuador/Uruguay/Guyana/Venezuela: verified-current, minimal/no edits.

## Tooling/code changes made
- Added wiki_updates sheet to build_review_package.py (update+discovery modes).
- HARDENED _write_row to coerce list/dict cell values to strings (a subagent emitted a list →
  openpyxl crash; now defended for the whole sweep).

## Findings log (carry forward)
- GEM DB is already remarkably current (LastUpdated ~2026-05); the ChatGPT audit was overwhelmingly
  CONFIRMATORY. Expect the same elsewhere → bias toward verification + small high-signal changes,
  not bulk edits.
- Tooling gaps: `fetch_timeline.py` endpoint 404 (stale heroku URL); `url_verifier.py` has no PDF
  text path (false-negatives on .pdf; curl+pdftotext workaround).
