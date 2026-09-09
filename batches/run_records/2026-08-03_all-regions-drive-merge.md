# 2026-08-03 — all-regions merge of the captive Drive deliverables

## Plan

User request: in the shared-Drive "Captive power research" folder
(`1AW4LOVCF63NBLdo0UAVZ1_fxe60KeOnc`), (1) merge the regional `Captive PPs_*` files into a
single workbook maintaining the tabs, and (2) combine the six regional
`lng_terminals_batch...captive_update.xlsx` files into one. Also noted: Natalia moved
**Toscana FSRU** to "Excluded" — steam turbines, not aeroderivative gas turbines.

## What was done

- Downloaded the **current Drive copies** of all 12 files (Natalia had edited five of the
  six Captive PPs files that morning; local repo copies were stale).
- Verified `Captive PPs_Europe_Americas_Natalia_updated_08.03.2026.xlsx` fully supersedes
  the 07.31 "redone by BL with missing terminals" supplement (all 39 supplement rows folded
  in), so the merge uses the 08.03 file + the four 08.02 regionals only.
- Confirmed the Toscana move: EU-Qualifying (07.31) → **EU-Excluded** (08.03), reason =
  steam turbogenerators are neither aeroderivative GTs nor gensets. Recorded as the
  confirmed technology gate in her GOGPT screen (captive SOP §4a); LNG-side
  `CaptiveGasPower=True` unaffected — our lane has no technology gate.
- Built and uploaded to the same folder (tool:
  `batches/staging/captive_power/_merge_drive_deliverables.py`):
  - **`Captive PPs_All Regions_08.03.2026.xlsx`** (Drive id `19YvVT918PYHq_DkdvKWtoXYJ2Xl7l7R3`) —
    14 tabs (EU / Russia / Americas / Asia / ME-Gulf / Africa / Oceania × Qualifying+Excluded)
    copied verbatim with styles, widths, freeze panes. Local copy in `batches/deliverables/`.
  - **`lng_terminals_batch_20260803_0929_ET_all-regions-captive_update.xlsx`** (Drive id
    `1CDf7axc0ktiKgFiEZJqYozsuq3uUY38o`) — same-named sheets concatenated across the six
    regional workbooks: 385 updates_summary rows, 384 paste rows, 763 qa_review,
    843 terminal_first_priors, 940 neighboring_plants, 834 gogpt_candidates. README rebuilt
    with aggregated counts and the 105-country union (56 changes / 49 verified). Local copy
    in `batches/`.

## QC

- Header schemas verified identical across all six batch files per sheet before concatenation.
- Cell-fill (confidence color) counts in the merged batch file match the six sources exactly
  (30 blue-tint / 56 yellow-tint / 299 green-tint colored cells).
- Sources were merged as-is — no values re-researched, no URLs re-verified (all cells passed
  verification in their original builds; Natalia's edits are reviewer-authoritative).

## Outcome

Both merged files live in the Drive folder alongside the regional sources. The regional
files remain the granular audit trail; the merged pair is the apply/review convenience view.
