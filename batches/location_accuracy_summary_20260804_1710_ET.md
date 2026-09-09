# Location accuracy summary — LNG terminals

**Date:** 2026-08-04 (fresh GEM export pulled same day; 1,274 unit rows → 843 distinct terminals)

Part of this year's LNG update is improving the accuracy of terminal lat/lon locations. This memo is the baseline tally of `Accuracy` (exact vs approximate) by status, plus terminals fully missing coordinates.

## Method

- Terminal-level rollup of the unit-row export: each terminal counted under its **most-built unit status** (operating > mothballed > idled > retired > construction > proposed > shelved > cancelled), and counted **exact if any unit row is exact**.
- Accuracy is genuinely per-unit in a handful of records — 8 terminals have units with differing coords/accuracy (e.g. Qatar North Field: NFE trains exact, NFS/NFW approximate; Das Island: operating trains exact, the debottlenecking unit approximate) — so the unit-level picture is slightly larger than these terminal-level counts.

## Accuracy by status (terminal level)

| Status | Exact | Approximate | Blank | Total |
|---|---|---|---|---|
| operating | 235 | 24 | 0 | 259 |
| construction | 36 | 29 | 0 | 65 |
| proposed | 30 | 120 | 1 | 151 |
| shelved | 10 | 60 | 0 | 70 |
| mothballed | 6 | 1 | 0 | 7 |
| idled | 5 | 3 | 0 | 8 |
| retired | 3 | 5 | 0 | 8 |
| cancelled | 27 | 246 | 2 | 275 |
| **All** | **352** | **488** | **3** | **843** |

## Terminals fully missing lat/lon (3, all also blank Accuracy)

- AGP LNG Terminal (United States, proposed) — T100001061234
- New Fortress Angola LNG Terminal (Angola, cancelled) — T100000130823
- Singapore Offshore LNG Terminal (Singapore, cancelled) — T100000130889

## Observations for the accuracy-improvement work

- **High-value gap: 24 operating + 29 construction terminals still marked approximate** (~53 built or building sites). Physically visible facilities — per the georeference ladder (workflows §10) these should all be resolvable to `exact` via mapping services/OSM.
- The 120 approximate proposed terminals are a bigger pile, but many legitimately stay approximate (never-built sites).
- Spot-check candidate: coordinate-sharing across units marked `exact` — e.g. 4 of New Fortress Altamira's 5 units share identical coordinates yet all claim `exact`, while units 2–5 sit ~18 km from unit 1.

## Tooling

- `scripts/location_accuracy_audit.py` + prior deliverable `batches/deliverables/location_accuracy_audit_20260729_1146_ET.xlsx` (2026-07-29) — rerun against a fresh export for a review workbook of the approximate/blank terminals.
