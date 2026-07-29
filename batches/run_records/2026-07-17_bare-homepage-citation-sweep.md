# 2026-07-17 — dead-giignl.org sweep + bare-homepage citation hardening (tracker-wide)

## Ask

Two user-flagged citation-quality failures in the gulf-turkiye exhaustive batch:

1. **Inconsistent dead-giignl.org handling** — Dörtyol's dead GIIGNL-2024 `FacilityType [ref]`
   was repaired while Qatar North Field NFE's dead giignl.org-2022 ref was missed entirely.
   Root cause: per-country subagents applied uneven diligence (the Türkiye agent swept
   giignl.org 404s systematically; the Qatar/UAE agents didn't; Kuwait partial) and nothing
   mechanical enforced batch-wide coverage.
2. **Bare homepage URLs staged as citations** — the Dörtyol wiki/monitor row cited
   `https://www.turkiyetoday.com` and `https://www.ceenergynews.com` (homepages, not the
   articles). Those URLs had never been through `url_verifier.py` at all; the verifier gate
   was only ever enforced by agent discipline, not by the build. User: "this is a huge issue
   and can never happen again."

## What was done

### gulf-turkiye repair (both defects)

- Mechanical export-grep found **34 in-scope cells** citing dead giignl.org URLs → **33 repair
  records** appended (UAE 25, Qatar 6, Kuwait 2; one cell already covered by a staged edit).
  Each re-cites the SAME edition at GIIGNL's official mirror (giignl.org/annual-report →
  elfsightcdn / cdn.prod.website-files.com) after confirming the value in the local
  `data/` PDF; merge semantics kept every surviving URL; drops declared in `dropped_urls_dead`.
  Two deliberate non-rehosts: Das Island Debottlenecking Cost (GIIGNL 2022 never contained
  $1.2bn — real provenance is the ADNOC Gas RGD FID, cited adnocgas.ae + worldoil) and
  QatarEnergy LNG (N) Owner (2022 edition contradicts the 100% value → cited 2026 edition).
- Dörtyol wiki row: homepages replaced with the actual verified articles (turkiyetoday
  article + ceenergynews article + lngprime); qa prose citations expanded to full URLs.
- Rebuild: `batches/lng_terminals_batch_20260717_1224_ET_gulf-turkiye_exhaustive_update.xlsx`
  (97 updates / 25 qa / 10 wiki / 16 giignl_recon; guard-clean, recalc OK). Supersedes 1047_ET.

### Mechanical enforcement (never again)

- **New build guard** `warn_bare_domain_urls` in `scripts/build_review_package.py`: flags any
  bare domain/homepage (scheme+host, no path) in every citation-carrying key
  (`ref_urls`/`source_urls`/`new_value`/`[ref]`/`_ref`) across all lanes, both modes.
  Tests: `tests/test_bare_domain_guard.py` (suite now 77 passed).
- **Docs**: Update SOP §7 (bare-domain rule; every-lane gate) + §7.2 (exhaustive-tier
  mechanical dead-domain sweep step); `_country_agent_brief.md` (specific-page rule,
  every-lane verifier gate with `--log`, giignl.org dead-on-sight + mirror pointer);
  CLAUDE.md hard-requirements bullet extended; `data/README.md` now tables the seven
  official per-edition mirror URLs (all verifier-passed 2026-07-17).

### Tracker-wide scan for the same defect

Guard run over all 1,167 staged JSON files. Hits and dispositions:

| Where | Defect | Fix |
|---|---|---|
| levant-iraq / israel (built, NOT applied) | 15 homepage `ref_urls` entries across 10 records (mees, offshore-energy, lngprime, chevron, jpt.spe, naturalgasintel) + 2 wiki source_urls | Specific articles found + verifier-passed (log in staging dir); rebuilt **1236_ET** |
| sw-europe / germany + malta (built, NOT applied) | jadeenergy.de + melitatransgas.com.mt homepages (1 updates record + 2 wiki rows) | Specific pages verified; rebuilt **1236_ET** |
| devpipeline_exhaustive / africa / mozambique (old, APPLIED) | 6 staged records; **4 cells live in GEM**: Mozambique LNG T1+T2 `ProposalDate [ref]` and `FIDYear [ref]` = `https://www.mozambiquelng.co.mz/` | New repair batch `batches/staging/mozambique-refrepair/` → **`batches/lng_terminals_batch_20260717_1237_ET_mozambique_update.xlsx`** (2010: offshore-mag Windjammer article + Mitsui project page; 2019 FID: worldoil + PRNewswire/Anadarko). bgc.co.mz (Matola) never reached the live DB — no action. Historical staging left as-is (audit trail). |

All subagent replacement URLs were independently re-verified by the orchestrator (13/13 PASS).

## Outcome

- Workbooks: gulf-turkiye **1224_ET**, levant-iraq **1236_ET**, sw-europe **1236_ET**
  (supersede 1047/0952/0951), mozambique **1237_ET** (new). All guard-clean, recalc OK.
- Staging tree is bare-domain-free except the applied historical africa files (documented above).
- 77 tests pass. Verifier logs: per-staging-dir `url_verifier_log.jsonl` files.

## Addendum (same day) — abarrelfull banned as a source

User directive: never use abarrelfull (`abarrelfull.wikidot.com` / `abarrelfull.co.uk`) as a
reference, ever, even corroborated; it must never appear anywhere. Applied across all four
researcher repos (lng-terminals, pipelines, lng-carriers, refineries — CLAUDE.md + source
rosters/forbidden lists).

- **Mechanical enforcement:** `warn_banned_domain_urls` / `BANNED_CITATION_DOMAINS`
  (abarrelfull + gem.wiki/globalenergymonitor.org backstop) in `build_review_package.py`,
  called in every lane, both modes; tests in `tests/test_banned_domain_guard.py` (suite: 81).
- **Purged from unapplied staging** (each replacement url_verifier-passed, logged):
  - gulf-turkiye / Mina Al-Ahmadi Explorer FSRU `Capacity [ref]` → Excelerate project page +
    OGJ first-cargo article + Technica (500 MMcf/d baseload ≈ 3.8 mtpa; note added).
  - sw-europe / Zeebrugge 2008 Expansion `Status`/`ProposalDate`/`ConstructionDate [ref]` →
    live offshore-technology.com project page (bot-blocked, Wayback-verified) +
    oilandgasadvancement.com.
  - south-asia-iran / Mashal `Capacity [ref]` fill → OPIC project EIA PDF (primary/regulatory;
    Wayback snapshot — live www3.opic.gov host dead post-DFC merger).
  - Rebuilds: `..._20260717_1246_ET_{gulf-turkiye,sw-europe,south-asia-iran}_exhaustive_update.xlsx`
    (supersede 1224/1236/0947). Guard-clean, recalc OK.
- **Live-DB inventory (follow-on needed):** the fresh export has abarrelfull `[ref]`s on
  **27 terminals (~60 cells)** — Arun, Bontang, North West Shelf, Brass, Monkey Island,
  Creole Trail, Crown Landing, Calhoun, Keyspan, Compass Port, Beacon Port, Casotte Landing,
  Broadwater, Canvey, Le Havre-Antifer, Brindisi, Trieste Monfalcone, Shtokman,
  Brunnsviksholme, Santos Basin FLNG, Gas Atacama, Colombia FLNG, El Viajano, San Pedro de
  Macoris, El Salvador FSRU, GNL Del Plata, Delta Caribe Oriental. Mostly FacilityType/
  Capacity/Owner refs on old cancelled proposals. A dedicated ref-replacement update batch
  is the offered next step (not run in this session).
