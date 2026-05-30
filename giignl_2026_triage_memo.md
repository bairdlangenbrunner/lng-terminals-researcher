# GIIGNL 2026 reconciliation — triage memo

Generated 2026-05-29. Source: `giignl_diff.json` (fresh GEM pull + fixed extractor).
Deliverable workbook: `batches/lng_terminals_batch_20260529_1418_ET.xlsx`.

**Nothing here is applied.** Reconciliation surfaces work; the fixes go through the
Update / Discovery workflows where GIIGNL is one Tier-1 source among others
(SOP §3.8). This memo just routes what the clean diff found.

## Headline numbers

| Bucket | Count | Note |
|---|---|---|
| Matches | 223 | exact 148 + fuzzy 75 |
| — owner-only deltas | 118 | benign (full JV vs immediate owner) — log/confidence only |
| — clean (agree) | 32 | confidence bump |
| — **material capacity conflicts** | **45** | 35 real value deltas + 10 status-lag (GEM op=0) |
| — minor capacity (<5%) | 28 | rounding-level; surfaced, low priority |
| GIIGNL-only (report-only) | 31 | Discovery / name-reconcile candidates |
| GEM-only operating | 54 | mostly expected GIIGNL gaps (§3.7) |
| Ambiguous | 15 | manual review in the sheet |

Both SOP §6 raw gates show TRIPPED in the README (53.8% disagreement; report-only
31 > 30), but judged by **material** signal they're benign: the 53.8% is dominated
by 118 owner-only deltas, and the 35 real capacity deltas are spread across ~30
countries (FSRU nameplate / per-train nuances) — the normal long tail, not a
systematic issue. report-only 31 is now genuine (the country-mislabel false
positives were fixed this batch).

## A. Update — real capacity conflicts worth a look first

Likely **GEM missing expansion units** (investigate per §3.5; highest value):
- **Yangshan, Shanghai** — GIIGNL 12.0 vs GEM 6.0 (100%)
- **Zhuhai, Guangdong** — 7.0 vs 3.5 (100%)
- **Tianjin (PipeChina)** — 6.0 vs 12.0 (50%, GEM higher — check double-count vs real)
- **Hibiki** (Japan) — 2.0 vs 1.0 (100%)

Likely **GEM correct / GIIGNL lag** (verify, probably confidence-note not edit):
- **LNG Canada T1** — GIIGNL 7.0 (T1 only) vs GEM 14.0 (T1+T2; T2 started 2025)

FSRU/regas nameplate-vs-sendout deltas (batchable, §3.6 — peak vs baseload):
Sumed/Ain-Sokhna 11.4/8.0, South Hook 19.5/15.6, Oman Qalhat 7.8/11.4, Dörtyol
5.7/7.5, Hong Kong 4.4/6.1, Damietta 3.4/4.99, Old Harbour 2.8/3.6, Inkoo 2.7/3.68,
Gate 9.9/11.76, Singapore Jurong 9.0/11.0, Moheshkhali 3.8/4.5, Wilhelmshaven TES
4.5/3.31, Plaquemines Ph1 11.3/13.33, Yung-An 12.0/10.5, Al Zour 24.0/22.0,
Sodegaura 29.3/31.4, Quintero/El Musel/Brunei/Rovigo/Acajutla/Thi Vai/Nansha/
Tanjung Benoa/Risavika (all <16%).
Newly-recovered Korea: **Ulsan** 3.5/2.4 (46%) — verify the just-recovered match.

## B. Update — status lag (GEM operating capacity = 0 vs GIIGNL operating)

Mostly already captured by the §3.2.1 narrative pass (`giignl_to_action` sheet):
- **Darwin** 3.7 (idled→operating, Barossa) and **Golden Pass** 15.7/5.2
  (construction→operating T1) — in narrative findings, route to Update.
- Worth a direct check (big, GEM op=0): **Cameron** 11.4, **Lake Charles** 17.9,
  **Guanabara Bay** 6.0, **Ravenna** 3.7, **Aqaba/Sheikh Sabah** 3.8,
  **Tianjin Nangang/Beijing Gas** 12.0, **Dakar (Karmol)** 0.5.

## C. Discovery / name-reconcile — GIIGNL-only (31)

- **Brazil regas cluster** (Pecem 1.9, Port of Açu 5.6, Sepetiba 0.5, São … 3.7) —
  check coverage; possible small Discovery scope.
- **China regas** (Chaozhou, GDLNG, Hua'an, Suntien, Wuhaogou, Yuedong,
  Zhuangyuanao) — several are GEM name-variants (Yuedong=Jieyang, Zhuangyuanao=
  Wenzhou Huagang per narrative) → **name reconciliation**, not new records.
- Singletons: Canada T2 7.0 / Tilbury 0.3, Dominican Andrés, Congo Tango FLNG,
  Myanmar Thanlyin, Norway Mosjøen/Snøhvit (Hammerfest), Puerto Rico Peñuelas,
  Sweden Nynashamn, Türkiye Saros, Malaysia Tenaga Empat, Japan Himeji LNG,
  Russia Kaliningrad/Sakhalin-2 (name match), USA Corpus Christi Stage III.

## D. Ambiguous (15) — manual review

China multi-terminal ports (Caofeidian, Binhai, Qidong, Putian, Diefu, Shennan,
Zhangzhou), Senboku I/II, Map Ta Phut 1/2, Malaysia MLNG (4 cands),
Germany Mukran, Indonesia Cilamaya, and **Calcasieu Pass** (residual: a
capacity-less Trinidad-tagged GIIGNL fragment collides with GEM's already-matched
USA Calcasieu — see extractor note below).

## Extractor changes this batch (verified, ready to commit)

`giignl_extract.py`: detect embedded subtotals on data rows; stitch split
multi-word country labels (South+Korea); reassign greedily-absorbed country
islands (Japan/Indonesia); narrow site→country fallbacks (EG LNG, PNG LNG,
Tortue). `normalize.py`: `korea→south korea`. Net: 21 country corrections, all
verified geographically correct, 19 real terminals recovered into matches, zero
regressions, totals unchanged.
