# 2026-07-10 — Vietnam final pass (Asana task close-out)

## Plan

User: "one final pass for Vietnam research" — walk the Vietnam Asana task
(GGIT LNG Update 2026, task 1216449907202757) step by step, map each subtask to
work already done, and close any genuinely unfinished research substeps. Not a
new update/discovery batch — a verification + close-out after the 2026-07-02
exhaustive-update+discovery and 2026-07-09 discovery re-check.

## Asana subtask mapping

- **Copy the template** — done (pre-existing).
- **Research › existing › Compare to GIIGNL** — VERIFIED CLEAN this pass (below).
- **Research › existing › Check possible updates** — worked all 56 Vietnam rows of
  the shared "Possible Updates" sheet (LNG tab); bulk already addressed by the two
  batches; 4 residual open rows researched this pass (below), all resolve to
  no-new-edit.
- **Research › existing › Search for other updates** — done (2026-07-02 exhaustive).
- **Research › Search for new projects** — done (two discovery passes; Hiep Phuoc found).
- **Country wrap up / tracking-sheet / time comment / resources doc** — admin, left to user.

## GIIGNL 2026 comparison — Vietnam slice (CLEAN)

Reused the committed GIIGNL 2026 extract (`batches/staging/recon/giignl2026/giignl_extracted.csv`,
same PDF → deterministic), pulled a fresh GEM export (1,291 rows, 2026-07-10),
re-ran `report_diff.py`. GIIGNL 2026 lists exactly 2 Vietnam terminals, both matched:

- **Cai Mep LNG (Hai Linh)** — GIIGNL 3.0 mtpa / 2024 / Hai Linh 51% + AG&P 49%.
  GEM: 3.0 mtpa operating, parent Hai Linh 51% / Nebula 39.2% / Osaka Gas / JBIC.
  Capacity exact match; "AG&P" report-only delta is aliasing — Nebula = AG&P parent.
- **Thi Vai** — GIIGNL 1.1 mtpa / 2023 / PetroVietnam 51% + Bitexco 39% + Tokyo Gas 10%.
  GEM: Phase 1 1.0 mtpa operating, parent Vietnam Oil & Gas Group 51% / Bitexco 39% /
  Tokyo Gas 10%. 1.0-vs-1.1 = 0.1-mtpa rounding/basis (GEM's cited source stands);
  "petrovietnam" report-only delta is aliasing — Vietnam Oil & Gas Group IS PetroVietnam.

No report-only Vietnam rows (no missed terminal per GIIGNL); GEM-only proposed units
(Thi Vai Phase 2, Vung Tau FSRU) correctly excluded (GIIGNL lists operating only).
Every flagged delta is a matcher aliasing artifact — nothing to edit.

## Possible Updates — 4 residual rows researched (all no-new-edit)

Each verified with ≥2 independent working URLs via `url_verifier.py`; no gem.wiki/GEM cites.

1. **Cai Mep — "AG&P to become sole owner"** (row 2026-04-22). The 2026-04-21
   announcement is an *agreement to acquire* 100% "subject to customary regulatory
   approvals and closing conditions" — NOT closed. GEM's multi-party parent structure
   is correct. No edit; optional qa note to revisit on close. (lngindustry, pgjonline, lngprime — PASS.)
2. **Nghi Son — Greenwell Energy Canada** (rows 2024-12). Speculative: Greenwell's MD
   made a supply/build *suggestion* at a ministry meeting; no award. Nghi Son STILL has
   no selected investor — international bidding failed twice, a 3rd round opened Q1 2026
   (close ~Apr 10 2026). GEM's blank Owner/Parent is correct; do not stage Greenwell.
   (theinvestor, tapchicongthuong, en.vneconomy — PASS.)
3. **Quang Trach III** (rows 2025-12 / 2026-02). NOT a missed terminal — power plant fed
   by piped regas from the existing Vung Ang LNG Terminal (~30 km N), same as Quang Trach II.
   Apr-2026 EVN–PV GAS framework agreement supplies regas LNG from Vung Ang to Quang Trach
   II AND III (from ~Apr 2029). This was already staged in the 2026-07-09 correction
   (Vung Ang T100000131060, PowerPlantsSupplied += "Quang Trach 2/3") and the PDP8 note —
   PENDING APPLICATION: the 2026-07-10 export still shows Vung Ang PowerPlantsSupplied =
   "Vung Ang power station" only. Re-confirmed with vir 150036 + lngprime 189784 (PASS).
4. **"1,500 MW southern Vietnam delay"** (row 2024-09-03, "?"). = Long An I (VinaCapital
   GS Energy), already tracked as Long An I & II. Stale 2024 delay; no action. (theinvestor — PASS.)

## Outcome

- Research side of the Asana task is complete: GIIGNL clean, all Possible Updates
  resolved, new-project discovery done. No new staging produced.
- **One pending live-DB apply carried over from 2026-07-09**: Vung Ang LNG Terminal
  `PowerPlantsSupplied` += Quang Trach 2 & 3 (staged in the 07-09 discovery workbook's
  qa/correction; not yet reflected in the live DB).
- Remaining Asana items are administrative (tracking-sheet "Complete?" checkbox, time-log
  comment, shared Country Resources doc) — left to the user.
- No workbook built (verification pass, no new edits). Fresh export overwrote
  `scripts/gem_export.csv` in place.
