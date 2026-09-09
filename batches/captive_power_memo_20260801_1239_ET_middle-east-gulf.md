# Captive-power memo — Middle East/Gulf (11 countries)

**Stamp:** 2026-08-01 12:39 ET
**Workbook:** `batches/lng_terminals_batch_20260801_1237_ET_middle-east-gulf-captive_update.xlsx`
**Staging:** `batches/staging/captive_power/middle-east-gulf/`
**Fifth regional increment** after us-gulf → americas-complete, europe, and asia. Remaining:
Africa, Oceania. (Türkiye was covered in the europe increment, Turkmenistan in asia; Egypt
belongs to the future africa increment. Sister scope built the same session:
`americas-residue` — separate memo/workbook.)

---

## What this is

**34 terminals / 55 unit-rows across 11 countries** (Bahrain, Iran, Iraq, Israel, Jordan,
Kuwait, Lebanon, Oman, Qatar, UAE, Yemen), terminal-first crawl sharded 5 ways (max 8
terminals/shard) on a fresh 2026-08-01 pull. No recovery pass was needed: all five shards
completed their full worklists (52–85 tool uses each), and every INSUFFICIENT documents a
genuine source dead-end, not exhausted budget. `_assemble_middle_east_gulf.py` (committed
alongside the shard results) reproduces the five canonical staging JSONs.

| | count |
|---|---|
| staged unit-rows | **26** (all `CaptiveGasPower=True`; no overturns — nothing in scope carried a pre-existing True) |
| terminals with a staged edit | **10** |
| staged confidence | 22 green / 4 yellow |
| `terminal_first_priors` | 34 (every terminal, verdict + evidence) |
| `gogpt_candidates` | 34 (1 ADD / 1 MAYBE / 8 REVIEWER CALL / 24 DO NOT ADD) |
| `neighboring_plants` | 56 (nearest-2 GOGPT per terminal, 30 km cap, `gogpt_plant_id` on every row) |
| `qa_review` | 34 (10 INSUFFICIENT + 24 update-batch flags) |
| `PowerPlantsSupplied` | **0** (never staged by this workflow) |

Verdicts over all 34: **10 YES / 10 NO / 10 INSUFFICIENT / 4 SCREENED**. Build emitted no
`GUARD:`/`REF-DROP:` warnings; `recalc.py` clean; test suite green (81 passed).
`fsru_sync_check.py` ran in `gem_only` mode (no carrier backend; graceful short-circuit).

## Where the YES verdicts are

Two structural families, as in Asia:

- **Liquefaction complexes with mechanical-drive/power islands** (`mechanical=True` on 5
  terminals, 18 of the 26 staged rows): **QatarEnergy LNG (N) and (S)** — the textbook Ras
  Laffan case, GE Frame 9E (~132 MW ISO) mechanical drives on the mega-trains (with motor-
  generator surplus-power export) and Frame 5C/5D/7EA on the legacy trains; **Oman Qalhat** —
  a 120 MW MAN 51/60 gas-engine power plant (replacing the original Frame 6 turbine-generator
  station) plus Frame 6/7 compressor drives; **Das Island** (36 MW GE Frame 6 plant + legacy
  Frame 5 units + mechanical drives); **Yemen LNG** (heavy-duty gas-turbine 1×100% shaftline
  drives at Balhaf; the GE 11 MW induction motors are starter/helper only and are excluded
  from `electric_mw` per the brief).
- **FSRU onboard generation** (`power_generation`): **Aqaba** (Energos Eskimo, vessel-specific
  DFDE), **Khor Al-Zubair** (DFDE), **Mina Al-Ahmadi** (Explorer's documented 2015-16
  dual-fuel genset module — vessel-specific — plus Golar Igloo covered by the exhaustively
  enumerated Golar fleet: 14× Wärtsilä 50DF + one 34DF + one 20DF across all 16 managed
  vessels, two publishers). The batch convention: the vessel's onboard generation IS the
  captive question for an FSRU terminal, separate from the direction test on its send-out gas.
- Iran contributes two YES on its own pattern: **Iran NIOC LNG** (the 500 MW MAPNA power
  station built for the suspended project; currently exporting to the grid, hence
  `hybrid_basis=grid_export` on all three unit-rows) and **South Pars** (complex-wide gas
  turbine generation documented before suspension).

## What the region taught the workflow

