# Captive-power cross-tracker — the Americas, consolidated (all four increments)

**Date:** 2026-07-27
**Workflow:** Captive-power cross-tracker (`docs/workflows.md` §9, `docs/sops/captive_power.md`), terminal-first.
**Workbook:** `batches/lng_terminals_batch_20260727_1411_ET_americas-all-captive_update.xlsx` (recalc clean, no `GUARD:` warnings)
**Staging:** `batches/staging/captive_power/americas-all/`
**Consolidates:** Louisiana (2026-07-09) · Texas (2026-07-10) · US Gulf remainder (2026-07-27) · rest-of-Americas (2026-07-27)

> **This is a consolidation, not a new research pass.** No verdict, citation, confidence colour or
> note was changed. The four increments' staging JSONs were concatenated into one hemisphere-wide
> deliverable so the reviewer applies **one** workbook instead of four. **Apply this workbook; the
> four per-increment workbooks are superseded.** Each increment keeps its own memo and run record as
> the detailed audit trail — the per-terminal reasoning lives there, not repeated here.

The merge is clean: **zero duplicate `(unit_id, field_name)` pairs** across the four staged sets and
**zero duplicate `terminal_id`s** in the three review tabs. The increments partition the hemisphere
without overlap.

---

## Apply state: what the fresh export revealed (read this before pasting)

Re-pulling the GEM export for this build turned the consolidation into an incidental apply-check, and
it found three things worth acting on.

**1. Louisiana has already been applied — 9 of its 10 terminals.** `CaptiveGasPower = True` is live in
GEM for Argent, Calcasieu Pass, Commonwealth, CP2, Delfin, Gulfstream, Plaquemines, Sabine Pass and
Woodside. G2 LNG (yellow, cancelled project) was not applied. Texas, the US Gulf remainder and the rest
of the Americas are **not** applied. Every record's `old_value` in this workbook has been refreshed
against the fresh export, and the **25 already-landed rows are recoloured blue** (value re-verified
unchanged) with the original per-area confidence preserved in `source_notes`. Nothing is lost and
nothing is double-pasted — the paste sheet now shows what is genuinely outstanding.

**2. The ref half of the Louisiana apply is incomplete — 13 rows.** `CaptiveGasPower` reads `True` but
`CaptiveGasPower [ref]` is still **blank** in GEM for **Gulfstream (1 row), Plaquemines (3) and Sabine
Pass (9)**. Those rows say so in `source_notes`; they are blue but still actionable — paste the ref.
This is exactly the "value landed, citation didn't" class that leaves an unsourced `True` in the
tracker.

**3. Three ref-merge violations, now fixed.** Three staged citation sets would have overwritten a URL
already in GEM (ref edits MERGE, never replace):

| Record | Existing GEM URL | Disposition |
|---|---|---|
| CP2 LNG (3 rows) | FERC eLibrary accession 20260324-5193 | **Carried forward.** Live (HTTP 200) but a JS-rendered filelist page, so url_verifier can't content-check it — an existing citation preserved, not a new one. |
| Delfin FLNG `FIDStatus` → `FIDYear [ref]` | DOE Delfin April-2026 progress report | **Carried forward**, re-verified PASS. |
| Alaska LNG (3 rows) | FERC FEIS Volume 1 | **Declared drop** (`dropped_urls_dead`) — full-text verified at 17.2 MB / 1,927,950 chars and it does not contain the claim; AGDC Resource Report 1 carries it verbatim. |

**Why none of these tripped the build guard, and the fix.** `warn_ref_url_drops` only inspected records
whose `field_name` ends in `[ref]`. The captive-power record shape is a **value** record
(`field_name = CaptiveGasPower`) carrying its citations in `ref_urls`, so the existing ref cell never
appeared in `old_value` and the guard was structurally blind to it. `build_review_package.py` now reads
the target ref cell from the fresh export for value-records carrying `ref_urls`, so this shape is
covered — the guard reproduces all three violations against the un-fixed per-area staging dirs, and is
silent against the corrected consolidated one. Test suite green (81 passed).

---

## What is in the combined workbook

