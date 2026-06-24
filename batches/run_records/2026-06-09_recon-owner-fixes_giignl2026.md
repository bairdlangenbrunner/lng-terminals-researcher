# 2026-06-09 — Recon owner-column factual errors (coworker review of Japan) → two parser fixes + rebuild

## Request
Coworker reviewing the GIIGNL-2026 reconciliation for Japan: the owner-comparison columns make
**factual errors about what the report says** — Higashi Niigata flagged "GIIGNL names ['tokyo-gas']
not in GEM" (report does NOT list Tokyo Gas; it agrees with GEM); Sodegaura flagged "GEM has ['jera']
not in GIIGNL" (JERA IS in GIIGNL). "Happens for a number of terminals"; explicitly NOT the known
ownership-tree/parent issue.

## Diagnosis — two independent bugs
1. **Extraction head-bleed** (`giignl_extract._attribute_owner_fragments`): a tall vertically-centered
   owner cell's dangling-open head ("Niihama LNG (Tokyo Gas") sat nearer the PREVIOUS row's data line,
   so strict-nearer fused it up onto Niigata and stranded the shareholder tail on Niihama. Same shape
   in China: Tianjin Nangang ate Wenzhou's head.
2. **Missing spaced-slash split** (`report_diff._split_top_level` + `normalize.parse_entity_list`):
   "Tokyo Gas / JERA" stayed one token → normalized to its FIRST entity, silently dropping JERA →
   false gem-only deltas on Sodegaura, Negishi, Chita Kyodo, Ishikari.

## Fixes (permanent, in repo)
- `scripts/giignl_extract.py` — paren-balance repair post-pass in `_attribute_owner_fragments`:
  complementary imbalance (upper row +ve in trailing below-data-line fragments, row below net −ve)
  marks a bled head; move the minimal trailing positive-balance run down.
- `scripts/report_diff.py` — `_split_top_level` splits on a SPACED `' / '` at paren depth 0;
  a TIGHT slash never splits ("Japex/Fukushima Gas Power", "Torp Technology A/S", "N/A").
- `scripts/normalize.py` — `parse_entity_list` mirrors the spaced-slash rule on the GEM side.
- `scripts/README.md` deep-dives updated (owner-bleed paragraph, "read the source when" clauses,
  `parse_report_owner` paragraph).

## Plan / status
- [x] Reproduce all coworker cases from the committed diff + raw pdftotext.
- [x] Both fixes implemented; re-extract → `giignl_extracted.csv` (348 rows, totals within +1.0%/+0.1%);
  exactly 4 cells changed vs pre-fix (Niigata, Niihama, Tianjin Nangang, Wenzhou — the last two a bonus
  China fix of the same bleed shape).
- [x] Fresh GEM pull (1,279 unit rows, 115 cols) + colmap re-derived; diff regenerated
  (`giignl_diff.json`): matches_with_disagreement 106→100; every coworker-reported false delta cleared
  (Niigata, Sodegaura, Negishi, Chita Kyodo gone from audit_operating; Niihama overlaps on all five
  entities incl. tokyo-gas; Wenzhou matches GEM).
- [x] One GENUINE finding surfaced by the slash fix: **Ishikari** — Hokkaido Electric co-owns (Tank
  No. 3, 230,000 kL, joint-usage agreement; no published equity split). Researched + staged owner edit
  (verdict appended to `staged_recon_verdicts.json`, 81 entries) with two verified independent refs
  (DBJ case page + Kawasaki press release; NS Energy 403-bot-blocked and JEPIC token-fail dropped).
  Caveat: `entity_lookup.py` remote returned ZERO candidates for every HEPCO variant (identical
  raw_html_size each query) — endpoint likely broken/stale (cf. fetch_timeline's dead Heroku host);
  user should confirm the entity exists at apply time.
- [x] Rebuilt workbook → `batches/lng_terminals_batch_20260609_1858_ET_giignl2026_reconciliation.xlsx`
  (recalc clean; superseded 1854 build removed). Ishikari shows RESOLVED; edits_to_gem fans the owner
  edit to all 3 unit-rows.
- [x] Docs + memory updated (`giignl_owner_column_contamination.md`).

## Side findings (not caused by the fixes)
- **Kushiro LNG Terminal (T100000130495) and Akita LNG Terminal (T100000130714) were DELETED from the
  live GEM DB** between the Jun-7 snapshot and this pull; both are still referenced in Hachinohe's
  `AssociatedTerminals`. Kushiro is operating per GIIGNL 2026 and now surfaces as `report_only`.
  Flagged to user — intentional deletion or accident?
- Discovery lead: Hokkaido Electric plans a NEW LNG terminal (+ gas-fired plant for data-center
  demand), pgjonline Jan 2026 — candidate for the next Discovery batch, not staged here.

## Outcome
Coworker's reported errors were real, fully reproduced, and root-caused to the two bugs above; both
fixed permanently in the versioned scripts, the giignl2026 staging inputs re-derived, and the
reconciliation workbook rebuilt. Net diff churn was strictly the intended corrections plus live-DB
drift (Kushiro/Akita deletions, Summit Lake PG addition).
