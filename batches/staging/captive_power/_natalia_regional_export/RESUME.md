# Natalia-format regional captive export — resume instructions

Goal: produce four workbooks in Natalia Fretz's Qualifying/Excluded threshold
format — `Captive PPs_{Asia, Middle East-Gulf, Africa, Oceania}_08.02.2026.xlsx`
— and upload each to the shared-Drive "Captive power research" folder
(`1AW4LOVCF63NBLdo0UAVZ1_fxe60KeOnc`, shared drive → `supportsAllDrives:true`).
Companion to `Captive PPs_Europe_Americas_Natalia_07.31.2026.xlsx` and its
`_missing_terminals` companion (both already in that folder).

`state.json` is the source of truth for progress: per-region `status` walks
`extracted → classified → built → uploaded`; append each session wake to
`wake_log`. When ALL four regions are `uploaded`: copy the xlsx files to
`batches/deliverables/`, delete the session cron restart job (CronList →
CronDelete), write the run record, and report.

## Pipeline (all scripts in this dir; run from repo root)

1. **Extract** (done if `<region>_detail.json` exists):
   `python3 batches/staging/captive_power/_natalia_regional_export/extract_region.py <workbook> <region-key>`
   Workbooks: `batches/lng_terminals_batch_20260802_1145_ET_{asia,middle-east-gulf}-captive_update.xlsx`,
   `batches/lng_terminals_batch_20260802_1650_ET_{africa,oceania}-captive_update.xlsx`.
   Universe = staged CaptiveGasPower=True terminals, minus `exclude_ids.json`
   (Natalia's 55 + the 39 already delivered). Expected counts: asia 30,
   middle-east-gulf 10, africa 17, oceania 14.

2. **Classify** → `<region>_classified.json`. One subagent per region (cheapest
   good-enough model, e.g. Sonnet), input = the region's `_detail.json`; the
   ORCHESTRATOR then reviews every row against the detail dump before building.
   Schema:
   `{"qualifying": [{terminal, terminal_id, country, status, hardware_type, individual_mw, aggregate_mw, basis}], "excluded": [{terminal, terminal_id, country, reason, mw_figure}]}`
   Every terminal in the detail file appears exactly once; no facts beyond the
   dump (class ratings like "Frame 7 ~85-90 MW" may be inferred and labeled as
   class ratings, mirroring her Sakhalin row).

   Classification rules (her framework, from her Europe/Americas file):
   - Threshold **>=50 MW** for all four regions (only the EU uses 20 MW).
   - An individual unit >=50 MW qualifies; **aggregate** MW counts for
     aeroderivative-turbine and genset/engine fleets (her aeroderivative/genset
     rules); heavy-duty industrial single units are judged individually.
   - Mechanical drive counts toward qualifying (her Sakhalin-2 precedent);
     note shaft vs electric in the basis.
   - **Cancelled or effectively shelved/abandoned → Excluded "per instruction"**
     regardless of MW (her Placentia Bay precedent); note "would qualify if
     active" when the design MW clears the bar.
   - Documented captive hardware but **no published MW figure → Excluded, "No
     MW figure disclosed"** (her Alexandroupolis / Marshal Vasilevskiy
     precedent) — typical for FSRU onboard-generation Trues.
   - Below threshold → Excluded with the MW figure shown.
   - Statuses: operating/construction/proposed can qualify; mothballed/idle is
     a judgment call — say so in the reason/basis rather than deciding silently.

3. **Build**: `python3 .../build_regional.py <region-key>` — validates the
   roster (fails on missing/extra/dupe terminals), pulls References from the
   detail file, writes the xlsx (Calibri 10, her tab/column layout; ME-Gulf tab
   prefix shortened for Excel's 31-char sheet-name cap).

4. **Upload** (explicitly user-authorized for this task, 2026-08-02):
   `GOOGLE_WORKSPACE_CLI_CONFIG_DIR=~/.config/gws-gem-write GOOGLE_WORKSPACE_CLI_KEYRING_BACKEND=file gws drive files create --params '{"supportsAllDrives":true,"fields":"id,name,webViewLink"}' --json '{"name":"<filename>","parents":["1AW4LOVCF63NBLdo0UAVZ1_fxe60KeOnc"]}' --upload "<path>"`
   (The `+upload` helper 404s on shared drives — use the raw form above.)
   Record the returned file id in state.json. If a region was already uploaded
   (id present), do NOT re-upload a duplicate.

## Notes
- PAWA PNG (verdict NO — direction test), Pasca FLNG (INSUFFICIENT), Tango FLNG
  are live-DB Trues with no staged True row → deliberately outside this
  universe; mention them in the final report, don't add them to the files.
- Terminal-level status strings: join the distinct unit statuses meaningfully
  (e.g. "operating (T1-3); proposed (T4)") using the detail dump's notes.
