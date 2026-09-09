# 2026-08-02 — Natalia-format captive threshold screens, all remaining regions

## Ask

After delivering the Europe/Americas `missing_terminals` companion to Natalia
Fretz's `Captive PPs_Europe_Americas_Natalia_07.31.2026.xlsx`, extend the same
Qualifying/Excluded MW-threshold screen to every remaining region — Asia,
Middle East/Gulf, Africa, Oceania — and upload the workbooks to the shared-Drive
"Captive power research" folder (`1AW4LOVCF63NBLdo0UAVZ1_fxe60KeOnc`). A
cron-based restart mechanism was requested in case of usage-limit interruption.

## What ran

- Working dir: `batches/staging/captive_power/_natalia_regional_export/`
  (extract/build scripts, per-region detail dumps + classified JSONs, RESUME.md,
  state.json — all committed as the audit trail).
- Universe per region = terminals with a staged `CaptiveGasPower=True` row in
  the 2026-08-02 full-region captive workbooks (`20260802_1145_ET` asia +
  middle-east-gulf, `20260802_1650_ET` africa + oceania), minus the 94 already
  covered (Natalia's 55 + the 39-terminal companion): asia 30, middle-east-gulf
  10, africa 17, oceania 14 = 71 terminals.
- Rules (her framework generalized): threshold >=50 MW everywhere outside the
  EU's 20; individual >=50 qualifies; aeroderivative/genset fleets and on-site
  power-plant totals qualify on aggregate; named-model class-rating inference
  allowed (Frame 7EA ~85-90 MW etc.); cancelled/shelved -> Excluded "per
  instruction"; documented hardware with no published MW -> Excluded.
- One Sonnet subagent per region drafted the classification; orchestrator
  verified every MW figure against the source dumps and fixed two rows:
  Wheatstone re-based to the aeroderivative aggregate (individual LM6000PF is
  borderline ~45-50), Satu FLNG flipped X->Q (PGT25+G4 = industrial LM2500+G4;
  same class-inference basis as Cameroon FLNG / Corpus Christi).

## Deliverables (Drive folder + batches/deliverables/)

| File | Qualifying | Excluded |
|---|---|---|
| Captive PPs_Asia_08.02.2026.xlsx | 8 | 22 |
| Captive PPs_Middle East-Gulf_08.02.2026.xlsx | 4 | 6 |
| Captive PPs_Africa_08.02.2026.xlsx | 7 | 10 |
| Captive PPs_Oceania_08.02.2026.xlsx | 5 | 9 |

Judgment calls are flagged inline in the Qualifying Basis / Reason cells
(Karaikal unnamed-class gensets; PNG LNG design-sized 59.8 MW vs 44.3 MW base
load; Marsa El Brega mothballed + single-source; MLNG Satu/Dua/Tiga excluded
rather than extrapolating a per-terminal share of the Bintulu complex total).

Outside the universe by design (live-DB Trues with no staged True row): Tango
FLNG (Argentina), Pasca FLNG (INSUFFICIENT re-verification), PAWA PNG (verdict
NO — direction test; grid-supply project).

## Restart mechanism

Session cron (`:09/:49`) + `RESUME.md`/`state.json` pipeline state; the run
finished in one session, so the cron was deleted unused. The state dir remains
the template for resuming any future interrupted export.
