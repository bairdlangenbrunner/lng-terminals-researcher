# 2026-08-01 — captive-power cross-tracker, Middle East/Gulf (11 countries)

## Plan

Fifth regional increment (after us-gulf → americas-complete, europe, asia). Scope per
`batches/staging/captive_power/_kickoff_middle-east-gulf.md`: Bahrain, Iran, Iraq, Israel,
Jordan, Kuwait, Lebanon, Oman, Qatar, UAE, Yemen — 34 terminals / 55 unit-rows. Terminal-first
crawl per SOP + workflows §9: fresh 2026-08-01 pull, deterministic GOGPT priors + nearest-2
neighbors from the GOGPT Postgres, 5 dispatch shards (max 8 terminals each), general-purpose
sonnet subagents, LNG-side edits only (`CaptiveGasPower` + ref, never `PowerPlantsSupplied`).
Batch FSRU convention: the vessel's onboard generation IS the captive question, separate from
the shore-side direction test.

## Status / how it ran

- 5/5 shards completed in one session (52–85 tool uses each); **recovery pass determined a
  documented no-op** — every INSUFFICIENT is a genuine source dead-end (paywalled OTC/IEEE
  papers, Iran sanctions opacity, undisclosed FEED content), not exhausted budget.
- **QC gate**: **Hadera overturned NO→INSUFFICIENT** (shard returned a green direction-test NO
  with the Excelsior's onboard-generation fuel unconfirmed — violates the fuel gate + the FSRU
  convention; shore-side NO preserved as a documented split finding, full overturn trail in
  `shard_results/shard_04_israel-lebanon.json`). Citation repairs: QatarEnergy (N) 2×OGJ =
  one origin → Baker Hughes Frame 9/1E vendor PDF added; Mina Al-Ahmadi Igloo inference closed
  via the full Golar-fleet dual-fuel enumeration (2 publishers); Aqaba strengthened to green
  with the vessel-specific Energos fleet page; Iran NIOC `hybrid_basis=grid_export`; gem.wiki
  structural flags (6) all inspected → compliant anti-circularity prose, no changes.
- **Permanent tooling fix**: `scripts/url_verifier.py` now detects Incapsula/Imperva-style
  bot challenges served as HTTP 200 text/html (body markers `_Incapsula_Resource` et al.),
  demotes a pdf-URL-with-HTML-body to HTML, and routes to the existing Wayback fallback —
  fixes the bakerhughes.com false-FAIL ("PDF has no extractable text"). 81 tests pass.
- Assembly via committed `_assemble_middle_east_gulf.py` (reproducible from `shard_results/`).

## Outcome

- Verdicts (34): **10 YES / 10 NO / 10 INSUFFICIENT / 4 SCREENED**. YES: QatarEnergy (N)+(S),
  Oman Qalhat, Das Island, Yemen LNG (mechanical=True family); Aqaba, Khor Al-Zubair, Mina
  Al-Ahmadi (FSRU onboard DFDE); Iran NIOC (grid_export hybrid) + South Pars.
- Workbook: `batches/lng_terminals_batch_20260801_1237_ET_middle-east-gulf-captive_update.xlsx`
  — 26 staged unit-rows / 10 terminals (22 green / 4 yellow), qa 34, priors 34, candidates 34,
  neighbors 56. Build clean (no GUARD/REF-DROP), recalc clean, tests 81 passed,
  fsru_sync_check gem_only short-circuit.
- Memo: `batches/captive_power_memo_20260801_1239_ET_middle-east-gulf.md` (GOGPT for Natalia:
  1 ADD Das Island 36 MW / 1 MAYBE NewMed / 8 REVIEWER CALL / 24 DO NOT ADD; qa flags incl.
  Al-Faw Hull-3407 vessel misassignment, Khor Al-Zubair 2027 slip, NewMed FID clarification,
  Az-Zour North future PowerPlantsSupplied candidate).
- Uploaded to the user's shared-Drive folder per instruction (with the americas-residue
  workbook). Not yet applied to GEM. meta.json → status `built`.
- Sister scope built same session: americas-residue (own run record). Remaining increments:
  Africa, Oceania.
