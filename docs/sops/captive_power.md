# SOP — Captive-power cross-tracker matching

**Type:** on-request cross-tracker analysis (not part of the quarterly cycle).
**Output:** an LNG staging xlsx (`CaptiveGasPower` + occasional status/FID fix — **never
`PowerPlantsSupplied`**, see §2) **plus** a markdown memo. **Edit lane is LNG-side only** —
GOGPT-side gaps are documented in the memo, never staged (this repo has no GOGPT write path —
that now lives in the sibling `gogpt-researcher` repo, whose discovery backlog is seeded from
this workflow's candidate JSONs).

**Terminal-first** (set 2026-07-10): the unit of work is the LNG terminal, not the GOGPT plant.
Crawl the LNG terminals of an area — a US **state**, or a whole **country** where states aren't
meaningful — one area per batch, and for EACH terminal research whether it has on-site captive gas
power. The deterministic GOGPT match (§3.1) is a PRIOR that flags likely cases; it is NOT the
worklist filter. Many terminals run captive/mechanical-drive turbines that GOGPT never tracks as a
separate "power station," so a plant-first sweep silently misses them (e.g. Corpus Christi / Rio
Grande gas-turbine drives). **Which areas are done lives in the coverage ledger** — each area's
`batches/staging/captive_power/<area>/meta.json` (`scripts/coverage_status.py` reads these), not in
this prose; Louisiana (2026-07-09) and Texas (2026-07-10) are the completed-to-date areas as of this
writing. Process order follows GEM's own cadence — finish a state/country before moving to the next.

## 1. What this workflow answers

Which LNG terminals have a **captive gas power plant** that is separately tracked in GOGPT (the
Global Oil & Gas Plant Tracker)? A match lets us (a) set the LNG side's `CaptiveGasPower` field
(NOT `PowerPlantsSupplied` — §2), and (b) surface where the two trackers disagree on status or capacity.

Both trackers live in the same read-only Postgres, so the match is a data join plus web research —
no live-DB writes on either side.

## 2. Definition of "captive" (locked 2026-07-09; mechanical-drive in scope, flagged — settled 2026-07-10; **MW floor removed 2026-07-27**)

A captive gas power plant is an **on-site / fenceline gas-fired plant, at any size**, whose primary
function is powering the terminal / liquefaction. Anchored to the methodology's "Associated Projects
and Fuel Sources" section + the GOGPT captive block.

- **There is NO MW threshold (user directive 2026-07-27).** Earlier revisions of this SOP set a
  `>50 MW` floor and attributed it to GOGPT's inclusion threshold. **That was wrong on both counts:**
  GEM's `CaptiveGasPower` is a plain Boolean (schema col 73) with no size qualifier, and GOGPT
  demonstrably tracks **1,900 sub-50 MW units, 861 of them `captive=true`, down to 1.5 MW** (queried
  against the read-only Postgres 2026-07-27). A 3 MW on-site gas turbine is a `True`. Record the size
  in `electric_mw`; never use it to disqualify.
  - The floor caused a real miss: **Mukran FSRU** (`T100000131141`) had a regulator's permit stating
    the terminal "can be operated permanently with onboard gas generators" and was still returned NO
    on an *assumed* sub-50 MW rating. A documented positive must never lose to an inferred size.
- **Partially-captive counts** (a plant that powers the terminal *and* exports to the grid).
- **Mechanical-drive counts — but is flagged.** On-site gas turbines that **mechanically drive the
  refrigeration compressors** (shaft power, no electricity generated) are captive power just as much
  as electricity generators are. This keeps e.g. **Woodside Louisiana** in scope even though its
  site *electricity* is grid-fed (its 8× LM6000PF+ turbines are pure mechanical compressor drives).
  Settled 2026-07-10 (in-scope-but-flagged, per the `mechanical` flag below); see the run record for
  that date if the history matters.
- **`mechanical` flag (required, 2026-07-10).** Any terminal whose captive designation includes
  mechanical-drive turbines is marked `mechanical = True` in a left-most column of the staging
  review sheet — so a reviewer can see at a glance which "captive" verdicts rest on shaft-power
  turbines vs a dedicated electricity generator. In Louisiana: **Woodside** (pure mechanical, no
  generator), **Sabine Pass** and **Commonwealth** (mixed: a real generator *plus* mechanical
  drives) → `True`; the seven pure-generator terminals → `False`. The flag is a review annotation
  only — it is NOT a GEM column and never appears in the paste (`updates_in_database_format`) sheet.
- **Out of scope:** a hydrogen/other-fuel captive plant with no LNG terminal (the Clean Hydrogen
  Works false positive), and any plant that is not on-site.

- **`PowerPlantsSupplied` is NEVER filled by this workflow (rule set 2026-07-10).** Captive power
  flows INTO the terminal (the plant powers the liquefaction/compression). `PowerPlantsSupplied`
  describes the OPPOSITE relationship — a terminal piping regasified gas OUT to an external power
  plant (e.g. Vung Ang → Quang Trach). The two are mutually exclusive for a captive relationship,
  so `PowerPlantsSupplied` and its `[ref]` stay blank in every captive-power staged record. The
  ONLY field this workflow stages is `CaptiveGasPower` (+ its `[ref]`), plus the occasional
  status/FID fix.

### 2a. GOGPT-side definitions (from the GOGPT manual, folded in 2026-07-10)

The captive concept above is anchored to BOTH the LNG Terminals Manual and the GOGPT (Global Oil &
Gas Plant Tracker) manual; GOGPT's captive fields are how the match output reads. Per the GOGPT
manual:

- **Captive plant** = a power plant located *within an industrial facility* that primarily supplies
  power to that facility. A CHP (combined heat & power) captive plant also supplies most of its heat
  to the host. A captive plant that sells a significant share of electricity to the grid (or heat to
  neighbours) is still captive — this is our "partially-captive counts."
- **GOGPT captive fields** (visible in the match CSV): `Captive Industry Type` (the served industry;
  id **56 = "LNG production / liquefaction"** — but tagging is inconsistent, so do NOT gate on it),
  `Captive Industry Use` (**heat / power / both**), `Captive Non-Industry Use` (grid/home sales →
  the partially-captive signal), and an `Emergency/Backup` flag (data-centre-only; irrelevant here).
- **GOGPT has NO effective 50 MW floor — an earlier version of this line claimed it did, and that
  claim was false.** Queried against the read-only Postgres 2026-07-27: of 16,166 GOGPT units,
  **1,900 are below 50 MW and 861 of those are `captive=true`**, with a minimum of 0.0 MW (captive
  examples: Nyala 1.5 MW, El Geneina 1.6 MW, Argyle Diamonds 3.0 MW ×5). `load_gogpt_plants()` in
  `scripts/captive_power_colocation.py` applies **no MW filter whatsoever**. Consequences: (a) size is
  never a reason to withhold a `CaptiveGasPower = True`, and (b) **size is never a reason to return
  `gogpt_candidate: DO NOT ADD`** — a sub-50 MW captive plant is a legitimate GOGPT candidate.
  Reserve DO NOT ADD for "a record already exists" or "not a gas power station at all."
- **GOGPT naming convention:** a captive plant with no standalone name is called "*<Host> power
  station*" — e.g. "XYZ LNG Terminal power station." This is the name-containment signal the matcher
  keys on, and the reason a real captive relationship can hide behind a generic plant name.
- GOGPT tracks *electricity generation*. A pure mechanical-drive turbine set (shaft power to
  compressors, no generator) may therefore be **absent from GOGPT entirely** — the strongest reason
  to research terminal-first rather than plant-first.

### 2b. The tests that do the work now that size doesn't (europe pass, 2026-07-27)

With the MW floor gone, these five are the whole screen. Each one retired a candidate that the floor
would otherwise have disposed of without anyone reading the evidence:

- **Gas-fired.** Must burn natural gas, LNG, or boil-off gas. **Diesel/MDO-only is NO at any size**
  (Puerto de la Luz's 4× 18.5 MW engines are diesel-cycle → NO). **Dual-fuel (DFDE, Wärtsilä `W*DF`)
  counts as gas** where sourced as gas/BOG-burning in service — that is what puts most FSRUs in scope.
  **Non-combustion self-generation is NOT gas power:** turboexpanders / pressure-letdown recovery
  (Barcelona, 6,325 MWh/yr), ORC-ORMAT waste-heat units (Huelva, 287 MWh/yr), wind (Dragon LNG's
  12.6 MW), solar.
- **Power, not heat. Thermal ≠ electric.** A gas-burning installation producing *process heat* is not
  captive power however large: submerged-combustion vaporizers (Świnoujście holds a permit for a
  **>50 MWt** SCV installation → still NO), ORVs, process boilers. **Watch the unit — MWt/MWth is
  thermal.** Waste heat flowing *into* the terminal is likewise not captive power (Gate ← Uniper,
  Grain ← Uniper 340 MWth, Brunsbüttel ← Covestro warm water, Stade ← Dow).
- **Loads are not generators.** Do not read consumption as generation: Falconara's "4× 1.1 MW electric
  motors" are compressor drives, Tenerife's "3.9 MW" is site demand, Fos Tonkin's "45 MW" is
  incremental *grid draw* from RTE, Barcelona's "38,499 MWh" is metered grid **import** (and MWh is
  energy, not capacity). Sub-50 MW figures must be read in context, never pattern-matched.
- **Captive to whom — the industrial-host trap.** Settled: Huelva's GEMASA + La Rábida are CEPSA's
  refinery's; the 163 MW Stade plant is **Dow's own**, commissioned 2015 years before the FSRU arrived;
  Sines' 43/41 MW are Repsol's and Indorama's; Gothenburg's Rya CHP is Göteborg Energi's.
- **Standby-only is a YES.** User directive, 2026-07-28: *"if there is any turbine whatsoever that
  runs when grid supply fails, that counts as a yes."* Gas-fired generation that exists to carry the
  site through a grid outage is captive power — stage `CaptiveGasPower = True`, category
  `standby_backup`. It is a *screen*, not a *test*: the four tests above still all have to pass, and
  the **gas-fired** one does the real work here, because emergency gensets are more often diesel than
  gas. Concretely, of the six terminals this directive flipped, every one had a gas-fired standby set
  named in a permit or regulatory filing (Montoir's single `groupe électrogène gaz de secours` of
  1,250 kVA sits *next to* two 1,400 kVA **diesel** sets — only the gas one counts); a diesel-only
  emergency genset is still a NO at any size, and an emergency set whose fuel no source states is
  still INSUFFICIENT, never a NO (Rostock, Southern Finland).

  **Disposition rule (2026-07-28 directive; supersedes the current-state rule settled 2026-07-27).**
  The old rule read `CaptiveGasPower` as a strictly current-state Boolean and refused to stage
  hardware that only runs on grid loss. That is reversed. Present-tense duty still decides the
  *category*, not the *value*:
  - **`power_generation`** — gas generation supplies the site in normal operation. **Klaipeda** is
    the type case (onboard engines are the operating power source now; contracted shore power does
    not land until May 2028 — a future shore-power date does not retire a present-tense True).
  - **`standby_backup`** — grid/shore power is the base case and the gas set runs on interruption:
    **Eemshaven, Montoir, Taranto, Zeeland ZET, Elba Island, Placentia Bay**, and Gulf LNG's
    operating *import* unit-row. All staged True as of 2026-07-28.
  - **A documented *past* primary-generation window is worth recording but is no longer what carries
    the value.** Eemshaven self-generated from commissioning (Sept 2022) until shore power landed
    (~March 2023); that history belongs in the wiki Background, and the standing standby duty is what
    makes it a `True` today.
  - **"As-designed" cuts both ways — and now cuts toward YES in both directions.** Where the only
    evidence is the permitted design, use it: design-as-self-supply carries the True at **Shtokman,
    Trieste Monfalcone, Constanța and Zaule**, and design-as-standby now carries the True at
    **Zeeland ZET** (base case shore power, onboard `gasgeneratoren` for supply security) and
    **Placentia Bay**. Consistency is the point — don't reach for as-designed only when it produces
    the answer you already have.

**Absence of evidence is INSUFFICIENT, never a documented NO.** The Mukran miss had a second half
worth naming separately: the researcher defeated a regulator-sourced positive with an *assumed*
"~20–30 MW, standard FSRU-class equipment" figure. Reasoning from class precedent to a negative is
not a finding. If the spec is unpublished, say INSUFFICIENT.

**A NO must point at a source.** Concretely, a NO needs either (a) an enumeration of the installation's
equipment — a DIA/AIA/SIA/BImSchG/air permit installation list — with no generator in it, or (b) an
explicit statement of how the site is supplied (grid connection, shore power, external CHP). Three
substitutes recur and none of them is a NO: **inference from a sibling terminal** ("Barcelona and Huelva
are grid-fed, so Cartagena is"), **inference from the plant's scale** ("too small for a turbine set" —
void with the floor gone), and **the direction test** ("the terminal pipes gas OUT to a power plant").
The direction test is the subtlest: it answers a different question, since a terminal that feeds a plant
can also draw its own power back from it — the partially-captive case, confirmed real at
**Peñuelas/EcoEléctrica**, and the reason **Port of Vlora** and **Mugardos** were re-opened.

**Sweep until the residue is enumeration-backed — one extra pass is not enough.** When a rule is
retired, re-dispatching the records that name it is not enough. The floor leaves a greppable `50 MW`
fingerprint; absence-as-NO leaves none, and the direction test leaves a *different* one again. The
europe increment needed **four** passes, each surfacing terminals the previous one had not flagged:
the floor sweep; then an absence sweep (Cartagena, Sines, Gran Canaria, Mugardos, Brunsbüttel
onshore); then a direction-test sweep (Bilbao, Cyprus FSRU, Marmara, Panigaglia, Zeebrugge, Bar);
then the **`SCREENED` sweep** below. So: **grep for all the fingerprints, then read the survivors'
actual text** and keep only the NOs that name an (a) enumeration or a (b) supply statement. Three
habits make this cheap —

- ***Re-audit the `SCREENED` class itself — a screen is a verdict with no research behind it.***
  This was the largest single miss of the europe pass and the easiest to overlook, because a
  screened record never appears in a verdict sweep at all. 36 europe terminals were screened, and
  the stated reason for a third of them *was the abolished floor in disguise* — "small-scale",
  "below the 0.5 mtpa screen threshold", "whole-site load orders of magnitude below the 50 MW
  captive-power threshold." **Partition the screened set by whether the plant was ever BUILT**
  (`operating`/`retired`/`idle`/`mothballed`/`construction` vs `proposed`/`cancelled`/`shelved`).
  For a never-built project the screen stands — there is no plant to have captive power. For a
  built one, scale is not a screen and the record must be researched like any other. **Ravenna LNG
  Terminal** (`T100000130683`) is the proof: screened unresearched as ~0.45 mtpa and "orders of
  magnitude below the threshold," it runs **three BOG-fired engine-gensets** supplying the site's
  own load with surplus to the grid, and grid purchases able to fall to zero — a green `YES` off a
  single MASE/VIA filing. **Invert the intuition: a small terminal with no pipeline send-out is
  MORE likely to run BOG gensets, not less**, because it has to do something with its boil-off gas.
  Screened **liquefaction/export** plants are the highest-yield sub-class of all — refrigeration
  compression is the site's dominant load, and if it is turbine- or engine-driven rather than
  motor-driven that is captive power (`mechanical = True`) that GOGPT will never have tracked.

- *Audit the reasoning, not just the verdict.* Three europe NOs (Gibraltar, Puerto de la Luz,
  Dunkirk) were **correct** but *led* with a void clause; the valid basis was buried a sentence
  later. Keep the verdict, disown the clause in writing, and record which finding actually carries
  it, or the next reader inherits the bad reasoning along with the right answer.
- *Know each country's enumerating document.* Most of these flips turn on one document class, and
  finding it is the whole job: Spain's per-plant EMAS **Declaración Ambiental** (its
  electricity table settled Huelva outright — 47,778 of 48,065 MWh purchased from the grid),
  Italy's **AIA/VIA** dossiers on `va.mite.gov.it`, Germany's **BImSchG** permits, Belgium's
  **omgevingsvergunning**, Türkiye's **ÇED** reports and EPDK licence annexes.