| Tab | Rows | What it is |
|---|---|---|
| `updates_summary` | 88 | Staged records with the review-only `mechanical` + GOGPT annotation columns |
| `updates_in_database_format` | 88 | The paste view (GOGPT columns are review-only, do NOT paste) |
| `qa_review` | 27 | Off-lane findings routed to Update / cross-tracker follow-ups |
| `terminal_first_priors` | 77 | **Every terminal crawled**, the audit trail for the negatives as well as the positives |
| `neighboring_plants` | 62 | Nearby GOGPT plants considered, and why each is or isn't the terminal's captive power |
| `gogpt_candidates` | 64 | GOGPT-side proposals — nothing staged from this tab |

**88 staged unit-rows across 29 terminals**: 87 `CaptiveGasPower = True` (+ paired `[ref]`) plus
**1 `FIDStatus` fix** (Delfin FLNG T1, Pre-FID → FID). Confidence after the apply-check recolour:
**52 green, 6 yellow, 30 blue** (blue = value already `True` in GEM and re-verified unchanged — 25 of
them the applied Louisiana rows, 5 the LNG Canada / Alaska rows that were already `True` before any of
these batches). **Zero `PowerPlantsSupplied`** — that field describes the opposite relationship and is
never staged by this workflow.

| Increment | Terminals crawled | Terminals staged | Rows staged | qa items |
|---|---|---|---|---|
| Louisiana (2026-07-09) | 10 | 10 | 27 | — |
| Texas (2026-07-10) | 5 researched (+18 screened, in memo) | 5 | 23 | — |
| US Gulf remainder (2026-07-27) | 17 | 2 | 6 | 10 |
| Rest of the Americas (2026-07-27) | 45 | 12 | 32 | 17 |
| **Combined** | **77** | **29** | **88** | **27** |

## The 29 staged terminals

`mech` = the review-only `mechanical` flag (captive verdict rests wholly or partly on gas-turbine
mechanical drive rather than a dedicated electricity generator).

| Terminal | Country | Rows | Conf | mech |
|---|---|---|---|---|
| Sabine Pass LNG | United States | 9 | blue | True |
| Rio Grande LNG | United States | 8 | green | True |
| Corpus Christi LNG | United States | 6 | green | True |
| Atlantic LNG | Trinidad and Tobago | 5 | green | True |
| New Fortress Altamira LNG | Mexico | 5 | green | True |
| Argentina LNG | Argentina | 4 | green | True |
| Delfin FLNG | United States | 4 | blue/green | False |
| Golden Pass LNG | United States | 4 | green | True |
| Port Arthur LNG | United States | 4 | green | True |
| ST LNG FLNG | United States | 4 | green | True |
| Alaska LNG | United States | 3 | blue | True |
| CP2 LNG | United States | 3 | blue | False |
| Costa Azul LNG | Mexico | 3 | green | True |
| Cove Point LNG | United States | 3 | green | True |
| Plaquemines LNG | United States | 3 | blue | False |
| Argent LNG | United States | 2 | blue | False |
| Goldboro LNG | Canada | 2 | green | False |
| Gulf LNG | United States | 2 | yellow | True |
| Kenai LNG | United States | 2 | green | True |
| LNG Canada | Canada | 2 | blue | True |
| Woodside Louisiana LNG | United States | 2 | blue | True |
| Calcasieu Pass LNG | United States | 1 | blue | False |
| Coastal Bend LNG | United States | 1 | yellow | False |
| Commonwealth LNG | United States | 1 | blue | True |
| Firebird LNG | Suriname | 1 | yellow | False |
| G2 LNG | United States | 1 | yellow | False |
| Gulfstream LNG | United States | 1 | blue | False |
| Ksi Lisims FLNG | Canada | 1 | yellow | False |
| Peru LNG | Peru | 1 | green | True |

Delfin's 4 rows are 3 `CaptiveGasPower` + the one `FIDStatus` fix (T1, Pre-FID → FID); every other row
in the table is `CaptiveGasPower`.

