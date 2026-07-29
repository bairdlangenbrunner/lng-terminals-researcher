# Captive-power memo — Americas, consolidated (single deliverable)

**Stamp:** 2026-07-27 20:05 ET
**Workbook:** `batches/lng_terminals_batch_20260727_2005_ET_americas-complete-captive_update.xlsx`
**Staging:** `batches/staging/captive_power/americas-complete/`
**Supersedes:** `captive_power/americas-all` + `captive_power/americas-floor-mopup` (and, through
americas-all, the louisiana / texas / us-gulf / americas increments)

---

## What this is

**One workbook for the whole hemisphere.** Six staging increments are now one: Louisiana (07-09),
Texas (07-10), US Gulf remainder (07-27), rest-of-Americas (07-27), the americas-all consolidation
(07-27 14:11) and the no-MW-floor mop-up (07-27 18:27). Nothing was re-researched — no verdict,
citation, confidence or source note was rewritten. The only substantive addition is the
`hybrid_basis` column (below).

| | count |
|---|---|
| staged unit-rows | **89** (88 `CaptiveGasPower` + 1 `FIDStatus`) |
| terminals with a staged edit | **30** |
| `terminal_first_priors` | 77 |
| `gogpt_candidates` | 68 |
| `neighboring_plants` | 62 |
| `qa_review` | 30 |
| `PowerPlantsSupplied` | **0** (never staged by this workflow) |

Merge is clean: zero duplicate `(unit_id, field_name)` pairs, zero duplicate `terminal_id`s in the
review tabs. Build emitted no `GUARD:` warnings; `recalc.py` found no formula errors; test suite
green (81 passed).

## How the two dirs were merged

`staged_updates` concatenated (the mop-up's single Peñuelas row did not collide with anything).
`captive_terminal_first` and `captive_gogpt_candidates` were deduped on `terminal_id` across their
**9 overlapping terminals**, with the mop-up row winning — it is the post-floor-removal
re-research — and its ref list **unioned** with the americas-all row's rather than replacing it, so
no verified independent URL is dropped. The superseded basis is preserved verbatim in
`_superseded_prior`.

**Coastal Bend is the case that makes the union matter.** The mop-up row cited two
`coastalbendlng.com` URLs — one self-published origin, not two independent sources — while
americas-all cited conocophillips.com + ogj.com + hartenergy.com. The merged row keeps all five and
takes the mop-up's stronger basis: the developer now **names "cogeneration"**, which retires the
">50 MW inferred from the 22.5 Mtpa scale" reasoning the floor removal invalidated. Both rows were
already yellow, so the mop-up's stated green→yellow downgrade was moot.

## New: `hybrid_basis` — the partially-captive judgment is now visible

§2's "partially-captive counts" is one line of SOP prose that does a lot of work: it is the clause
that turns a grid-entangled arrangement into a `True`. Until this build, every such judgment lived
**only inside free-text `source_notes`**, so a reviewer reading the workbook could not distinguish a
plain dedicated on-site plant from a verdict resting on that clause. `mechanical` got a first-class
review column on 2026-07-10 for exactly this reason; `hybrid_basis` is the same fix for the other
soft edge. Review-only — not a GEM column, never in the paste sheet. Definition table: **SOP §2c**.

All 30 staged terminals were classified explicitly (blank = a positive finding, not an unasked
question). **Four carry a value:**

| terminal | value | the assumption being made |
|---|---|---|
| **Peñuelas** (PR) | `grid_export` | EcoElectrica's CCGT is one permitted facility with the terminal; its generators produce "power for sale **and internal use**". Power flowing out to the PREPA grid does not defeat captive status. The boldest of the four — the source shows station service to the integrated site, not a terminal-dedicated genset. Yellow. |
| **Atlantic LNG** (T&T) | `grid_tied` | Solar Mars 100 gensets feed the complex's own 12.47 kV internal grid; the Train-4 set is "one tied to the existing grid, three new". Low risk — **over-determined**: the mechanical-drive Frame 5 fleet carries the `True` on its own. |
| **Woodside Louisiana** | `grid_fed_site` | The **inverse** hybrid: site electricity is bought from Entergy (230 kV) and there is no generating plant at all; the `True` rests wholly on 8× LM6000PF+ mechanical compressor drives. Already applied to GEM (blue). |
| **Ksi Lisims** (BC) | `contingency_only` | **See below — unresolved.** |

## Escalation: one reviewer call, unresolved

**Ksi Lisims FLNG (`T100000130914`), staged `True`, yellow.** The committed design is BC Hydro grid
electric-drive. The 603 MW of purpose-built on-site power barges is an **approved contingency** that
builds only if the interconnection is delayed.

This is in tension with a rule settled **hours later the same day** in the europe pass (SOP §2b):
`CaptiveGasPower` is a **current-state** Boolean, which is why Eemshaven, Zeeland Energy and Taranto
were **not** staged on hardware that only runs when grid supply fails. Ksi Lisims is arguably the
same class.

It is left **staged and flagged**, not silently flipped, because the evidence is primary/regulatory
and unambiguous about the *facts* — what is undecided is whether an approved-but-conditional design
element sets the Boolean. That is a definitional call, not a research gap. **Decide before pasting
that row.** Whichever way it goes, the rule belongs in SOP §2c so the next region inherits it.

## Carried forward from the increments (still true, still actionable)

1. **Louisiana is already applied** (9 of 10 terminals; G2 LNG was not). Those 25 rows are blue with
   their original per-area confidence preserved in `source_notes`. Texas, the US Gulf remainder and
   the rest of the Americas are **not** applied.
2. **13 rows read `CaptiveGasPower = True` with a blank `CaptiveGasPower [ref]`** — Gulfstream (1),
   Plaquemines (3), Sabine Pass (9). The ref half of the Louisiana apply never landed. An unsourced
   `True` sitting in the tracker is exactly what the ref half exists to prevent; these are blue but
   still actionable.
3. **`qa_review` carries 30 items**, the highest-severity being **American LNG Titusville**
   (`T100000130209`): GEM records `cancelled`, but the project filed a DOE 15-19-LNG semi-annual
   report on 19 Mar 2026 and had its FTA authorisation transferred to LNG Holdings LLC / New
   Fortress Energy in Nov 2024. A cancelled project does not keep filing DOE semi-annual reports.
   Routes to a follow-on Update batch — QC detects, Update fixes.

## GOGPT side

68 `gogpt_candidates` rows, nothing staged (this repo never stages GOGPT-side edits). The backlog
seed for the sibling `gogpt-researcher` repo's Discovery workflow is
`captive_power/americas-complete/captive_gogpt_candidates.json`. Standing caveat unchanged: GOGPT
tracks *electricity generation*, so a pure mechanical-drive turbine set may be absent from GOGPT
entirely, and GOGPT's plant MW can conflate compressor shaft power with generating nameplate.