### 2c. `hybrid_basis` — the partially-captive judgment must be VISIBLE (added 2026-07-27)

"Partially-captive counts" (§2) is one line of SOP prose doing a lot of work: it is the clause that
turns a grid-entangled arrangement into a `True`. Until now every such judgment lived only inside
free-text `source_notes`, so a reviewer reading the workbook could not tell a plain dedicated on-site
plant from a verdict that rests on the partially-captive clause. `mechanical` got a first-class
review column in 2026-07-10 for exactly this reason; this is the same fix for the other soft edge.

**Set `hybrid_basis` on every staged `CaptiveGasPower = True` record and every
`captive_terminal_first` row.** Like `mechanical` it is a **review annotation only** — not a GEM
column, never in the paste (`updates_in_database_format`) sheet. The build renders it as the second
left-most `updates_summary` column and column D of `terminal_first_priors`.

| value | meaning |
|---|---|
| *(blank)* | Plain dedicated on-site plant, no grid entanglement. **A positive finding, not an unasked question** — classify every terminal explicitly. |
| `grid_export` | The plant powers the terminal **and sells power out**. The canonical §2 partially-captive case. Type case **Peñuelas**: EcoElectrica's CCGT is one permitted facility with the terminal and its generators produce "power for sale *and internal use*". |
| `grid_tied` | Captive generation feeding the site's **own internal grid**, with at least one unit tied to the external grid. Type case **Atlantic LNG**: Solar Mars 100 gensets on the complex's 12.47 kV internal grid, "one tied to the existing grid, three new". |
| `grid_fed_site` | **The inverse hybrid** — site *electricity* is bought from the utility and there is no generating plant at all; the `True` rests wholly on mechanical drive. Type case **Woodside Louisiana** (Entergy 230 kV + 8× LM6000PF+ compressor drives). Always pairs with `mechanical = True`. |
| `contingency_only` | On-site generation is an **approved but conditional** design element; the committed design is grid. **Escalate — do not settle this one silently** (see below). |

