# Location accuracy follow-up — what Natalia's pass did and didn't cover

**Date:** 2026-08-07 (fresh GEM export pulled same day; 1,277 unit rows → 846 terminals)
**Follows:** `batches/location_accuracy_summary_20260804_1710_ET.md` (the 2026-08-04 baseline)
**Trigger:** Natalia's 2026-08-07 Slack update; she explicitly skipped terminals
"recently reviewed by other researchers" and "recently reviewed by both of you [Baird
and Amalia]". This memo identifies what that left uncovered.

## Method note — the export cannot answer this question

`LastUpdated` and `Researcher` in the export only move when a researcher marks a unit
**"updated"**, which is not what a coordinate fix does. Natalia's three-day pass edited
**62 LNG plants** but bumped only **11 unit rows**. Any recency split built on those two
columns (including `location_accuracy_audit.py`'s `recent_approximate` / `stale_approximate`
sheets) therefore misreads this work almost entirely.

Provenance here comes from the real audit log instead — `plant_history`, which stores a
full `plantJSON` snapshot per revision with `editor_id` and `modified`. New script:
`scripts/location_edit_provenance.py` (read-only). It walks each LNG plant's snapshots in
time order and records the last revision where `latitude`/`longitude`/`locationAccuracy`
actually changed.

## Progress since 2026-08-04

| Status | Approx (Aug 4) | Approx (Aug 7) | Fixed |
|---|---|---|---|
| operating | 24 | 4* | 20 |
| construction | 29 | 25 | 4 |
| mothballed | 1 | 0 | 1 |
| idled | 3 | 2 | 1 |
| retired | 5 | 5 | 0 |
| **all statuses** | **488** | **464** | **24** |

\* Terminal-level rollup counts a project approximate if *any* unit row is. Three of these
are **mixed** projects whose built units are already `exact` — the approximate flag comes
from a non-operating sibling unit:

- **Das Island** (UAE) — T1–T3 operating `exact`; the *proposed* debottlenecking unit is approximate
- **Engro Elengy** (Pakistan) — operating unit `exact`; the *shelved* expansion is approximate
- **Qatar North Field** — NFE (construction) `exact`; NFS (construction) and NFW (proposed) approximate

So the genuinely-still-approximate operating terminals are exactly the **two** Natalia
reported, both with her notes in the record:

- **Tema FSRU** (Ghana) — "NF 8/6/26: The exact location of the FSRU is not available."
- **Mosjoen LNG Terminal** (Norway) — "NF 8/7/26: … updated the approximate location based
  on this description, but could not find a source which mentions the exact location."

**Her account checks out.** The one thing her message overstates is construction: she
reviewed them, but only **4 of 29** moved to `exact`; **25 remain approximate**, and her
August edits touched only 7 of those 25.

## The gap: 20 terminals whose location Baird set, none re-checked

Natalia touched **zero** of these in August — exactly the skip she described. Full list in
`batches/deliverables/location_provenance_20260807_1242_ET.csv`.

### Still approximate, and building (highest priority — 3)

| Terminal | Country | Baird's edit | Coords |
|---|---|---|---|
| Regasificadora del Pacífico LNG Terminal | Colombia | 2026-05-29 | 3.904541, -77.077035 |
| Hiep Phuoc LNG Terminal | Vietnam | 2026-07-09 | 10.642, 106.7465 (3dp, ~110 m) |
| Quynh Lap LNG Terminal | Vietnam | 2026-07-09 | 19.281864, 105.800903 |

### Still approximate, proposed (2)

Cong Thanh LNG Terminal (Vietnam, 3dp) and Dung Quat LNG Terminal (Vietnam) — both
2026-07-09. Proposed sites may legitimately stay approximate.

### Marked `exact` by Baird, never independently re-verified (8 LNG)

This is the set the accuracy flag now asserts on Baird's judgment alone. Coordinate
*precision* is fine on all of them (4–7 dp), so the risk is placement, not rounding:

- LNG Canada Terminal (operating, 2025-12-08) — 2 units share one coordinate
- Chaozhou LNG Terminal (Huaying) (operating, 2025-05-07) — 2 units share one coordinate
- Adriatic LNG Terminal (operating, 2025-05-27) — 2 units share one coordinate
- Gulf LNG Terminal (US, operating, 2025-04-30) — 2 units share one coordinate
- Penuelas LNG Terminal (Puerto Rico, operating, 2026-07-29)
- San Juan LNG Terminal (Puerto Rico, operating, 2026-07-29)
- Rudong LNG Terminal (China Resources) (construction, 2025-05-20)
- Aguirre GasPort FSRU (Puerto Rico, proposed, 2026-07-29)

The remaining 7 of the 20 are legacy **oil/NGL deepwater-port** records (IMTT St. Rose,
Phillips 66 Beaumont, Blue Marlin, Bluewater Texas, SPOT, Texas GulfLink, JOLT) — out of
LNG scope, same class the ref-sweep set aside.

## Separate finding: 10 LNG terminals marked `exact` on ~1 km coordinates

Found while fixing a precision bug in `location_accuracy_audit.py` (`_dp` counted the
export's zero-padding as significant, so `-93.0100000` graded as 7 dp instead of 2). With
trailing zeros stripped, these carry `exact` on coordinates no better than ~1.1 km — none
are Baird's, and all are operating:

Gorgon (Australia), Revithoussa (Greece), Dabhol (India), Lampung FSRU (Indonesia),
Nusantara Regas Satu (Indonesia), HIGAS (Italy), Kawagoe (Japan), Hammerfest Snohvit
(Norway), Kollsnes (Norway), Tanzania LNG.

Natalia's pass would not have flagged these — they already read `exact`, so they never
appeared on an approximate worklist. They are `exact`-labelled but not exact.

## Suggested next steps

1. Re-georeference the 3 building + approximate terminals Baird last touched (workflows §10
   ladder — all three are real sites, so mapping services/OSM should resolve them to `exact`).
2. Spot-check the 8 `exact` LNG terminals above; the 4 with units sharing a single
   coordinate are the natural first look.
3. Treat the 10 coarse-`exact` terminals as their own worklist — they are the largest
   silent accuracy problem left, and no approximate-based pass will ever surface them.
4. The 25 remaining construction approximates are the biggest built/building pile; 18 were
   last touched by Robert, Amalia, Isabel, Gregor, or Julie.

## Tooling

- **New:** `scripts/location_edit_provenance.py` — location provenance from `plant_history`.
  `--editor Baird --all` reproduces the 20-terminal list above.
- **Fixed:** `location_accuracy_audit.py` `_dp` trailing-zero bug (above).
- Caveat: 14 LNG terminals set `plantLevelLocation = false` (coordinates on the unit rows),
  so plant-level history is blind to them; the script marks them `unit_level`. Only
  **Qatar North Field South** is a built/building gap among them.
