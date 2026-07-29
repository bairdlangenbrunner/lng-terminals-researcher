# Captive-power cross-tracker — US Gulf remainder (Mississippi, Alabama, Florida + blank-state residue)

**Date:** 2026-07-27
**Workflow:** Captive-power cross-tracker (§9), terminal-first.
**Area:** Third increment, after Louisiana (2026-07-09) and Texas (2026-07-10).
**Workbook:** `batches/lng_terminals_batch_20260727_1131_ET_us-gulf-captive_update.xlsx` (recalc clean)

---

## Headline

**One new confirmed captive terminal with a real generating plant behind it — and it was invisible to
both prior batches.** ST LNG FLNG (offshore Matagorda, Texas) is off-grid by design with **270.4 MW**
of installed gas-turbine generation. It has a blank `State/Province` in the export, so the
state-filtered Louisiana and Texas runs could never have seen it. That is a genuine miss recovered,
and the scoping gap that caused it is now documented and fixed in the SOP.

Everything else in the US Gulf remainder is negative, and mostly negative for a boring reason: of the
17 terminals in scope, 12 are cancelled-and-never-built or out-of-scope oil terminals.

| Verdict | Terminals |
|---|---|
| **Confirmed captive (staged)** | ST LNG FLNG (green), Gulf LNG (yellow) |
| **Confirmed NO** | Eagle LNG (green), American LNG Hialeah (yellow) |
| **No verdict possible** | AGP LNG (red — insufficient evidence) |
| **Screened, not researched** | 12 (10 cancelled-and-never-built, 2 crude-oil terminals) |

**Staged: 6 `CaptiveGasPower` records across 2 terminals.** No `PowerPlantsSupplied` (never in this
workflow). 10 `qa_review` items route the non-captive findings to the Update workflow.

---

## 1. ST LNG FLNG Terminal (T100001061236) — captive YES, green, 4 unit-rows

The strongest result of the three US Gulf increments so far, and the only one anywhere in TX/MS/AL/FL
that is a clean GOGPT **ADD**.

- **Off-grid, in the applicant's own words.** The MARAD deepwater-port licence application states:
  *"The facility would have no connection to the electric power grid... Gas turbine generators with
  waste heat recovery units would be utilized to provide power and heat to the DWP."*
- **270.4 MW installed nameplate, project-wide.** The Draft EIS (April 2026) stationary-source list,
  explicitly *"inclusive of all phases"*, gives **sixteen Baker Hughes LT-16 (NovaLT16)** gas-fired
  combustion turbines for **power generation** — 4 per phase × 4 phases, at 16.9 MW each. Normal N+1
  operation (3 running + 1 standby per phase) is ~202.8 MW. This is 5.4× the >50 MW threshold and it
  is *real electricity*, not only shaft power.
- **Mechanical drive is present too** (`mechanical = True`): **eight Siemens SGT-750** turbines as MR
  compressor drivers, 2 per phase, under a separate EIS heading from the generators. Shaft MW is
  **not** summed into the 270.4 MW.
- **Project-wide finding.** Because the EIS count is stated as covering all phases, propagating
  `CaptiveGasPower` to all four unit-rows rests on evidence, not on the usual project-level assumption.

Project shape: 4 phases × 2.1 mtpa = 8.4 mtpa, ~10.4 nm offshore Matagorda, Brazos OCS Block BA-476,
first LNG targeted 2Q 2030, pre-FID, MARAD/USCG deepwater-port track (no FERC).

**Two caveats, both logged in `qa_review`:**
1. **Vendor conflict, unresolved.** The application and Draft EIS both name Siemens SGT-750 as the
   compressor driver; the March-2026 Baker Hughes press release was read as LM6000PF compressor
   trains. Either a post-DEIS vendor change or a trade-press inaccuracy. It changes neither the
   captive verdict nor the 270.4 MW (which comes only from the NovaLT16 count).
2. **Final EIS not retrievable.** regulations.gov docket entries 403 without a session; docket entries
   -0029 through -0040 were brute-forced without success. Engineering facts therefore rest on the
   April-2026 **Draft** EIS, on the reasoning that a FEIS is a DEIS plus comment responses, not a
   redesign. Worth a re-check when the FEIS becomes reachable.

An earlier pass on this terminal had it at 50.7 MWe (Phase 1, 3 turbines) from trade press alone. Going
back to the MARAD docket for a regulatory primary source is what produced the correct project-wide
figure — a reminder that the trade-press number was both too small and scoped to one phase.

## 2. Gulf LNG Terminal (T100000130228) — captive YES by design, yellow, 2 unit-rows

The awkward one. **One TerminalID, two facilities, opposite answers.**

- **Operating import terminal — a clean NO.** Grid-fed by Mississippi Power (23,000 V stepped to
  4,160 V per the 2019 Final EIS), 10 submerged-combustion vaporizers (process heat, not power or
  drive), and only 2 × 12 MW "essential power backup" gas-turbine generators — **24 MW, below
  threshold and backup-only**.