**`contingency_only` — resolved 2026-07-28: it stays a `True`.** It used to collide with §2b's
current-state disposition rule (the rule that kept Eemshaven, Zeeland ZET and Taranto unstaged); that
rule is gone, and the standby directive settles this class the same way. The case is **Ksi Lisims**
(`T100000130914`, staged `True`, yellow, category `contingency_design`): committed BC Hydro
electric-drive, with 603 MW of purpose-built power barges that build **only if** the interconnection
is delayed. It stays staged. Keep the `contingency_only` tag and the yellow — approved-but-conditional
is a weaker evidentiary state than installed hardware, and the memo should still name it — but it is
no longer an escalation.

### 2d. `captive_category` + `hardware_summary` — say WHAT the hardware is (added 2026-07-28)

`CaptiveGasPower` is one Boolean, so the paste sheet alone cannot tell a mechanical-drive compressor
turbine from a grid-loss standby genset — a distinction the reviewer needs and, after the standby
directive, one that now spans five different physical arrangements. Set **both** fields on every
staged `CaptiveGasPower = True` record. They are **review annotations only** — not GEM columns,
never pasted — and the build renders them as the **two left-most columns of
`updates_in_database_format`**, ahead of the GOGPT pointers. Unlike the GOGPT columns they are
**per unit-row**: one terminal can hold different hardware on different rows (Gulf LNG's operating
import row is `standby_backup`; its proposed export row is `mechanical_drive`), while the
project-level Boolean is still written to every row.