**68 of the 88 rows carry `mechanical = True`** — across the hemisphere, captive power at an LNG
terminal is more often shaft power to the refrigeration compressors than a dedicated electric plant.
That is the single most consequential fact for anyone reading the `CaptiveGasPower` column.

---

## What the hemisphere-wide view says that no single increment did

**1. The axis is grid access, not geography.** Established in the rest-of-Americas increment and it
holds retroactively across all four. Every terminal that can reach a large utility or hydro grid chose
electric drive and said so in a filing (Freeport and Texas LNG in Texas; Tilbury, Cedar, Woodfibre and
Summit Lake in British Columbia; Placentia Bay in Newfoundland; Eagle LNG in Florida). Every terminal
that cannot generates its own power at scale (Kenai, Alaska LNG, the moored FLNGs, ST LNG offshore
Matagorda, the pre-electrification Canadian projects). **For a grid-connected North American project
after roughly 2015 the prior should be NO** — a real, reusable screening rule for the next hemisphere.

**2. Terminal-first was decisive, repeatedly.** GOGPT flagged essentially no Texas captive plants, yet
four of five confirmed Texas terminals run mechanical-drive compressors GOGPT does not track as a
separate power station. In the US Gulf remainder the matcher's *only* hit across MS/AL/FL was a Tier-C
false positive (an FPL utility station 1 km from a terminal cancelled in 2009); the two staged
terminals had no correct prior at all. A plant-first sweep of the Americas would have missed most of
this table. The prior is a prior.

**3. Caribbean and island terminals mostly fail the direction test.** They exist to *feed* a power
station — Peñuelas, San Juan, Costa Norte, Andrés — which is `PowerPlantsSupplied`, not captive. Worth
carrying into the next hemisphere as a screening heuristic, and the reason `PowerPlantsSupplied` sits
blank on several records that superficially look captive.

**4. Two scoping gaps found, both now fixed in the SOP.** Blank `State/Province` on the LNG side (five
US terminals) and blank `subnational` on the GOGPT side (96 US plants) are silently dropped by
`--subnational` runs on **both** sides — this caused a real miss (ST LNG FLNG, 270.4 MW, recovered in
the third increment). Sweep blank-area residue by coordinates before any area increment.

**5. Verifier behaviour worth remembering** (from the QC gates): no hyphen/space folding and no accent
folding (`SGT-400` fails against printed "SGT 400"; `Gatun` fails against "Gatún"), and multi-token
checks validate each token independently, so unrelated co-occurring tokens can manufacture a PASS —
bare numbers are weak tokens. Both are now in the SOP.

## GOGPT-side rollup (proposal only — nothing staged from this tab)

Six clean **ADD** candidates and a handful of MAYBEs across the whole hemisphere, against 29
confirmed-captive terminals. That gap is the standing lesson: **"confirmed captive" ≠ "GOGPT power
station"** — GOGPT tracks *electricity generation*, and most captive LNG terminals are mechanical-drive
or grid-fed.

| Terminal | Verdict | Electric MW |
|---|---|---|
| ST LNG FLNG | **ADD** | 270.4 MW (16 × NovaLT16 @ 16.9 MW, off-grid, project-wide) |
| Port Arthur LNG | **ADD** | 240 MW (8 gas CT generators + 1 backup, FERC-certified) |
| Goldboro LNG | **ADD** | 180 MW (Nova Scotia EA; GOGPT independently agrees to the MW) |
| Cove Point LNG | **ADD** | 130 MW |
| Alaska LNG | **ADD** | 124 MW |
| Firebird LNG | **ADD** | 430 MW |
| Ksi Lisims FLNG | MAYBE | 603 MW (approved *contingency* case, not the committed design) |
| Coastal Bend, Golden Pass, Atlantic LNG, Peru LNG, Saguaro Energía | MAYBE / REVIEWER CALL | MW undisclosed — never inferred |

