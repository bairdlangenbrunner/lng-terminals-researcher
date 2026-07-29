# Run record — Captive-power cross-tracker: remainder of the US + all of the Americas

**Date:** 2026-07-27
**Workflow:** Captive-power cross-tracker (`docs/workflows.md` §9, `docs/sops/captive_power.md`), terminal-first.
**Trigger:** user — "do the rest of the US now, and all of the americas generally".
**Staging:** `batches/staging/captive_power/americas/`
**Workbook:** `batches/lng_terminals_batch_20260727_1330_ET_americas-captive_update.xlsx` (recalc clean)
**Memo:** `batches/captive_power_memo_20260727_1330_ET_americas.md`
**Status:** built — awaiting user apply.

---

## Plan

Fourth and final Americas increment, closing out the workflow's first hemisphere:

1. Scope from the fresh export: every US LNG terminal **outside** the Gulf (already done in the
   Louisiana / Texas / US-Gulf increments) — East Coast, West Coast, Alaska, inland — plus every
   non-US country in the Americas.
2. Compute GOGPT colocation priors (`captive_power_colocation.py`) as a **prior, not a filter**;
   crawl terminal-first.
3. Fan out terminal-first researchers in batches, each returning a structured verdict per terminal.
4. Orchestrator QC gate over every cited URL on every YES record before staging anything.
5. Author the five staging JSONs, build, recalc, memo, run record, `meta.json`.

## Scope

45 terminals across 15 jurisdictions: United States (non-Gulf), Canada, Mexico, Puerto Rico,
Dominican Republic, Jamaica, Panama, Colombia, Brazil, Chile, Peru, Argentina, Trinidad and Tobago,
El Salvador, Venezuela.

## Outcome

**12 confirmed captive; 32 `CaptiveGasPower` unit-rows staged** (25 green, 5 blue = already `True` and
re-verified unchanged, 2 yellow). 11 confirmed NO, 8 insufficient, 14 screened-not-researched
(cancelled-and-never-built or no design detail in existence). **Zero `PowerPlantsSupplied`.**
17 `qa_review` items, 2 high-severity.

Staged terminals: Kenai (2 rows), LNG Canada (2, blue), NF Altamira (5), Alaska LNG (3, blue),
Peru LNG (1), Costa Azul (3), Firebird (1, yellow), Atlantic LNG (5), Goldboro (2), Cove Point (3),
Ksi Lisims (1, yellow), Argentina LNG (4).

**The generalisable finding: the axis is grid access, not geography.** Every terminal that can reach a
large hydro or utility grid chose electric drive and said so in a regulatory filing (Tilbury, Cedar,
Woodfibre, Summit Lake, Placentia Bay). Every terminal that cannot generates its own power at scale
(Kenai, Alaska LNG, moored FLNGs, the pre-electrification Canadian projects). Caribbean/island
terminals are mostly the *opposite* relationship — they exist to feed a power station, which is
`PowerPlantsSupplied`. **For a grid-connected North American project after roughly 2015, the prior
should be NO.**

Best find: **Goldboro LNG** — Nova Scotia EA states a "180 MW Power Plant" with "On-site (gas turbine)
power generation to support the LNG facility", and GOGPT's independent record agrees at 180 MW exactly.
`mechanical = False` deliberately: ~640 MW of Frame 7 mechanical drive also exists, but the YES rests
on the separate electric plant.

## What the QC gate caught

The gate earned its cost. 38 token checks, 35 PASS / 3 FAIL, all four retry-casualty citations
recovered.

1. **Argentina LNG's 66 MW was wholly unsupported** — no cited URL contains "33 MW" or "66 MW";
   `rivieramm.com` is live-dead (110 bytes) and its Wayback copy is about **Gimi**, a *different* Golar
   FLNG, quoting 26 MW. `electric_mw` blanked, two URLs dropped; the YES survives green on the
   well-sourced mechanical side (4× GE PGT25+G4, ~136 MW shaft, off-grid moored FLNG).