| `captive_category` | meaning |
|---|---|
| `mechanical_drive` | Gas turbines shaft-driving the refrigeration compressors. No generator, zero MWe. Pairs with `mechanical = True`. |
| `power_generation` | Gas-fired generating sets supplying the site's electricity in normal operation — a land plant, or an FSRU/FLNG's own onboard engines. |
| `mechanical_drive+power_generation` | Both on site (the common large-liquefaction shape: turbine drivers plus a house-power plant). |
| `standby_backup` | Gas-fired generation that runs when grid/shore supply fails (§2b, 2026-07-28). |
| `contingency_design` | Approved generation built only on a stated trigger (§2c `contingency_only`; Ksi Lisims). |

`hardware_summary` is one line — count, type, rating where a source states one — written as the short
form of that row's `source_notes`, e.g. *"Six GE/Baker Hughes Frame 7EA heavy-duty gas turbines
shaft-driving 12 refrigerant compressors across 3 trains."* Never put a MW figure in it that no
source states; "no MW figure published" is a legitimate thing to write, and per §2 an undisclosed
rating is never a reason to withhold the `True`.

## 3. Phases

1. **Match (deterministic)** — `scripts/captive_power_colocation.py` reads the LNG all-fields CSV,
   pulls GOGPT from Postgres, and pairs them on three signals (geospatial haversine, name
   containment, existing captive flags), resolving each GOGPT plant to ONE primary terminal so
   channel-neighbors don't cross-claim. Emits a tiered candidate CSV (A = real pairs, B = weak/both
   unflagged, C = neighbor-bleed, correctly demoted). Filters by `--subnational` (a state/province
   name); scale to a new area by re-running with a different `--subnational`.

   **Blank-area records are invisible to `--subnational` — on BOTH sides. Sweep them explicitly.**
   A state filter silently drops every record whose area field is empty, and that has already caused a
   real miss. On the **LNG side**, five US terminals have a blank `State/Province` (AGP LNG, American
   Coast LNG, **ST LNG FLNG**, Phillips 66 Beamont Oil, IMTT St. Rose Oil), so the state-filtered
   Louisiana (2026-07-09) and Texas (2026-07-10) runs could never see them — and ST LNG FLNG, off the
   Texas coast, turned out to be confirmed captive with 270.4 MW of off-grid generation (recovered
   2026-07-27). On the **GOGPT side**, 96 US plants have a blank `subnational`, including Big Hill
   Energy Power Plant, the nearest GOGPT plant to ST LNG at 38 km:
   `load_gogpt_plants(engine, "Texas")` returns 362 plants and misses it, `by_country=True` returns
   1,724 and finds it. So before dispatching any area increment: list the in-scope country's
   blank-area rows on both sides and assign them to an area by **coordinates**, or run the neighbor
   computation against the whole-country set rather than the state-filtered one.
