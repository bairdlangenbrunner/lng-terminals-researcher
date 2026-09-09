# 2026-07-29 — QC pass, Warda's Southern Asia scope

**Plan:** full four-pass QC (SOP docs/sops/qc.md) over Warda Ajaz's 5 assigned countries — Bangladesh, India, Iran, Pakistan, Sri Lanka (62 terminals / 77 unit-rows). Fresh export pulled same day. Spot-check via 4 Sonnet subagent groups (20 unit-rows); apply-check run off-label against the never-applied 2026-07-17 `south-asia-iran_exhaustive_update` batch (comparing the draft's research to Warda's independent live-DB edits).

**Outcome:** complete. Memo at `batches/qc_20260729_1533_ET.md`; evidence in `batches/staging/qc-warda-southern-asia/` (`staged_qc_findings.json`, `staged_qc_spotchecks.json`, per-country sweep JSONs, `applycheck.json`).

Headlines:
- Link-rot: no country over the 25% threshold (worst Pakistan 11.9%); giignl.org rot = 28 of the 73 dead citations (mechanical mirror repair).
- Spot-check: 56 cells — 35 supported / 13 unsupported / 8 stale; formally trips §6's 10% unsupported threshold but 9 of 13 are citation defects with independently-correct values. 4 genuine value questions (Moheshkhali owner backwards vs Excelerate BOOT, Jaigarh status doubtful, GasPort FSRU 2 capacity + proposed/ShelvedYear contradiction, Summit onshore owner ref miscited).
- Dahej: Petronet's 5-mtpa expansion commissioned 2026-03-31 — GEM still 17.5 mtpa / Phase 2 `construction` (matches the 07-17 draft's not-applied staged edit).
- Summit Matarbari FSRU vs LNG Terminal: NOT duplicates; RPGCL-overlap follow-on flagged.
- Mashal LNG `Capacity [ref]` in live DB cites banned abarrelfull.
- Stopped at SOP §4 step 9 — awaiting user's pick of follow-up batches.