- **Proposed export project — a YES.** FERC-authorized July 2019, never built, no FID. Design has gas
  turbines mechanically driving the MR/PR refrigeration compressors, 2 per train × 2 trains. FERC's
  order condition #48 requires vendor datasheets for the *"MR/PR compressor gas turbine emission
  control system"*; NS Energy independently: *"Fitted with two gas-fired turbine compressors, each
  train will have a nominal liquefaction capacity of 5Mtpa."* No MW/HP rating appears in any verified
  source — **left undisclosed rather than inferred**, which is the main reason this is yellow rather
  than green.

**How it was resolved rather than hedged.** `CaptiveGasPower` is a project-level field, so the DB holds
one value for this TerminalID and it must serve both facilities. Precedent from Texas settles the
"unbuilt" half of the question: Coastal Bend (proposed) and Rio Grande (under construction) were both
staged True on as-designed captive power, because GEM records proposed projects by their design. So
**True is staged on both rows**, with each row's `source_notes` stating plainly which facility the
captive power belongs to and that the import unit is grid-fed. The import row is explicitly labelled a
propagation row. A reviewer who would rather the field describe only built infrastructure can decline
this one edit; the finding survives in the note either way. Logged as a data-model observation in
`qa_review` — the same import/export split under one TerminalID will recur elsewhere in the tracker.

## 3. Confirmed negatives

**Eagle LNG Terminal (T100000130220) — NO, green.** The never-built Jacksonville export terminal
(3 trains, Chart IPSMR, 1.65M gal/day) is grid-tied: its own project description has electricity
supplied by Jacksonville Electric Authority and the inlet boost compressor explicitly *"motor-driven"*.
Independently, JEA's own five-year capital plan funds three dedicated interconnection projects for this
site (Eagle LNG 138-13.8 kV Substation, ...-SPCP, 138 kV Circuit 847 Interconnect) — a utility-side
buildout, the opposite of on-site captive generation. No source anywhere mentions an on-site gas
turbine here.

**American LNG Hialeah Terminal (T100000130208) — NO, yellow.** A 0.06 mtpa / 100,000 gal-per-day
modular skid-mounted liquefier, roughly two orders of magnitude below the scale at which a >50 MW
turbine set is ever installed. DOE's 2016 categorical-exclusion determination describes modular skids
needing only *"electrical connections"* between them. Yellow rather than green because the finding
rests on scale plus the conspicuous absence of any generation mention across the entire DOE docket
(2014 application → Oct 2025 semi-annual report), not on an explicit "grid-tied, no on-site
generation" statement — no FDEP/Miami-Dade air-construction permit with enumerated units was locatable.

**AGP LNG Terminal (T100001061234) — no verdict, red.** No site or state is establishable from any
citable source; no FERC, MARAD, or DOE docket found. The only citable source is an LNG Prime item on a
7.2 mtpa floating export proposal (capacity matches GEM). The sponsor's homepage claim of holding "all
DOE authorizations" is unverifiable and, being a bare homepage, uncitable in any lane. Nothing stages.

## 4. The scoping gap this batch found — and it caused a real miss

**Five LNG terminals have a blank `State/Province`** in the export: AGP LNG, American Coast LNG, **ST
LNG FLNG**, Phillips 66 Beamont Oil, IMTT St. Rose Oil. The Louisiana and Texas increments filtered by
state, so none of these could ever appear in their worklists. ST LNG FLNG — the batch's one green
confirmed-captive terminal with 270.4 MW behind it — sits off the Texas coast and was missed by the
Texas run for exactly this reason.

**The same gap exists on the GOGPT side, and it also bit.** 96 US GOGPT plants have a blank
`subnational`, among them **Big Hill Energy Power Plant** — the nearest GOGPT plant to ST LNG at
38.07 km. Loading Texas by `--subnational` returns 362 plants and misses it entirely; loading the US
by country returns 1,724 and finds it. So `captive_power_colocation.py --subnational` silently drops
blank-subnational records on **both** sides of the match.

This is not a one-off. Any future area increment run purely on a state filter inherits both holes.
Fix recorded in the SOP and in `qa_review` (severity high): populate the five LNG rows' State/Province
(coordinates resolve all of them), and have area runs either fall back to a coordinate-bounded
selection or explicitly sweep the blank-subnational residue.

## 5. GOGPT-side candidates

| Terminal | Verdict | Electric MW |
|---|---|---|
| **ST LNG FLNG** | **ADD (yes)** — green | **270.4 MW** (16 × NovaLT16 @ 16.9 MW, off-grid) |
| Gulf LNG | DO NOT ADD | — (mechanical-drive only, never built) |
| Eagle LNG | DO NOT ADD | — (grid-fed, motor-driven, never built) |
| American LNG Hialeah | DO NOT ADD | — (0.06 mtpa skid plant) |