2. **Research (agentic, terminal-first — one subagent per candidate LNG terminal)** — dispatch a
   researcher for each LNG terminal in the area that could plausibly have captive power (live
   liquefaction/export terminals, any terminal with a GOGPT captive-plant prior; quick-screen and
   document — without deep web research — the obvious non-candidates: **cancelled-and-never-built
   projects and crude-oil loading terminals, and nothing else**). **Size is NOT a screen and never
   was a valid one** — an earlier revision of this line also screened out "small import/FSRU regas
   terminals," which was the abolished MW floor smuggled into the dispatch step; it cost us Ravenna
   (§2b) and a dozen re-dispatches. If the plant was ever built, it gets researched, however small.
   Each researcher
   confirms against §2 and finds capacity/status, held to the full hard rules: every cited URL
   value-checked through `url_verifier.py`, **≥2 independent publishers**, **no gem.wiki / no
   GEM-derivative**. Return a structured verdict (captive yes/no, **whether captive power is
   mechanical-drive**, capacity finding + whether it's verified, status). Choose a cost-appropriate
   model at dispatch time (Model selection block at the top of `docs/workflows.md`).
3. **Reconcile & stage (LNG side)** — for each confirmed terminal, stage `CaptiveGasPower = True`
   with a paired `[ref]` on **every unit-row** of the terminal (project-level fields propagate to
   all units — Sabine Pass = 9 rows).

   **As-designed captive power on an unbuilt facility still counts** — GEM records proposed projects
   by their design, so a proposed/under-construction terminal whose design includes captive power is
   staged `True` (Coastal Bend and Rio Grande, TX 2026-07-10). **But the design that counts is the
   terminal's OWN design, not an abandoned captive-power bolt-on at a terminal that is already
   operating.** Counter-case — **South Hook** (UK, 2026-07-27): a CHP plant was proposed for the site
   and never built, and the terminal itself is `operating`, so its GEM record describes an as-built
   facility with no captive power. Verdict **NO** — staging `True` off the dead CHP proposal would
   misdescribe the facility. The clause above applies where the *terminal* is still proposed/under
   construction and captive power is part of the design being recorded; it does not resurrect a
   cancelled add-on to a built facility. **When one TerminalID spans facilities
   with opposite answers**, the project-level field still holds ONE value: stage it, and make each
   unit-row's `source_notes` say which facility the captive power belongs to, labelling the others
   propagation rows. Canonical case — **Gulf LNG** (MS, 2026-07-27): an operating import terminal that
   is grid-fed with only 24 MW of backup gensets (recorded as a NO at the time on the since-removed MW
   floor) plus a FERC-authorized but never-built export project with mechanical-drive captive power
   (a YES), staged `True` at **yellow** with the split spelled out per row. **Both halves are now a
   YES, and the import row is no longer a propagation row** (2026-07-28): the 2019 FERC/DOE Final EIS
   Ch.2 lists "two essential power backup gas turbine generators each with a capacity of 12
   megawatts" — gas-fired, so with the floor gone (§2) and standby counting (§2b) that row carries its
   own basis. It is also the case that makes the per-unit-row `captive_category` (§2d) necessary: the
   import row is `standby_backup`, the export row `mechanical_drive`. Do not resolve this by leaving the field blank and writing a
   "reviewer may prefer…" hedge — decide, document the basis in the note, and add a `qa_review` entry
   so the reviewer can decline the single edit.

   **A captive record is a VALUE record that writes a ref cell, so ref-MERGE applies to it.**
   `field_name = CaptiveGasPower` with the citations in `ref_urls` — the existing
   `CaptiveGasPower [ref]` cell never appears in `old_value`, so it is easy to overwrite a live
   existing citation without noticing. Read that cell in the fresh export before staging and carry
   every surviving URL forward in `ref_urls` (Update SOP §7.2a); declare proven-dead drops in
   `dropped_urls_dead`. The `REF-DROP:` build guard was blind to this shape until 2026-07-27 — three
   undeclared drops (Alaska LNG, CP2, Delfin) reached built workbooks before it was extended to read
   the target ref cell from the fresh CSV.

   **Do NOT stage `PowerPlantsSupplied`** (§2 — captive power
   flows into the terminal, not out). Set the per-record **`mechanical`** field (`"True"`/`"False"`)
   on every record of a terminal whose captive power involves mechanical-drive turbines (§2); the
   build renders it as the left-most column of `updates_summary`. Set **`hybrid_basis`** (§2c) and
   **`captive_category` + `hardware_summary`** (§2d) on every staged `True` record — the last two are
   per-unit-row, so a terminal whose unit-rows differ (Gulf LNG) gets different values on each, and
   the build renders them as the two left-most columns of the paste sheet. Stamp each record with the related
   GOGPT plant's `gogpt_plant_id` / `gogpt_plant` / `gogpt_wiki_url` (from the matcher deliverable) —
   the build renders these as the three left-most, **review-only** columns of the paste sheet
   (`updates_in_database_format`), italicized "do NOT paste"; the gem.wiki URL is a navigation
   pointer to the GOGPT record, never a citation. **When no GOGPT captive record exists for a
   confirmed terminal** (the terminal-first case — GOGPT doesn't track its captive/mechanical-drive
   power, e.g. all of Texas): either leave the annotation cols empty (the build emits them on key
   *presence* now, with an explanatory header note) OR, if useful, stamp the **nearest GOGPT plant by
   distance** plus `gogpt_suggested="True"` and a `gogpt_match_note` — the build fills those cells
   **RED** so a reviewer reads them as *suggestions to verify*, never confirmed matches. Route any
   confirmed status/FID change through the normal staging path. Build with
   `build_review_package.py --mode update` + `recalc.py`.
4. **Memo (GOGPT-side + findings)** — everything that is *not* an LNG edit goes here: GOGPT
   capacity/tagging issues, the mechanical-vs-electric split, unverified figures, and the
   scale-past-this-area recommendation.

Full command recipe: `docs/workflows.md` §9.

## 3a. Deliverable workbook structure (standing layout — build every area this way)

Beyond the two staging sheets (`updates_summary`, `updates_in_database_format`), a captive-power
batch's workbook carries **three review-context tabs** that capture the research reasoning, not just
the staged edits. They are built by dedicated `build_review_package.py` builders, each **gated on the
presence of its own staging JSON** in `--inputs-dir`, so a normal Update batch (which lacks those
files) is unaffected. Author the three JSONs alongside `staged_updates.json` and commit them (audit
trail). All URLs in these tabs pass `url_verifier.py` the same as any staged cell — no exceptions.

1. **`terminal_first_priors`** ← `captive_terminal_first.json` (one row per crawled terminal).
   Columns: `terminal`, `terminal_id`, `mechanical`, `confidence`, `gogpt_captive_prior`
   (what the deterministic matcher's prior was — usually "none" or a *false* C-tier neighbor),
   `confirmed_how` (how the captive verdict was reached by researching the terminal's OWN drive tech),
   **`confirmed_how [ref]`** (the verifying URLs). This tab is the terminal-first audit: it shows, per
   terminal, that the confirmation came from the terminal's own tech, not from a GOGPT plant match —
   the direct answer to "did you cover terminals with no captive-flagged GOGPT plant nearby?"
2. **`neighboring_plants`** ← `captive_neighboring_plants.json` (nearest ~2 GOGPT gas plants per
   terminal by haversine). Columns: `terminal`, `terminal_id`, `rank`, `neighboring_plant`, `dist_km`,
   `gogpt_mw`, `gogpt_units`, `gogpt_captive`, `gogpt_status`, `subnational`, `relation` (WHY this
   plant is / isn't the terminal's captive power — usually "unrelated merchant/industrial plant"),
   **`info_url`** (an independent, non-gem.wiki source on the plant), and `gogpt_record (nav only)`
   (the plant's gem.wiki URL, rendered italic/gray — a navigation pointer to the GOGPT record, NEVER a
   citation). This tab makes the terminal-first point concrete: the physically-nearest GOGPT plants
   are typically NOT the terminal's captive power. Compute the nearest-neighbor set with
   `captive_power_colocation.py`'s `load_gogpt_plants(...)` + `haversine_km(...)` over the whole
   country (uncapped radius) — the default matcher radius returns 0 for terminals whose real captive
   power isn't a separate GOGPT record.
3. **`gogpt_candidates`** ← `captive_gogpt_candidates.json` (one row per confirmed-captive terminal).
   Columns: `terminal`, `terminal_id`, `gogpt_candidate` (verdict: `ADD` / `MAYBE` / `REVIEWER CALL` /
   `DO NOT ADD`, color-coded green/yellow), `electric_mw` (the *generating* MW only — leave undisclosed
   blank, never invent), `confidence`, `basis`, **`basis [ref]`**, and `mechanical_drive_note` (the
   shaft-power figure kept explicitly SEPARATE from `electric_mw`). This tab answers "which of these
   terminals should become NEW GOGPT power-station records" — see §4a.

## 4a. GOGPT-candidate research (on-request follow-on — GOGPT-side, memo + `gogpt_candidates` tab)

When the user asks which confirmed-captive terminals should become **new GOGPT power-station
records**, run one researcher per terminal and produce a companion memo
(`batches/captive_power_gogpt_candidates_<stamp>_ET_<area>.md`) plus the `gogpt_candidates` tab above.
This is **GOGPT-side proposal only — nothing is staged** (the LNG edit lane never creates a GOGPT
record). Governing principle, proven in Texas:

- **"Confirmed captive" ≠ "GOGPT power station."** A GOGPT record tracks *electricity generation*
  with a nameplate MW. Most captive LNG terminals generate little or no on-site gas-fired electricity —
  their captive power is **gas-turbine mechanical drive** (shaft power, zero MWe) or **grid-imported**,
  with only diesel emergency gensets on site. Only a terminal with a genuine, sourced, gas-fired
  *generating* plant (e.g. Port Arthur's FERC-certified 240 MW) is a clean candidate.
- **Never let mechanical-drive shaft power populate a GOGPT generating-MW.** The biggest gas MW at a
  liquefaction site is usually the Frame 7 / LM2500-class compressor drives (hundreds of MW aggregate
  shaft). Record it in `mechanical_drive_note`, never in `electric_mw` — doing otherwise fabricates
  nonexistent power supply (the same conflation flagged LNG-side per §4).
- Verdict scale: **ADD** (green — real, sourced generating plant) / **MAYBE** (yellow — cogeneration
  exists but MW undisclosed or pre-file) / **REVIEWER CALL** (generation exists but no citable
  nameplate) / **DO NOT ADD** (grid-fed or mechanical-drive-only; a green *negative* determination).
- **Where candidates go (2026-07-27):** ADD/MAYBE verdicts route to the sibling
  `gogpt-researcher` repo's Discovery workflow — its seed backlog
  (`notes/backlog_captive_power_candidates.md` there) points back at this SOP's
  `captive_gogpt_candidates.json` files. Nothing GOGPT-side is ever staged from this repo.

## 4. Recurring findings to expect (from the Louisiana test case)

- **GOGPT is ahead of the LNG tracker on flagging.** Most Tier-A pairs are GOGPT-captive but
  LNG `CaptiveGasPower=False` → the main actionable LNG-side gap is filling that field (+ its `[ref]`).
- **Mechanical-drive vs electric-generation capacity conflation.** GOGPT's aggregate MW for a
  "power station" record often bundles mechanical compressor-drive turbines with (or instead of)
  a dedicated electric plant. This does **not** change the captive verdict (mechanical-drive counts
  per §2), but it has two consequences: (a) mark the terminal `mechanical = True` so the review sheet
  shows the verdict rests on shaft-power turbines (fully so for a no-generator site like Woodside,
  partly for a mixed site like Sabine Pass / Commonwealth); (b) the GOGPT MW figure may not be a
  power-generation capacity — flag it in the memo, don't "fix" the LNG side to match.
- **`captiveIndustryType` tagging is inconsistent** (only some records use id 56 = "LNG
  production/liquefaction") — do NOT gate the match on the type field.
- **Status lead-lag** — GOGPT may show the captive plant in `construction` while the LNG terminal
  is still `proposed` (Delfin). Reconcile per the methodology: a confirmed FID stages `FIDStatus`,
  but FID ≠ construction — only flip lifecycle `Status → construction` with an explicit
  construction-start / NTP source, otherwise leave it and note the follow-up.

### 4b. The grid-access prior (Americas sweep, 2026-07-27)

Across 45 terminals covering every non-Gulf US terminal and every other country in the hemisphere,
the verdicts sorted on **grid access, not geography** — use this to set expectations, never as a
substitute for the crawl:

- **Grid-connected → electric drive, and they say so in a filing.** Every terminal within reach of a
  large hydro or utility grid chose e-drive and documented it in its environmental assessment or air
  permit (Tilbury, Cedar, Woodfibre, Summit Lake, Placentia Bay). **For a grid-connected North
  American project after roughly 2015 the prior is NO** — and these negatives are *documented*, so
  they're worth recording as such in `terminal_first_priors` rather than left as "not researched".
- **No grid → self-generation at scale.** Remote and off-grid sites generate their own power by
  necessity: Kenai and Alaska LNG, moored FLNGs (an FLNG at a permanent mooring is off-grid almost by
  construction), and remote-coast projects predating the electrification turn (Goldboro, Ksi Lisims'
  contingency case).
- **Caribbean / island terminals are usually the OPPOSITE relationship.** They exist to *feed* a
  power station — `PowerPlantsSupplied`, never captive (Peñuelas, San Juan, Costa Norte, Andrés all
  fail the direction test cleanly). Expect these to also surface blank `PowerPlantsSupplied` cells:
  route them to an Update batch, never stage them from a captive batch.
- **A "committed design vs approved contingency" split is a reviewer call, not a research gap.**
  Ksi Lisims is committed to grid e-drive but holds an approved 603 MW contingency case; staged
  **yellow** so a reviewer rules on it. Where the driver study itself was *deferred* and never done
  (Placentia Bay, AMIGO FLNG), the answer is INSUFFICIENT — preserve the MW finding in `qa_review`
  for a future revival, don't stage it.

## 5. Escalate to the user when

- The mechanical-vs-electric (or any other) scope boundary is genuinely ambiguous on a candidate —
  resolve it before staging, never stage-with-doubt.
- A GOGPT-side capacity looks systematically wrong across many records (schema/definition issue,
  not a per-record finding).
- More than ~5 confirmed new captive pairs surface in one area (worth a conversation before a
  large staging batch), or you're about to scale past the current area.

## 6. Data-access reference

- LNG = `plant."projectType" = 8`; state = the `State/Province` export column. LNG captive handles =
  `CaptiveGasPower` (bool) + `PowerPlantsSupplied`.
- GOGPT = `plant."projectType" = 1` + `powerplant_unit."trackerSearch" = 'GOGPT'`. Captive block =
  `plant.captive` (bool) + `captiveIndustryType` (jsonb array of ids into `captive_industry_type`;
  id 56 = "LNG production / liquefaction") + `captiveIndustryUse` (power/heat/both).
- GOGPT unit status = `powerplant_unit.status_id` → `status` table. (This is NOT the LNG
  `status_timeline` pattern, which returns 0 rows for GOGPT units.)
