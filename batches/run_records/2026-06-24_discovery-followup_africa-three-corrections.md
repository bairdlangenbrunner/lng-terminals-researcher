# 2026-06-24 — Discovery follow-up: africa sweep, three user-flagged corrections

**Trigger:** User reviewed the 2026-06 africa discovery sweep (workbooks `20260604_2140` / `20260609_1607`) and flagged three errors:
1. **MISS — Congo FLNG (Trident Energy):** "you missed this FLNG" + 3 URLs (worldoil, zawya, a YouTube clip). Asked *why* it was left out and *how* the process will be corrected.
2. **OVER-INCLUSION — Dar es Salaam Small-Scale LNG Terminal:** "domestic only and isn't included in our tracker" — remove it.
3. **MISS — Durban LNG Terminal:** `https://www.gem.wiki/Durban_LNG_Terminal` — another miss to capture.

## Plan
For each: diagnose the root cause honestly, make the data correction in the committed africa staging JSON, then harden the Discovery SOP + CLAUDE.md so the next sweep catches the class. Rebuild + recalc the africa discovery workbook.

## Corrections made (data)

### 1. Trident Energy Congo FLNG — ADDED (`republic-of-the-congo.disc.*`)
- **What:** Proposed FLNG to monetize gas from Trident Energy's **Nkossa / Nsoko II** offshore fields (Trident acquired ~85% operated interest in 2025). Planned as **shared basin infrastructure** (can take associated gas from multiple operators), aligned with Congo's Oct-2025 Gas Code + flaring-reduction Gas Master Plan; CEO has said they are "expediting" it (~3-yr commissioning target). Distinct from the two existing Eni Congo FLNG rows.
- **Staged:** `export`, `proposed`, ProposalYear 2025, Owner/Operator Trident Energy, Offshore/Floating TRUE, **Capacity blank** (no FEED/FID/firm number yet — note flags that the reviewer may prefer `monitor_list`). Entity **Trident Energy** added (likely exists cross-tracker via Equatorial Guinea/Brazil — resolve before creating).
- **Verification:** `url_verifier` PASS — worldoil (`/congo-advances-lng-deepwater-projects…`) + zawya press release, two independent publishers. No gem.wiki / GEM-derivative citations. (Dropped trident-energy.com 403, energycapitalpower 404, energychamber/engineeringnews 403-to-verifier — used only PASS URLs.)

### 2. Dar es Salaam Small-Scale LNG Terminal — REMOVED (`tanzania.disc.*` → `[]`)
- It is a **domestic-only "virtual pipeline"**: a Dar es Salaam liquefaction skid trucking cryogenic LNG to inland regas points (e.g. Elsewedy Industrial City ~100 km inland). It moves **no LNG by ship across a border** → neither import nor export → **out of scope**.
- `tanzania.disc.newterminals.json` and `tanzania.disc.entity.json` set to `[]` (the three entities Rosetta Energy Solutions / TAQA Arabia / Africa50 were referenced only by it). A `scope_correction` qa note records the withdrawal. The existing Tanzania LNG Terminal (Lindi) status_timeline qa note was preserved.

### 3. Durban LNG Terminal — ADDED (`south-africa.disc.*`, new files)
- **What:** Proposed LNG **import** terminal at the **Port of Durban**, **Vitol / ACWA Power / Engen** consortium, FSRU under evaluation, to serve KwaZulu-Natal ahead of South Africa's gas-cliff supply gap. Distinct from the existing Richards Bay and Ngqura/Coega projects.
- **Staged:** `import`, `proposed`, ProposalYear 2026, Offshore/Floating TRUE (provisional FSRU), **Capacity blank** (trade-press ~400 mmscfd / 1,000–1,800 MW figures risk conflation with Richards Bay — a `disambiguation` qa note records this). Entities Vitol / ACWA Power / Engen added, all flagged **likely-existing cross-tracker** (resolve before creating).
- **Verification:** `url_verifier` PASS across constructionreviewonline + cnbcafrica + zawya + clubofmozambique (independent publishers per asserted value). gem.wiki/Durban page **403 bot-blocked** (consistent with stored memory) and web.archive.org blocked for WebFetch this session — characterized entirely from independent trade press.

## Why each was missed (root causes — genuine method gaps, not timing)

