# 2026-07-17 — gulf-turkiye giignl_recon tab experiment + recon research refresh

## Ask

Add a GIIGNL reconciliation tab to the exhaustive-update workbook; pilot on the
already-built gulf-turkiye batch. The committed giignl2026 diff/verdicts were
stale for these countries, so the reconciliation research was refreshed first.

## Plan → what happened

1. **Fresh export + diff regen** — re-pulled the GEM export (1,270 rows) and
   regenerated `batches/staging/recon/giignl2026/giignl_diff.json` twice
   (second time after the alias fix below). Final stats: 180 exact / 80 fuzzy /
   2 report_only / 18 gem_only_operating / 130 nonoperating / 103
   matches_with_disagreement. Gulf-turkiye slice: 14 matches + 2 fuzzy + 1
   nonoperating.
2. **Research pass on the 5 gulf-turkiye disagreements:**
   - **Jebel Ali (UAE) owner delta** — alias false-positive (GEM "DUSUP" vs
     GIIGNL "Dubai Supply Authority"); fixed permanently in
     `scripts/normalize.py` `_OWNER_ALIAS_PAIRS`; row cleared on diff regen.
   - **Das Island (UAE) capacity** — keep GEM 6.0 (ADNOC Gas primary "6 mtpa";
     per-train 1.7/1.7/2.6 in the Air Products capabilities PDF). The cited
     Air Products URL is a genuine 404 → staged 3 `Capacity [ref]` repairs in
     `united-arab-emirates.updates.json` (Wayback snapshot + adnocgas.ae,
     `dropped_urls_dead` declared). New `no_change` verdict.
   - **QatarEnergy LNG (S) owners** — GIIGNL abbreviates the Qatargas 1
     shareholding; GEM's full list re-verified against
     qatarenergylng.qa corporate-structure page. New `no_change` verdict (blue).
   - **Gulf of Saros (Türkiye) capacity** — resolved BY the update batch's
     staged 5.0→5.7 edit; verdict points at it ("do not double-stage").
     Also fixed the staged record's single-source green: added OIES Insight
     171 (7.6 bcm/y ≈ 5.6 mtpa) as the second independent source; 5.7 = range
     max per methodology. (Atlantic Council page failed token verification —
     dropped.)
   - **Al Zour (Kuwait) capacity** — existing keep-GEM-22 verdict retained;
     source re-verified.
   `staged_recon_verdicts.json` now 84 entries. All URLs passed
   `url_verifier.py` (log: `batches/staging/recon/giignl2026/url_verifier_log.jsonl`).
3. **Builder change** (`scripts/build_review_package.py`) — update-mode builds
   accept `--recon-inputs-dir` (+ `--recon-countries`, default = batch
   meta.json `countries`) and append a `giignl_recon` sheet:
   `build_audit_operating_sheet` gained `include_agreeing` (blue
   "agrees — no action" rows) + `sheet_name`; new
   `_diff_filtered_to_countries` + `build_giignl_recon_sheet` (adds scoped
   report_only / gem_only_operating rows); README legend + SHEET_DESCRIPTIONS
   updated. Docs: workbook_conventions.md sheet entry, workflows.md §2 note.
4. **REF-DROP guard fix** — the rebuild surfaced 4 undeclared drops, all
   legitimate 301 rehosts from the earlier ref-drop repair: Al Zour ×3
   (hydrocarbons-technology → offshore-technology, same path) and Mina
   Al-Ahmadi ×1 (bit.ly/2mFGrzK → the kept abarrelfull.wikidot.com page).
   Fixed durably: `warn_ref_url_drops` now treats a dropped URL whose exact
   path survives at a different host as kept (mirrors `audit_ref_drops.py`'s
   `rehosted_same_doc`); the bit.ly shortlink (path unmatchable offline) got a
   `dropped_urls_dead` declaration + disposition note in
   `kuwait.updates.json`. Update SOP §7.2a updated.

## Outcome

- Workbook: `batches/lng_terminals_batch_20260717_1047_ET_gulf-turkiye_exhaustive_update.xlsx`
  (sheets: README, updates_summary, updates_in_database_format,
  entity_additions, qa_review, wiki_updates, **giignl_recon** — 16 rows,
  Kuwait/Qatar/Türkiye/UAE). Build guard-clean; recalc OK. Supersedes the
  1014/1042 files (user prunes).
- The 2026-07-14 discovery workbook (`…_1623_ET_gulf-turkiye_discovery.xlsx`)
  still stands — discovery content is unaffected.
- Test suite: 73 passed.
- Experiment verdict: works; to roll out to other regions, refresh the diff +
  verdicts for that region's countries first (workflows.md §2 note).
