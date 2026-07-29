# Run record — Captive-power: standby-only becomes YES + hardware taxonomy columns (Americas + Europe rebuilt)

**Date:** 2026-07-28
**Workflow:** Captive-power cross-tracker (`docs/workflows.md` §9, `docs/sops/captive_power.md`) — policy reversal + targeted re-research + a repo improvement. No new area coverage.
**Trigger:** user — "if there is any turbine whatsoever that runs when grid supply fails, that counts as a yes. but I'd like you to add two columns on the left hand side of the deliverable that say what category and a quick description of the hardware… in the `updates_in_database_format`, I want this information and a short description (akin to what's in the `source_tier` and `source_notes` on the `updates_summary` tab) in the left-most columns. redo the americas and europe xlsx files with this."
**Staging:** `batches/staging/captive_power/americas-complete/`, `batches/staging/captive_power/europe/`
**Workbooks:**
- `batches/lng_terminals_batch_20260728_1021_ET_americas-complete-captive_update.xlsx` — 102 updates, 101 data rows
- `batches/lng_terminals_batch_20260728_1021_ET_europe-captive_update.xlsx` — 64 updates, 64 data rows

Both recalc clean, zero `GUARD:` warnings; `pytest` 81 passed.
**Status:** built — awaiting user apply. Supersedes the 2026-07-27 workbooks for both regions.
**Prior run records:** `2026-07-27_americas-complete_captive-power-consolidation.md` (Americas base build), `2026-07-27_europe_captive-power.md` (Europe base build).

---

## 1. The policy reversal

SOP §2b's disposition rule — settled the previous day during the Europe pass — held that
`CaptiveGasPower` is a **current-state** Boolean, so hardware that only runs when grid supply fails
did not qualify. That rule is **reversed**. The user's test is presence, not duty: *any* turbine that
runs when the grid fails is a `True`.

**What survives:** the **fuel gate**. This is what keeps the flip list short and defensible.

| standby hardware | verdict |
|---|---|
| gas-fired | **YES** (new) |
| diesel-only | **NO** (unchanged) |
| fuel not stated in any source | **INSUFFICIENT** (unchanged) |

Rostock and Southern Finland were re-checked under the new rule and stay INSUFFICIENT for exactly
that reason — the sources establish backup generation but never its fuel.

Duty did not become irrelevant; it moved. Present-tense duty now decides the **`captive_category`**
(§2d), not the value.

## 2. What flipped

**Europe — 4 terminals, +7 unit-rows (57 → 64), all green.** These were the four verdicts explicitly
parked as `STANDBY_ONLY` by the rule now reversed, so the flip list was already enumerated:
Eemshaven (3 rows), Montoir (2), Taranto (1), Zeeland ZET (1). Zero `STANDBY_ONLY` verdicts remain in
the Europe increment.

Montoir vindicates the previous pass's OCR work: the *same* Article I-2 line that made it
`STANDBY_ONLY` — "1 groupe électrogène gaz de secours d'une puissance de 1 250 kVA", recovered from a
33-page image-only 1997 scan via `url_verifier.py`'s pdftoppm+tesseract fallback — is now the
citation for a green `True`. Its second georisques URL (`/details/0006300974`) was **deliberately
dropped** from `ref_urls`: it passes `url_verifier` on "MONTOIR" but contains none of the
generating-plant text, so it is not evidence for this value. The reason is recorded in the record's
`source_notes`.

**Americas — 3 flips, +13 unit-rows (89 → 102).** None of these were tagged `STANDBY_ONLY`; the label
postdates the Americas research, so the flip list had to be re-derived by re-reading the negatives:

- **Elba Island** (`T100000130221`, 12 rows, **green**) — a previously *dismissed* NO. The Georgia EPD
  PSD permit documents on-site gas-fired emergency generation, so it flips on a primary source.
- **Placentia Bay** (`T100000131034`, 1 row, **yellow**, `mechanical=True`) — a YES verdict that was
  deliberately left *unstaged* under never-stage-with-doubt, because the EA deferred the choice of
  mechanical driver. But the emergency gas generation in the same filing is **unconditional**, so the
  `True` never depended on the deferred study. `staged_qa_review` item 21 moved
  `unresolved_conflict`/medium → `resolved`/low.