ST LNG would be GOGPT's first clean LNG-captive **generating** addition from any of the three US Gulf
increments — Texas produced only Port Arthur (240 MW), and Louisiana's captive power was largely
mechanical drive. GOGPT naming convention would make it *"ST LNG FLNG Terminal power station"*, status
announced/pre-construction (pre-FID, first LNG 2Q 2030).

The Texas lesson repeats and is worth restating: **"confirmed captive" ≠ "GOGPT power station."** Three
of the four researched terminals here generate no on-site gas-fired electricity at all.

## 6. Terminal-first coverage — the method earned its keep again

Neither staged terminal had a correct GOGPT captive prior:

- **ST LNG** — no GOGPT record at all (offshore, pre-FID); nearest plant is 38 km of unrelated onshore
  CCGT.
- **Gulf LNG** — nearest GOGPT plant is Chevron Oil power station at 2.26 km, which is the Chevron
  Pascagoula **refinery's** cogen (Mississippi Power's own list: 5 gas CTs, 147,292 kW). A textbook
  false geographic prior.

The area's **only** deterministic matcher hit across MS/AL/FL was Tier C: Port Everglades power station
1.00 km from **Calypso LNG** — FPL's 1,352 MW utility station next to a deepwater port that was
cancelled in 2009 and never built. A plant-first sweep of this area would have produced exactly one
candidate, and it would have been wrong.

One nearby GOGPT plant *is* genuinely captive-flagged — **Bulldog Power Plant** (2 × 310 MW,
pre-construction, Brazoria County) — but it is captive to a **data centre**, not to LNG, and sits 74 km
inland from an offshore terminal. A real captive flag pointing at the wrong host industry.

## 7. Data-quality items routed out of this lane (10 `qa_review` entries)

- **Gulf LNG:** `Status=proposed` + `ShelvedYear=2022` is an inconsistent pair. Verified filings show
  an active-on-paper project — FERC construction deadline extended to 16 July 2029 (Feb 2024, citing
  COVID-19 and litigation with import customers over terminal-use-agreement scope), and a 31 March 2026
  DOE filing to push non-FTA export commencement to 31 July 2031. No verified source reverses a 2022
  "shelved" characterization (the S&P item failed url_verifier: 403, no Wayback snapshot). → Update.
- **Eagle LNG:** shelved trending to cancelled. Site for sale/under contract, Merus purchase-and-sale
  agreement (26 Nov 2025) for 67.56 acres, Feb-2026 rezoning ordinances flipping 42.58 acres off
  water-dependent zoning, March-2026 City Council clearance for the "Zoo Parkway Industrial Park".
  Surrendering water-dependent zoning is hard to reverse. → Update.
- **American LNG Hialeah:** operator rebranded Miami LNG → **Sawgrass LNG & Power** (April 2025) under
  Pennybacker Capital Management, which closed its acquisition from New Fortress Energy in 2024. GEM's
  Parent is correct; the operator name is stale. Terminal confirmed operating as of the Oct 2025 DOE
  semi-annual report. → Update.
- **AGP LNG:** stated 2025 FID target has passed while GEM shows Pre-FID; no docket or site
  establishable. May not meet the "sufficient information to include" threshold. → Update, possibly
  escalation.
- **Oil terminals in the LNG dataset:** Phillips 66 Beamont (name also appears to misspell "Beaumont")
  and IMTT St. Rose join the five flagged in Texas — **at least seven** now. → separate scope cleanup.
- Plus the blank-State/Province gap (§4), the Gulf LNG project-level field-semantics note (§2), the
  ST LNG vendor conflict and Floating=True precision note, and an Eagle LNG identity check (the export
  unit is the never-built port terminal, **not** the separate operating Maxville plant 26 miles inland
  — press coverage routinely merges them, and GEM's capacity of 1.65M gal/day is the correct
  FERC-authorized figure, not the stale 900,000 pre-FEED number).

## 8. Verification

- **26 cited URLs**, every one re-verified by the orchestrator through `url_verifier.py` with the
  specific claimed value as the token — **26/26 PASS, 0 failures**. Audit log:
  `batches/staging/captive_power/us-gulf/url_verifier.jsonl`.
- Three passed via Wayback fallback after a live 403 (bot-blocked ≠ dead): offshore-technology ×2,
  NS Energy. Live URLs retained in the cells.
- **0 gem.wiki / globalenergymonitor.org citations, 0 abarrelfull, 0 bare domains** across all staging
  JSONs. The 9 gem.wiki links present are `gogpt_record (nav only)` pointers in `neighboring_plants`,
  rendered italic/gray as do-not-cite navigation.
- One bare-domain citation *was* caught and rejected mid-batch: a researcher returned
  `https://www.big-hill.com` as a plant info URL; it was sent back and replaced with the interior
  `/faq` page. That round-trip also resolved a county error — Big Hill Energy is in **Matagorda**
  County, and the "Jefferson County Big Hill" is an unrelated DOE Strategic Petroleum Reserve salt
  dome sharing the name.
- Fresh GEM export pulled at batch start (1,273 unit rows); column map re-derived.