**MW-review items for GOGPT** (records that exist but whose MW conflates shaft power with generation):
Woodside Louisiana (430.4 MW listed; 0 MW electric — all mechanical drive, site is grid-fed),
Sabine Pass (1,665.6 MW, unverified), Commonwealth (438.6 MW listed vs ~120 MW electric per DOE FEIS),
Argent (675 MW from a single Baker Hughes announcement), G2 (300 MW vs a >1,000 MW design —
conflation risk with NET Power's Texas plant).

## `qa_review` — 27 items, 3 high-severity

All three high-severity items are "the world moved and GEM did not", and none is staged here (the edit
lane is `CaptiveGasPower` only):

- **Argentina LNG is `proposed` but phase 1 reached FID** — RIGI certificate, 30-year export permit,
  20-year ~US$13.7bn Hilli Episeyo charter, Seatrium mooring contract starting Q3 2026 for a 2027
  start; second FLNG (MK II) on the **Fuji LNG** hull, FID ~Aug 2025. → Update batch (needs the
  timeline pull).
- **Bahía Blanca is `mothballed`/YPF but the Tango FLNG barge is gone** — sold to Eni Aug 2022,
  redeployed to Marine XII offshore Republic of Congo, first gas Dec 2023. → vessel-reassignment case;
  run `fsru_sync_check.py` and check GEM's Congo-side record.
- **Blank `State/Province` on five LNG rows** (AGP LNG, American Coast LNG, ST LNG FLNG, Phillips 66
  Beamont Oil, IMTT St. Rose Oil) — coordinates resolve all five. → Update / data hygiene.

Notable mediums: Repsol has owned **100%** of Saint John LNG since 2021 (GEM shows 75/25 with Irving
Oil); Gulf LNG's `Status=proposed` + `ShelvedYear=2022` is an inconsistent pair against active FERC/DOE
filings; Eagle LNG is shelved trending to cancelled (site under contract, water-dependent zoning
surrendered); American LNG Hialeah's operator rebranded to **Sawgrass LNG & Power**; `PowerPlantsSupplied`
blank on Peñuelas and San Juan despite documented purpose-built relationships; and **at least seven
crude-oil terminals sit in the LNG dataset** (five flagged in Texas, two more in the US Gulf remainder)
— a scope-cleanup item, not a captive-power one.

## Verification

Every URL in every lane passed `url_verifier.py` with the specific claimed value as the token, at the
increment that produced it — including the US Gulf increment's 26/26 audit log
(`batches/staging/captive_power/us-gulf/url_verifier.jsonl`) and the rest-of-Americas QC gate's 38
checks (35 PASS / 3 FAIL, all three token-choice artifacts, no citation defects). That gate blanked
Argentina LNG's unsourced 66 MW, dropped Alaska LNG's FERC FEIS Vol 1 citation after full-text
verification, and overrode two verdicts for consistency (Placentia Bay YES → not staged;
TGS Puerto Galván NO → INSUFFICIENT). **Zero gem.wiki / globalenergymonitor.org citations, zero
abarrelfull, zero bare domains** across all staging JSONs — the only gem.wiki links are
`gogpt_record (nav only)` pointers in `neighboring_plants`, rendered italic/gray as do-not-cite
navigation. The combined build emitted **no `GUARD:` warnings**, and `recalc.py` is clean. GEM export
re-pulled fresh for this build (1,273 unit rows); column map re-derived.

## The one open decision, now hemisphere-wide

**Should documented NO verdicts be staged as `CaptiveGasPower = "False"`?** Consolidation makes this
bigger, not smaller: across the four increments there are now roughly a dozen green-quality negatives
(Freeport and Texas LNG in Texas; Eagle LNG in Florida; Tilbury, Cedar, Woodfibre and Summit Lake in
BC; the Caribbean feed-a-power-station cases). All have documented grid-fed electric drive or a
documented opposite relationship. Precedent across the applied batches is **positives only**, so this
consolidation follows it — every verdict, positive and negative, sits on the review-only
`terminal_first_priors` tab regardless. If the answer is yes, it is a mechanical addition and applies
to all four increments at once.

## Americas status

**Complete.** Next hemisphere is the reviewer's call — Asia-Pacific (Australia, Malaysia, Indonesia,
Qatar/Gulf) is where the mechanical-drive-dominant pattern should transfer most directly.