- **Gulf LNG import unit-row** — the interesting one. Its negative rested on **both** now-void grounds
  (the >50 MW floor, removed 2026-07-27, *and* backup-only duty, removed today). The 2019 FERC/DOE
  Final EIS Ch. 2 names "two essential power backup gas turbine generators each with a capacity of 12
  megawatts" — gas-fired. The row now carries its **own** `standby_backup` basis rather than
  propagating the export row's mechanical-drive `True`; `mechanical` → `False`; FEIS URL appended.
  The superseded reasoning is recorded verbatim in the record, not deleted.

**Ksi Lisims is resolved, not outstanding.** The Americas `meta.json` carried an escalation: Ksi
Lisims is staged `True` on 603 MW of approved-but-conditional power barges that build only if the BC
Hydro interconnection slips, which was in tension with the current-state rule. The directive admits
exactly that class. The row stands as staged (yellow, `captive_category=contingency_design`), SOP §2c
updated to match, escalation retired.

## 3. The two new columns

Per the user's ask, `updates_in_database_format` now leads with two **review-only, do-not-paste**
columns, ahead of the existing GOGPT annotation columns:

| column | contents |
|---|---|
| `captive_category` | one of five values (below) |
| `hardware_summary` | one line — count, type, rating where a source states one |

Taxonomy derived empirically from the 166 staged rows, not invented up front:

`mechanical_drive` · `power_generation` · `mechanical_drive+power_generation` · `standby_backup` ·
`contingency_design`

Two rules that fell out of the data:

- **Per-unit-row, not per-terminal.** Gulf LNG forced this: its import row is `standby_backup`, its
  export row `mechanical_drive`. A unit-row with no staged record inherits its terminal's values.
- **Every `hardware_summary` is grounded in that record's own already-verified `source_notes` /
  `MECHANICAL-DRIVE DETAIL:` text.** No ratings were newly asserted, so the new columns introduce no
  new citation surface.

Splits: **Americas** 39 both / 28 mechanical / 19 power / 14 standby / 1 contingency.
**Europe** 44 power / 7 mechanical / 7 standby / 6 both.

## 4. Code

`build_review_package.py` — `build_update_csv_shaped_sheet` generalized from three hard-coded GOGPT
annotation columns to a two-group `left_cols` (`cat_cols + annot_cols`), with `n_left` driving the
`ci0` fill offset and the freeze pane. Category values are looked up per `(terminal_id, unit_id)`
with a terminal-level fallback. The red "suggested GOGPT match" fill was narrowed to `annot_cols`
only, so it can never bleed onto the new columns; header comments got dedicated
`captive_category` / `hardware_summary` branches ahead of the generic empty-column branch.
`STAGED_KEYS["updates"]["known"]` and `SHEET_DESCRIPTIONS` updated.

## 5. Docs updated

- `docs/sops/captive_power.md` — §2b's standby bullet and disposition rule rewritten (Klaipeda is now
  the type case for "standby-capable but load-carrying → `power_generation`"); §2c's
  `contingency_only` escalation resolved; **new §2d** defining the two columns with the five-value
  table and the per-unit-row rule; §3's staging step and the §3 phase-3 Gulf LNG paragraph updated.
- `docs/workflows.md` §9 — standby is no longer listed among §2b's screens; step 4 now requires
  `captive_category` + `hardware_summary`.
- `CLAUDE.md` — captive-power routing note carries the no-duty-floor rule alongside the no-MW-floor
  rule.

## 6. Carried forward (unchanged by this run)

- 13 rows read `CaptiveGasPower = True` with a blank `CaptiveGasPower [ref]` in live GEM (Gulfstream
  1, Plaquemines 3, Sabine Pass 9).
- High-severity qa item: **American LNG Titusville** (`T100000130209`) is `cancelled` in GEM but filed
  a DOE 15-19-LNG semi-annual report 19 Mar 2026.
- Europe's as-designed-on-a-dead-record decision point (8 YES terminals not currently operating) is
  untouched by this change and still stands.
