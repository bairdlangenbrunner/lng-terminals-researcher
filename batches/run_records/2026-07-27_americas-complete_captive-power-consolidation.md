# Run record — Captive-power: all Americas into one file + `hybrid_basis` surfaced

**Date:** 2026-07-27
**Workflow:** Captive-power cross-tracker (`docs/workflows.md` §9, `docs/sops/captive_power.md`) — consolidation + one repo improvement, no new research.
**Trigger:** user — "just put ALL of the americas together into a single file... and where are the assumptions you've made about hybrid captive power?"
**Staging:** `batches/staging/captive_power/americas-complete/`
**Workbook:** `batches/lng_terminals_batch_20260727_2005_ET_americas-complete-captive_update.xlsx` (recalc clean, no `GUARD:` warnings)
**Memo:** `batches/captive_power_memo_20260727_2005_ET_americas-complete.md`
**Status:** built — awaiting user apply.

---

## Why there were still two Americas files

The 14:11 consolidation folded four increments into `americas-all`. The 18:27 no-MW-floor mop-up
(`americas-floor-mopup`) was then deliberately kept as a **sibling** rather than merged into it,
reasoning that americas-all was already built and its Louisiana rows already applied, so editing it
in place would desync the built workbook from its staging inputs. That reasoning was sound for
*mutating* americas-all — but it left two files on the desk when the deliverable should be one. The
fix is the same pattern americas-all itself used: a **new** dir that supersedes both.

## Merge

`americas-complete` = `americas-all` (88 updates / 77 terminal_first) + `americas-floor-mopup`
(1 update / 9 terminal_first). Rules, applied by script:

- `staged_updates` — concatenated. Zero duplicate `(unit_id, field_name)` pairs (asserted).
- `captive_terminal_first`, `captive_gogpt_candidates` — deduped on `terminal_id`; **9 and 5
  overlaps** respectively. The mop-up row wins (post-floor-removal re-research), but its ref list is
  **unioned** with the americas-all row's, never replacing it, and the superseded basis is kept in
  `_superseded_prior`.
- `staged_qa_review` — concatenated; zero `terminal_id` overlap. 27 + 3 = 30.

**Coastal Bend justified the union rule.** The mop-up cited two `coastalbendlng.com` URLs — one
self-published origin — where americas-all had conocophillips.com + ogj.com + hartenergy.com. Naive
"newer wins" would have dropped three independent publishers to leave a developer's own press
releases. The merged row keeps all five with the mop-up's stronger basis (developer now names
"cogeneration", retiring the >50 MW-from-scale inference). Both were already yellow, so the mop-up's
stated green→yellow downgrade was moot.

Result: **89 staged unit-rows across 30 terminals**, 77 `terminal_first_priors`, 68
`gogpt_candidates`, 62 `neighboring_plants`, 30 `qa_review`. Zero `PowerPlantsSupplied`.

## The second question: where the hybrid assumptions lived

They lived in **two places, neither visible to a reviewer**:

1. **SOP §2, one bullet** — "Partially-captive counts (a plant that powers the terminal *and*
   exports to the grid)", plus the §2a GOGPT `Captive Non-Industry Use` line.
2. **Per-row `source_notes` prose**, inside fields running 250–2,300 chars.

Nothing in any sheet marked a hybrid verdict. `mechanical` — the *other* soft edge of the captive
definition — got a first-class review column on 2026-07-10; the partially-captive clause never did,
even though it is the clause that does the actual work of turning a grid-entangled arrangement into
a `True`.

## Repo fix — `hybrid_basis`

New review-only column (**SOP §2c**), rendered as the second left-most `updates_summary` column and
column D of `terminal_first_priors`. Not a GEM column, never in the paste sheet — same contract as
`mechanical`.

Values: `grid_export` / `grid_tied` / `grid_fed_site` / `contingency_only`; blank = plain dedicated
on-site plant. **Blank is asserted, not defaulted** — all 30 staged terminals were classified
explicitly, so a blank means the question was asked and answered.

`scripts/build_review_package.py`: headers in `build_updates_sheet` + `build_terminal_first_sheet`
(the latter's wrap/width columns shifted G/H), `STAGED_KEYS` for `updates`,
`captive_terminal_first` and `captive_gogpt_candidates` (the last two also gained
`_superseded_prior`), and both `SHEET_DESCRIPTIONS` entries. Test suite green (81 passed).

Four of 30 Americas terminals carry a value — Peñuelas `grid_export`, Atlantic LNG `grid_tied`,
Woodside Louisiana `grid_fed_site` (the inverse case: grid-fed site, `True` rests wholly on
mechanical drive), Ksi Lisims `contingency_only`.

## Escalated, not resolved — Ksi Lisims

`T100000130914`, staged `True`, yellow, on 603 MW of power barges that build **only if** the BC
Hydro interconnection is delayed; the committed design is grid electric-drive. This collides with
the **current-state Boolean** disposition rule settled hours later the same day in the europe pass
(§2b), under which Eemshaven / Zeeland Energy / Taranto were *not* staged on hardware that only runs
when grid supply fails.

Left staged and flagged rather than silently flipped: the evidence is primary/regulatory and
unambiguous about the facts, and what is undecided is definitional — whether an approved-but-
conditional design element sets the Boolean. Recorded as open policy in §2c; the user decides before
that row is pasted, and the answer belongs back in §2c for the next region.

## Bookkeeping

- `americas-all` and `americas-floor-mopup` metas → `status: "superseded"`,
  `superseded_by: "captive_power/americas-complete"`. They keep their own memos and run records as
  the per-increment audit trail.
- Docs touched: SOP `docs/sops/captive_power.md` (new §2c), `docs/workflows.md` §9 step 4 (stage
  `hybrid_basis` alongside `mechanical`), project `CLAUDE.md` captive routing note.
- Carried forward and still actionable: Louisiana applied except G2; **13 rows still `True` with a
  blank `CaptiveGasPower [ref]`** (Gulfstream 1, Plaquemines 3, Sabine Pass 9); `qa_review`'s
  high-severity American LNG Titusville `cancelled`-but-filing-DOE-reports finding.
