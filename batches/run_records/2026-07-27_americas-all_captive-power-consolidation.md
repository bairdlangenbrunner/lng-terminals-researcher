# Run record — Captive-power: the four Americas increments consolidated into one deliverable

**Date:** 2026-07-27
**Workflow:** Captive-power cross-tracker (`docs/workflows.md` §9, `docs/sops/captive_power.md`) — consolidation, no new research.
**Trigger:** user — "you've done an lng captive power pass now across US states and all of the americas. can you combine all of those results into a single americas one, if you haven't already?"
**Staging:** `batches/staging/captive_power/americas-all/`
**Workbook:** `batches/lng_terminals_batch_20260727_1411_ET_americas-all-captive_update.xlsx` (recalc clean, no `GUARD:` warnings)
**Memo:** `batches/captive_power_memo_20260727_1411_ET_americas-all.md`
**Status:** built — awaiting user apply.

---

## What was asked, and what existed

No combined Americas deliverable existed. Four per-area workbooks did: Louisiana (2026-07-09),
Texas (2026-07-10), US Gulf remainder (2026-07-27) and rest-of-Americas (2026-07-27) — the last of
which is named `…_americas-captive_update.xlsx` but covers only the fourth increment (non-Gulf US +
the non-US hemisphere), which is what made the question worth asking.

## Plan

1. Verify the four increments partition the hemisphere without overlap.
2. Concatenate their five staging JSONs into `captive_power/americas-all/`; author a `meta.json` with
   a `consolidates` pointer.
3. Fresh GEM pull, build, recalc.
4. One hemisphere-level memo that consolidates rather than repeats the four; mark the four source
   metas `superseded`.

## Outcome

**One workbook, 88 staged unit-rows across 29 terminals** (87 `CaptiveGasPower` + 1 `FIDStatus`),
77 terminals on `terminal_first_priors`, 62 `neighboring_plants` rows, 64 `gogpt_candidates` rows,
27 `qa_review` items. Zero `PowerPlantsSupplied`. The merge is clean — **zero duplicate
`(unit_id, field_name)` pairs** and **zero duplicate `terminal_id`s** in the review tabs.

No verdict, citation, confidence or note was rewritten. Two mechanical corrections were applied, both
forced by the fresh export (below).

## The fresh pull turned this into an incidental apply-check — three findings

1. **Louisiana is already applied** (9 of 10 terminals; G2 LNG, yellow/cancelled, was not). Texas, the
   US Gulf remainder and the rest of the Americas are not. Every `old_value` was refreshed against the
   fresh CSV and the **25 already-landed rows recoloured blue**, with the original per-area confidence
   preserved verbatim in `source_notes`. Without this the paste sheet would have shown 25 rows as
   "blank → True" against a DB that already reads True.

2. **The ref half of the Louisiana apply never landed on 13 rows** — Gulfstream (1), Plaquemines (3),
   Sabine Pass (9) read `CaptiveGasPower = True` with a **blank `CaptiveGasPower [ref]`**. Those rows
   say so in `source_notes`: blue, but still actionable. An unsourced `True` sitting in the tracker is
   exactly what the ref half exists to prevent.

3. **Three ref-MERGE violations, fixed** — staged citation sets that would have overwritten a URL
   already in GEM:
   - **CP2 LNG** (3 rows): FERC eLibrary accession 20260324-5193 **carried forward**. Live (HTTP 200)
     but a JS-rendered filelist page, so `url_verifier` cannot content-check it — an existing citation
     preserved under the merge rule, not a new one, and flagged as such in the note.
   - **Delfin FLNG `FIDStatus`** (targets `FIDYear [ref]`): the DOE April-2026 progress report
     **carried forward**, re-verified PASS.
   - **Alaska LNG** (3 rows): FERC FEIS Volume 1 **declared** in `dropped_urls_dead` — the
     rest-of-Americas QC gate had already proven by full-text read (17.2 MB / 1,927,950 chars) that it
     does not contain the claim, but the drop was undeclared.

## Repo fix — the ref-drop guard was blind to the captive record shape

`warn_ref_url_drops` only inspected records whose `field_name` ends in `[ref]`. A captive-power record
is a **value** record (`field_name = CaptiveGasPower`) carrying its citations in `ref_urls`, so the
existing ref cell never appears in `old_value` and the guard could not see it — which is how three
undeclared drops reached built workbooks.

`scripts/build_review_package.py` now takes `gem_csv_path` in `warn_ref_url_drops` and, for a value
record carrying `ref_urls`/`ref_url`, reads the target ref cell (`ref_field`, else `<field> [ref]`)
from the fresh export and applies the same merge check. New helper `_csv_ref_cells`. Verified both
ways: the guard reproduces all three violations when run against the un-fixed per-area staging dirs,
and is silent against the corrected consolidated one. Test suite green (81 passed).

## Bookkeeping

- The four source `meta.json`s are now `status: "superseded"` with `superseded_by:
  "captive_power/americas-all"`; they remain the per-increment audit trail and keep their own memos and
  run records.
- Coverage-ledger nicety: `coverage_status.py` breaks a same-date tie by glob order, so the per-country
  "Last captive" column still names `captive_power/americas` rather than `…/americas-all`. Same date,
  same coverage — cosmetic, left alone.
- The interim 14:05 build (before the apply-check corrections) was moved to `batches/old/`.

## Americas status

**Complete and consolidated.** One workbook to apply. Next hemisphere is the reviewer's call —
Asia-Pacific is where the mechanical-drive-dominant pattern should transfer most directly.
