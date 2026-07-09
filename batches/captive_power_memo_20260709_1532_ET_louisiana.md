# Captive-power cross-tracker batch — Louisiana test case (memo)

**Date:** 2026-07-09 (ET) · **Scope:** Louisiana (test case) · **Mode:** LNG staging + memo
**Workbook:** `batches/lng_terminals_batch_20260709_1532_ET_louisiana-captive_update.xlsx`
**Run record:** `batches/run_records/2026-07-09_captive-power_louisiana-test-case.md`

## What this batch did

Matched every Louisiana LNG terminal to colocated GOGPT gas power plants (geo + name +
captive flags), then web-researched the 9 Tier-A + 1 Tier-B pairs against the strict captive
definition (on-site, >50 MW, powers the terminal/liquefaction; partial counts). **Scope
decision adopted this batch: mechanical-drive liquefaction turbines count as captive power**
(not only electricity generators) — so all 10 pairs are in scope and Woodside is included.

Every cited URL passed `url_verifier.py` (value-checked, 26/26 PASS). No gem.wiki / no
GEM-derivative sources.

## LNG-side edits staged (in the workbook — you apply manually)

`CaptiveGasPower = True` + a `PowerPlantsSupplied` description (with paired `[ref]`) on **all
unit-rows** of all 10 terminals; plus one confirmed status fix. Before this batch only CP2 and
Calcasieu Pass carried `CaptiveGasPower=True` (both with a blank `[ref]`, now filled).

| Terminal | CaptiveGasPower | Confidence | Note |
|---|---|---|---|
| Calcasieu Pass | already True → [ref] filled | green | 720 MW CCGT (FERC DEIS + DOE FEIS + sponsor) |
| Plaquemines | already? → set True | green | 2×720 MW CCGT/phase; 2,860 = 4-unit rollup |
| CP2 | already True → [ref] filled | green | 1,470 MW approved + 720 MW Phase-3 proposed |
| Gulfstream | blank → True | green | 275 MW CCGT (FERC application + 2 trade) |
| Commonwealth | blank → True | green | ~120 MW electric plant; see capacity note |
| Sabine Pass | blank → True | green | on-site GTGs (DOE EA + EPA); import-origin terminal |
| Argent | blank → True | **yellow** | e-drive LM9000 gensets; capacity not public (single-origin) |
| Delfin FLNG | blank → True | green | onboard/floating; +FID fix below |
| Woodside | blank → True | green | mechanical-drive only; site power is grid-fed (see note) |
| G2 (cancelled) | blank → True | **yellow** | historical; NET Power Allam-Fetvedt island |

**Status fix — Delfin FLNG T1:** `FIDStatus Pre-FID → FID` (confirmed FID reached 2026-06-03,
$5B, first FLNG vessel; company release + independent trade, both PASS). `FIDYear` already 2026.
The lifecycle `Status` was **left at `proposed`** — FID ≠ construction per the methodology, and
the FID announcement doesn't assert construction start / NTP. Recommend a follow-on Update to
flip `Status → construction` once an explicit construction-start source is found (this is the
divergence that GOGPT already reflects: GOGPT power plant = construction).

## GOGPT-side observations (memo only — no GOGPT staging path this batch)

1. **GOGPT is ahead of the LNG tracker on captive-flagging** — 10 captive-flagged GOGPT plants
   in LA vs. 2 LNG `CaptiveGasPower=True` before this batch. The LNG-side edits above close that gap.

2. **Capacity semantics — mechanical-drive vs electric generation.** Several GOGPT "power
   station" MW figures aggregate mechanical-drive refrigeration-compressor turbines (which drive
   liquefaction directly) rather than a dedicated electricity-generating plant. Under the adopted
   "mechanical-drive counts" scope we kept the GOGPT aggregates, but flag the split for GOGPT:
   - **Woodside (430.4 MW)** — this is purely 8× LM6000PF+ mechanical compressor drives; the site's
     *electricity* is grid-supplied (Entergy 230 kV, per FERC FEIS). There is **no** electricity-
     generating plant. Consider tagging this GOGPT record as mechanical-drive, not a power station.
   - **Commonwealth (438.6 MW)** — dedicated electric plant is only ~120 MW (DOE FEIS); the balance
     (~348 MW) is mechanical compressor-drive turbines.
   - **Sabine Pass (1,665.6 MW / 8 units)** — not stated in any primary source; likely conflates
     mechanical compressor turbines with the power-gen turbines. Worth a GOGPT capacity review.

3. **`captiveIndustryType` tagging is inconsistent** — only Argent uses the new id 56 ("LNG
   production/liquefaction"); the others use "other" / "oil & refining". Not reliable as a filter.

4. **Capacity unverified against primaries (LNG-side left as-is / documented, not overwritten):**
   Argent 675 MW (single Baker Hughes announcement), Sabine 1,665.6 MW, G2 300 MW (design was
   >1,000 MW; risk of conflation with NET Power's Texas plant).

5. **Not a captive-power issue but noted:** several crude-*oil* terminals (NOLA Oil, NuStar/Plains
   St. James, Plaquemines Oil, Louisiana Offshore Oil Port) sit in the LNG *export* tracker.

## Recommendation on scaling past Louisiana

The matcher + research pattern worked cleanly on LA (9/10 true-positive captive pairs; the one
screened-out false positive, Clean Hydrogen Works, was correctly rejected). Recommend scaling
next to the other US Gulf export states (Texas first — Corpus Christi, Freeport, Golden Pass,
Rio Grande, Port Arthur), where the same Venture-Global/Cheniere-style electric-drive and
e-drive designs dominate and the method should transfer directly. The mechanical-vs-electric
capacity question (point 2) will recur and is worth resolving with GOGPT before a wide sweep.