- **Hadera was overturned NO→INSUFFICIENT at the orchestrator QC gate** — the shard returned a
  green NO on the direction test (grid injection into INGL's national grid, well documented)
  while explicitly unable to confirm the Excelsior's own onboard generation fuel. Under the
  fuel gate (unstated = INSUFFICIENT, never NO) and the batch's own FSRU convention, the
  verdict cannot be NO. The shore-side direction-test finding is preserved in the record; the
  open vessel-side item (Excelsior aux-generation fuel; OTC-18398 is paywalled and likeliest
  to settle it) is in `qa_review`.
- **Iran is the mirror of India**: sanctions-era opacity produced 3 of the 10 INSUFFICIENT
  (Iran FLNG, North Pars, Persian NIOC — all red) where Asia's India found regulatory filings
  enumerating GTGs. The 4 SCREENED (Kangan, Qeshm, Sharjah, Eilat) are concept-stage/
  never-designed projects with no engineering content to evaluate.
- **`url_verifier.py` gained Incapsula-interstitial detection** (permanent fix, this batch):
  bakerhughes.com serves a 200 text/html bot challenge for a `.pdf` URL, which previously
  mis-read as "PDF has no extractable text." The verifier now demotes a pdf-URL-with-HTML-body
  to HTML, detects challenge body markers (`_Incapsula_Resource` et al.), and routes to the
  existing Wayback fallback — the Baker Hughes Frame 9/1E vendor PDF (which names Qatargas/
  RasGas as "the world's largest mechanical-drive application") now PASSes.

## Sourcing notes for review

- **QatarEnergy (N)**: the two OGJ refs share one publisher, so the Baker Hughes Frame 9/1E
  vendor PDF was added at QC as the independent primary origin. Both Qatar records also cite a
  GASTECH-style technical paper hosted at pdfcoffee.com (a document-mirror host; content is a
  genuine GE/Qatargas/RasGas paper, but the canonical conference copy would be a better home
  if ever found).
- **Al Zour (NO, yellow)**: the offshore-technology grid-feed claim verified via Wayback on the
  weaker token "power substations" after the exact hyphenated substation names failed strict
  match — the sentence-level claim is confirmed, but it is a single source, hence yellow. NO
  verdicts stage nothing, so this only affects the priors tab.
- **Aqaba** was strengthened at QC from a single fleet-level source to green with the
  vessel-specific Energos Infrastructure fleet page (sentence-level attribution confirmed).

## qa_review highlights (route to Update batches, NOT this one)

- **Al-Faw FSRU (Iraq)**: GEM lists vessel "Hull 3407" — multiple sources indicate that hull
  belongs to the **Khor Al-Zubair** vessel; Al-Faw's vessel assignment needs an Update-batch
  correction.
- **Khor Al-Zubair**: startup slipped to 2027 (Iran–Israel–US conflict per Energy
  Intelligence) — planned-start-slip elevation candidate for the next Update batch.
- **NewMed FLNG**: the Jan 2026 Chevron/NewMed FID is the **platform production expansion**
  for the Israel–Egypt pipeline deal, NOT the FLNG — do not read it as FLNG progress.
- **Az-Zour North Phase II/III (Kuwait)**: designed to run primarily on LNG from 2027 — a
  future `PowerPlantsSupplied` candidate on the Al Zour terminal once corroborated; GOGPT's
  captive=True proximity tag on Az-Zour North looks like a GOGPT-side false positive.
- **Aqaba**: the Energos Eskimo has since been chartered to Egypt (Ain Sokhna) — vessel-field
  update candidate.
- **Sheikh Sabah (Kuwait)**: commissioning targeted Q2 2026 by some sources; worth a status
  re-check in the next Update batch.

## GOGPT side — for Natalia (SOP §4a)

`captive_gogpt_candidates.json`: **1 ADD** — Das Island's 36 MW GE Frame 6 plant (+ legacy
Frame 5 units), citable nameplate. **1 MAYBE** — NewMed FLNG (only if it reaches FID with a
Golar-family vessel). **8 REVIEWER CALL** — mostly vessel-mounted FSRU gensets with no
standalone nameplate (Mina Al-Ahmadi, Aqaba, Khor Al-Zubair) and the two QatarEnergy
mechanical-drive complexes (shaft ratings must not be recorded as electric MW). Oman Qalhat's
plant already exists in GOGPT ("New Qalhat LNG power station", 119.7 MW, captive=True) — the
strongest cross-tracker match of the batch.