2. **Alaska LNG cited a document that does not contain its claim** — FERC FEIS Volume 1, verified in
   full (17.2 MB / 1,927,950 chars): zero "turbine generator", zero "N+1", "124" only as page numbers.
   Dropped; AGDC Resource Report 1 carries the whole claim verbatim, so it stands as a single
   primary/regulatory green.
3. **A false-PASS mechanism** — `['800,000','ISO horsepower']` passed on unrelated co-occurrence
   (800,000 is cubic yards of dredge spoil). Real figure: **298,000 ISO hp** across six GTP units.
4. **Two verdict inconsistencies**, both overridden with the researcher's text preserved verbatim in
   `_orch`: Placentia Bay YES → not staged (driver study explicitly deferred = same state as AMIGO
   FLNG, which scored INSUFFICIENT); TGS Puerto Galván NO/green → INSUFFICIENT ("undisclosed in any
   public source found" is absence of evidence, not a positive NO).

## Two verifier lessons (carry into the SOP / scripts README)

- **No hyphen/space folding and no accent folding.** `SGT-400` FAILs against printed "SGT 400"; ASCII
  `Gatun` FAILs against "Gatún". Two of the three FAILs were this, not citation defects.
- **Multi-token checks validate each token independently**, so unrelated co-occurring tokens can
  manufacture a PASS. **Bare numbers are weak tokens** — prefer distinctive multi-word phrases.

Also from this run: BC EAO rate-limits aggressively (expect retries), and background-agent `.output`
files are JSONL transcripts, not final text — recover returns by filtering `type=="assistant"` →
`content[].type=="text"`.

## Follow-ups routed out of this batch

High-severity, both "the world moved and GEM did not":

- **Argentina LNG is `proposed` but phase 1 reached FID** (RIGI certificate, 30-year export permit,
  20-year ~US$13.7bn Hilli charter, Seatrium mooring contract starting Q3 2026 for a 2027 start; second
  FLNG MK II on the **Fuji LNG** hull — *not* Gimi — FID ~Aug 2025). Deliberately not staged here:
  edit lane is `CaptiveGasPower` only, and a status change needs the Update workflow's timeline pull.
- **Bahía Blanca is `mothballed`/YPF but the Tango FLNG barge is gone** — sold to Eni Aug 2022,
  redeployed to Marine XII offshore Republic of Congo, first gas Dec 2023. Vessel-reassignment case:
  run `fsru_sync_check.py` and check GEM's Congo-side record.

Medium: Repsol has owned **100%** of Saint John LNG since 2021 (GEM shows 75/25 with Irving Oil);
`PowerPlantsSupplied` blank on Peñuelas and San Juan despite documented purpose-built relationships
(off-lane here, never staged from a captive batch); Summit Lake PG is an **inland** railed-container
site — a marine-scope question of the Dar es Salaam class (captive verdict NO either way); Kitsault now
pitched as a ~C$40bn dual-pipe oil-and-gas corridor, not an LNG terminal; Vista Pacífico and
Atlantic LNG Train 1 status changes; Sycar Venezuela's shelved status rests only on gem.wiki
(never citable).

## Open decision left to the reviewer

**Should documented NO verdicts be staged as `CaptiveGasPower = "False"`?** Four negatives here are
green-quality (Tilbury, Cedar, Woodfibre, Summit Lake — all documented grid-fed electric drive).
Precedent across three applied batches is positives-only, so this pass follows it; all 45 verdicts sit
on the review-only `terminal_first_priors` tab regardless. If the answer is yes, those four are a
one-line addition and the question applies retroactively to LA / TX / US-Gulf negatives too.

## Americas status

**Complete.** Louisiana (2026-07-09) → Texas (2026-07-10) → US Gulf remainder (2026-07-27) → this
batch. Next hemisphere is the reviewer's call.