1. **Trident:** The original Ring-C sponsor sweep enumerated **established LNG developers** only — it never walked the **upstream OIL operators** who are the actual FLNG sponsors in associated-gas economies (Congo, Gabon, Nigeria…). Trident is an oil independent monetizing field gas, so it fell outside the sponsor list. Discoverable in June (2025 acquisition; Energy Chamber 25-May-2026; AEW 2025).
2. **Dar es Salaam:** A **scope-gate failure compounded by a discipline failure.** The candidate is domestic-only (out of scope), but worse, the staged record **self-flagged the doubt** ("reviewer may prefer a small-scale/peak-shaving classification") and was staged anyway. The lesson: resolve scope doubt *before* staging — never stage-with-doubt.
3. **Durban:** A **structural blind spot** — the terminal HAS a `gem.wiki` page but **NO row in the export CSV**. So it was invisible to BOTH the CSV-dedup step (nothing to match) AND the web-search rings (gem.wiki is correctly excluded as a source, so GEM's own page never enters the candidate pool). A wiki page with no tracker row cannot be seen by an export-driven + web-only method. (Secondary: the SA trade-press sweep under-covered Durban as distinct from Richards Bay/Ngqura.)

## Safeguards added (so the next sweep catches these classes)
`docs/sops/discovery.md` bumped to **rev 2**:
- **§3 scope gate** (new, before the threshold) + matching edge-case bullet + §11 hard rule: `import`/`export` requires LNG crossing a border BY SHIP; domestic-only virtual-pipeline/trucking/peak-shaving plants are out of scope; resolve scope doubt before staging, never stage-with-doubt.
- **§4.0b gem.wiki coverage cross-check** (new) + §10 step 4 + §11 hard rule: enumerate gem.wiki LNG pages per in-scope country, reconcile to the export CSV, research any wiki-only one from independent sources (gem.wiki detects the gap, is NEVER the citation).
- **§4.3 Ring C** expanded + §11 hard rule: sweep upstream OIL operators / associated-gas monetization / flaring-reduction over field operators (Trident/Perenco/Eni/Wing Wah + the NOC), not just established LNG developers.
- `CLAUDE.md` routing notes: one consolidated bullet covering all three blind spots (scope gate / gem.wiki cross-check / upstream-operator sweep).
- Memory: `domestic-only-out-of-scope`, `oil-operator-flng-sweep`, `gemwiki-coverage-blind-spot`.

## Outputs
- Committed source: `batches/staging/africa/republic-of-the-congo.disc.{newterminals,entity,qa}.json` (Trident appended); `batches/staging/africa/tanzania.disc.{newterminals,entity,qa}.json` (Dar es Salaam removed + scope note); `batches/staging/africa/south-africa.disc.{newterminals,entity,qa}.json` (new — Durban). Plus reconstructed `*.disc.done.json` roster markers for all 25 swept africa countries (the original sweep's markers were pruned from head in commit 76a927e; rebuilt so the discovery workbook's "countries checked" roster is accurate).
- Workbooks (build via `_build_region.py africa 20260624_1254_ET`):
  - **`batches/lng_terminals_batch_20260624_1254_ET_africa_discovery.xlsx`** — recalc OK, 0 formula errors. `new_terminals` now = **6**: Beira FSRU, Inhambane FSRU (Mozambique); Banga Kayo, **Trident Energy Congo FLNG** (Congo); Elton Dakar (Senegal); **Durban** (South Africa). **Dar es Salaam absent**; its 3 entities (Rosetta/TAQA/Africa50) absent. entity_additions 16 (incl. Trident/Vitol/ACWA Power/Engen).
  - `batches/lng_terminals_batch_20260624_1254_ET_africa_update.xlsx` — rebuilt alongside (the regional builder always emits both); update side unchanged by this follow-up.

## Caveats / open items
- Built against existing `scripts/gem_export.csv` (Jun-9) — targeted correction to the existing africa discovery batch, no fresh pull. Re-pull if a full fresh batch is preferred.
- Trident and Durban capacities left blank by design (unconfirmed / conflation risk) — reviewer to confirm.
- All four new entities (Trident, Vitol, ACWA Power, Engen) flagged as **likely-existing cross-tracker** — Ownership Team to resolve to canonical IDs before any are created, to avoid duplicates.
- `monitor_store` seed/update not run (no monitor-list change from these additions).
