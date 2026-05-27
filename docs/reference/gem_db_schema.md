# GEM Database Schema (LNG Terminals)

Reference for the GEM project-database all-fields LNG export. Derived empirically from the 2026-05-26 export (1,263 unit-rows across 859 terminals, 115 columns).

The authoritative schema source is the live database. This doc captures what the **CSV export** looks like, which is the entry point for all SOPs.

## Pull command

```bash
python pull_gem_db.py
```

Wraps `gem_export_via_web.py` (uploaded by the user). Requires `GEM_PROJECT_DB_SESSIONID` and `GEM_PROJECT_DB_CSRFTOKEN` env vars set from the user's browser session — cookies expire periodically, re-export when auth fails. Output at `gem_export.csv` with a sibling `./gem_export.colmap.json` containing the derived column-index map.

## Row structure

- **One row per unit.** A multi-unit terminal has one row per unit, with project-level fields duplicated across all unit-rows.
- **TerminalID** identifies the project (e.g. `T100000130274`).
- **UnitID** identifies the unit (e.g. `G100002027401`).
- Unit ordering in the export is not stable batch-to-batch — re-derive `(TerminalID, UnitName)` keys on every batch.

Distribution of units per terminal (May 2026 export):

| Units | Count |
|---:|---:|
| 1 | 645 terminals |
| 2 | 127 |
| 3 | 46 |
| 4 | 20 |
| 5 | 10 |
| 6–13 | 11 |

About 75% of terminals are single-unit; 25% are multi-unit with a long tail. Multi-unit projects matter disproportionately because they're usually larger and more complex export terminals.

## Status timeline is NOT in the export

This is the single most important schema fact and the methodology doc doesn't make it obvious.

The export contains:
- The **current** `Status` and `Substatus`
- A flat set of **anchor years** (`ProposalYear`, `ConstructionYear`, `OriginalPlannedStartYear`, `LatestPlannedStartYear`, `ActualStartYear`, `ActualStartYear2`, `ActualStartYear3`, `ShelvedYear`, `CancelledYear`, `StopYear`, `PlannedStopYear`, `FIDYear`)

The export does NOT contain:
- The ordered status timeline with all historical entries
- Per-entry notes
- Part-of-year information (month/quarter/half)
- Data-entry timestamps for individual entries

**Implication:** any batch that adds or modifies a status timeline entry must pull the existing timeline from the live DB first, via `fetch_timeline.py <UnitID>`. Otherwise, you risk:
- Appending a duplicate entry that already exists
- Re-ordering entries unintentionally (the methodology says the timeline is append-only except for genuine error corrections)
- Losing context that the methodology requires preserving

See `lifecycle_rules.md` for the rules that derive current status from a timeline.

## Field classification: project-level vs unit-level vs mixed

The methodology doc treats some fields as "project-level" and others as "unit-level," but empirically several fields the manual classifies as project-level vary across units in practice. This matters for the build script: writing a "project-level" update to only one unit-row produces an inconsistent next-export.

Empirical analysis: for each multi-unit terminal (214 of them in the May 2026 export), count what percentage have the same value across all unit-rows. ≥95% = treat as project-level; ≤30% = treat as unit-level; everything in between is mixed.

### Definitely project-level (apply to all unit-rows on edit)

Identity, location, classification, totals, opposition/CCS flags, and the entire set of "no longer updated" fields:

```
TerminalID, Wiki, TerminalName, Country/Area, Region, SubRegion,
Prefecture/District, State/Province, Latitude, Longitude, Accuracy,
Location, Location [ref],
OtherNames, LocalNames, Language,
ResearcherNotesProject,
Fuel, ImportExportOnly,
Offshore, Floating, FloatingVesselName, FloatingVesselName [ref],
VesselOwner, VesselOwner [ref], VesselParent, VesselOperator, VesselOperator [ref],
AssociatedTerminals, AssociatedTerminals [ref],
Source, Source [ref],
PowerPlantsSupplied, PowerPlantsSupplied [ref],
CaptiveGasPower, CaptiveGasPower [ref],
Pipelines, Pipelines [ref],
TotImportLNGTerminalCapacityinMtpa, TotImportLNGTerminalCapacityinBcm/y,
TotExportLNGTerminalCapacityinMtpa, TotExportLNGTerminalCapacityinBcm/y,
TotKnownTerminalCostsUSD, TotTerminalCost [ref],
Opposition, ESJNotes, Defeated, CCS, CCSNotes,
PCINotes, PCI3, PCI4, PCI5, PCI6,
LH2, NH3, SyntheticLNG, RetrofitProposed,
AltFuelPrelimAgreement, AltFuelCallMarketInterest
```

The "Tot…" totals appear identical across all unit-rows because they're project-wide rollups computed by the GEM backend. **Don't write to these directly** — they'll be recomputed from unit-level capacity changes.

### Definitely unit-level (apply only to the targeted unit-row)

```
UnitID, UnitName, Capacity, CapacityinMtpa, CapacityinBcm/y, StartDate [ref]
```

Plus the timeline-related fields (see "mixed" below) which are usually unit-level for multi-phase projects.

### Mixed / context-dependent (the build script must decide per case)

These are nominally project-level per the manual but vary across unit-rows in real data. Common cause: phases or trains added at different times with different owners, costs, or status histories. The build script should:
- Read the existing value across all unit-rows of the target project
- If currently consistent → apply the change to all unit-rows
- If currently inconsistent → apply the change only to the targeted unit-row, flag in `qa_review` for human review

```
FacilityType, FacilityType [ref]            (91% consistent — almost always project-level)
Status, Substatus, Status [ref]             (47% / 59% / 31% — clearly unit-level in multi-phase projects)
Researcher, LastUpdated                     (per-unit by design — different researchers touch different units)
ResearcherNotesUnit                         (per-unit by design)
Owner, Owner [ref]                          (82% / 85% — usually project-level, JV/phase differences exist)
Parent, ParentHQCountry, Parent GEM Entity ID  (85% — same as Owner)
CapacityUnits, Capacity [ref]               (82% / 91% — usually consistent within a project)
ProposalYear, ProposalMonth, ProposalDate [ref]    (53% / 66% / 45% — different phases proposed at different times)
ConstructionYear, ConstructionMonth, ConstructionDate [ref]   (54% / 66% / 55%)
OriginalPlannedStartYear, LatestPlannedStartYear   (43% / 43%)
ActualStartYear, ActualStartMonth, ActualStartYear2, ActualStartYear3   (47% / 73% / 97% / —)
ShelvedYear, ShelvedYear [ref], CancelledYear, CancelledYear [ref]   (~88-94%)
StopYear, StopYear [ref], PlannedStopYear   (83% / 86% / 98%)
ShelvedCancelledStatusType                  (86%)
Cost, CostUnits, CostYear, CostUSD, CostEuro, Cost [ref]   (45-92%)
FIDStatus, FIDYear, FIDYear [ref]           (81-83%)
Financing, Financing [ref]                  (89% / 95%)
TempFacility                                (99% — almost always project-level)
```

`ActualStartYear2` is interesting: 97% consistent suggests it's almost always blank or duplicated, used rarely for unit-specific corrections.

## All 115 columns

Indexed in export order. The "Klass" column indicates classification per the analysis above: **P** = project-level, **U** = unit-level, **M** = mixed/context-dependent. The "Notes" column flags read-only and out-of-scope fields.

| Idx | Column | Klass | Notes |
|---:|:---|:---:|:---|
| 0 | TerminalID | P | Read-only (DB-assigned). `T100000NNNNNN` format. |
| 1 | UnitID | U | Read-only (DB-assigned). `G100002NNNNNN` format. |
| 2 | Wiki | P | URL to `gem.wiki/<TerminalName>`. Updated automatically. |
| 3 | TerminalName | P | See methodology naming conventions. |
| 4 | UnitName | U | `--` for default; phase / train / expansion name otherwise. |
| 5 | FacilityType | M | Enum: `import`, `export`. |
| 6 | FacilityType [ref] | M | |
| 7 | Fuel | P | Enum: `LNG`, `Oil`, `NGL`, `NH3`, `LH2`, `eLNG`, `Oil+NGL`, `Oil+Fuels`. **Filter to `LNG` for standard work.** |
| 8 | Status | M | Enum: `proposed`, `construction`, `operating`, `idled`, `mothballed`, `retired`, `shelved`, `cancelled`. |
| 9 | Substatus | M | Enum: `actual`, `confirmed`, `inferred 2 y`, `inferred 4 y`. Note the year-threshold embedding. |
| 10 | Status [ref] | M | |
| 11 | Country/Area | P | Free text; normalize via `normalize.py`. |
| 12 | Researcher | M | Per-unit by design. |
| 13 | LastUpdated | M | Per-unit by design. ISO date. Used by `stale_sweep.py`. |
| 14 | ResearcherNotesUnit | M | Per-unit by design. |
| 15 | ResearcherNotesProject | P | |
| 16 | OtherNames | P | Comma-separated. |
| 17 | LocalNames | P | Comma-separated. |
| 18 | Language | P | Free text. |
| 19 | Owner | M | Immediate owner. Comma-separated if multiple. Entity lookup required. |
| 20 | Owner [ref] | M | |
| 21 | Parent | M | Ultimate parent. |
| 22 | ParentHQCountry | M | |
| 23 | Parent GEM Entity ID | M | The entity-system link. |
| 24 | Operator | P | |
| 25 | Operator [ref] | P | |
| 26 | Capacity | U | Numeric. |
| 27 | CapacityUnits | M | Enum: `mtpa`, `bcm/y`, `bpd`, `bcf/d`, `MMcf/d`, `gal/day`, `tpa`, `MWh/d`, `TJ/d`. **For LNG terminals, use `mtpa` or `bcm/y` only.** Other units are mostly oil terminals. |
| 28 | CapacityinMtpa | U | Computed from Capacity + CapacityUnits. Read-only. |
| 29 | CapacityinBcm/y | U | Computed. Read-only. |
| 30 | Capacity [ref] | M | 86% blank in current export → high-value [ref]-fill target. |
| 31 | TotImportLNGTerminalCapacityinMtpa | P | Project-wide rollup. Read-only. |
| 32 | TotImportLNGTerminalCapacityinBcm/y | P | Read-only. |
| 33 | TotExportLNGTerminalCapacityinMtpa | P | Read-only. |
| 34 | TotExportLNGTerminalCapacityinBcm/y | P | Read-only. |
| 35 | ProposalYear | M | |
| 36 | ProposalMonth | M | |
| 37 | ProposalDate [ref] | M | 49% blank in current export → high-value [ref]-fill target. |
| 38 | ConstructionYear | M | |
| 39 | ConstructionMonth | M | |
| 40 | ConstructionDate [ref] | M | 78% blank → high-value [ref]-fill target. |
| 41 | OriginalPlannedStartYear | M | Methodology: original target for tracking slippage. |
| 42 | LatestPlannedStartYear | M | Updated as project slips. |
| 43 | ActualStartYear | M | Set when operation begins. |
| 44 | ActualStartMonth | M | |
| 45 | ActualStartYear2 | M | Rare; used for restarts after idling. |
| 46 | ActualStartYear3 | M | Rare. |
| 47 | StartDate [ref] | U | 32% blank → high-value [ref]-fill target. |
| 48 | ShelvedYear | M | |
| 49 | ShelvedYear [ref] | M | |
| 50 | CancelledYear | M | |
| 51 | CancelledYear [ref] | M | |
| 52 | StopYear | M | When operation stopped (mothballed/retired/idled). |
| 53 | StopYear [ref] | M | |
| 54 | PlannedStopYear | P | |
| 55 | ShelvedCancelledStatusType | M | Enum: `inferred`, `confirmed`. Duplicates info in Substatus. |
| 56 | TempFacility | P | Enum: `interim`, `permanent replacement`, blank. |
| 57 | ImportExportOnly | P | Boolean. True = terminal imports/exports without regas/liquefaction. |
| 58 | Location | P | Free-text location string. |
| 59 | Region | P | GEM region taxonomy. |
| 60 | SubRegion | P | GEM sub-region taxonomy. |
| 61 | Prefecture/District | P | |
| 62 | State/Province | P | |
| 63 | Latitude | P | Decimal WGS 84. |
| 64 | Longitude | P | Decimal WGS 84. |
| 65 | Accuracy | P | Enum: `exact`, `approximate`. |
| 66 | Location [ref] | P | |
| 67 | AssociatedTerminals | P | Comma-separated terminal names. |
| 68 | AssociatedTerminals [ref] | P | 95% blank. |
| 69 | Source | P | "Fuel source" — gas field, not URL source. |
| 70 | Source [ref] | P | 89% blank. |
| 71 | PowerPlantsSupplied | P | |
| 72 | PowerPlantsSupplied [ref] | P | 89% blank. |
| 73 | CaptiveGasPower | P | Boolean. Per methodology, new priority for 2026. |
| 74 | CaptiveGasPower [ref] | P | 99.7% blank — this whole field set is essentially unpopulated. |
| 75 | Pipelines | P | |
| 76 | Pipelines [ref] | P | 90% blank. |
| 77 | Cost | M | Numeric. |
| 78 | CostUnits | M | Currency code. 18 values seen including `USD`, `RMB`, `EUR`, `RUB`, `KRW`, `JPY`, `AUD`, `INR`, etc. |
| 79 | CostYear | M | Publication year of the cost source (per methodology, for FX timing). |
| 80 | CostUSD | M | Computed from Cost + CostUnits + CostYear. Read-only. |
| 81 | CostEuro | M | Computed. Read-only. |
| 82 | Cost [ref] | M | 88% blank → high-value [ref]-fill target. |
| 83 | TotKnownTerminalCostsUSD | P | Project-wide rollup. Read-only. |
| 84 | TotTerminalCost [ref] | P | 100% blank. |
| 85 | FIDStatus | M | Enum: `Pre-FID`, `FID`, blank. Methodology: only set when explicit reporting exists. |
| 86 | FIDYear | M | |
| 87 | FIDYear [ref] | M | 86% blank. |
| 88 | Financing | M | Free text. |
| 89 | Financing [ref] | M | 92% blank. |
| 90 | Offshore | P | Boolean (`True` or blank). |
| 91 | Floating | P | Boolean. If `True`, terminal is FSRU/FLNG/FSU/FRU. |
| 92 | FloatingVesselName | P | Vessel name when floating. **FSRU sync touchpoint.** |
| 93 | FloatingVesselName [ref] | P | 92% blank. |
| 94 | VesselOwner | P | **FSRU sync touchpoint.** |
| 95 | VesselOwner [ref] | P | 95% blank. |
| 96 | VesselParent | P | |
| 97 | VesselOperator | P | |
| 98 | VesselOperator [ref] | P | 95% blank. |
| 99 | Opposition | P | Boolean. |
| 100 | ESJNotes | P | Free text. |
| 101 | Defeated | P | Boolean. |
| 102 | PCINotes | P | **READ-ONLY** — methodology: PCI no longer maintained. |
| 103 | PCI3 | P | **READ-ONLY**. |
| 104 | PCI4 | P | **READ-ONLY**. |
| 105 | PCI5 | P | **READ-ONLY**. |
| 106 | PCI6 | P | **READ-ONLY**. |
| 107 | LH2 | P | **READ-ONLY** — methodology: alt-fuel tracking no longer updated as of 2026. |
| 108 | NH3 | P | **READ-ONLY**. |
| 109 | SyntheticLNG | P | **READ-ONLY**. |
| 110 | RetrofitProposed | P | **READ-ONLY**. |
| 111 | AltFuelPrelimAgreement | P | **READ-ONLY**. |
| 112 | AltFuelCallMarketInterest | P | **READ-ONLY**. |
| 113 | CCS | P | Boolean. **In scope** (CCS is still tracked). |
| 114 | CCSNotes | P | Free text. **In scope.** |

### Read-only column list (build script must NEVER write to these)

Computed/rollup columns (overwritten by DB):

```
CapacityinMtpa, CapacityinBcm/y,
TotImportLNGTerminalCapacityinMtpa, TotImportLNGTerminalCapacityinBcm/y,
TotExportLNGTerminalCapacityinMtpa, TotExportLNGTerminalCapacityinBcm/y,
CostUSD, CostEuro,
TotKnownTerminalCostsUSD, TotTerminalCost [ref],
TerminalID, UnitID, Wiki
```

Out-of-scope per methodology (no longer updated as of 2026):

```
PCINotes, PCI3, PCI4, PCI5, PCI6,
LH2, NH3, SyntheticLNG, RetrofitProposed,
AltFuelPrelimAgreement, AltFuelCallMarketInterest
```

(`AltFuelNotes` is in the manual but not in the export — likely renamed or merged.)

## Enum value catalogs

Lifted from the May 2026 export. Values that don't appear in this catalog should be treated as suspect — flag in `qa_review` rather than auto-accept.

### Status

`proposed` (290) · `construction` (103) · `operating` (414) · `idled` (10) · `mothballed` (16) · `retired` (28) · `shelved` (98) · `cancelled` (303)

(Plus 1 blank row.)

### Substatus (by Status)

- `proposed`: blank (287), `actual` (3)
- `construction`: `actual` (103)
- `operating`: `actual` (414)
- `idled`: `actual` (10)
- `mothballed`: `actual` (16)
- `retired`: `actual` (28)
- `shelved`: `inferred 2 y` (73), `confirmed` (25)
- `cancelled`: `inferred 4 y` (175), `confirmed` (125), `actual` (3)

The methodology describes "actual" and "planned" as sub-statuses, but the export never shows `planned` — likely because the export only emits the current status, and planned-status entries live only in the timeline. `planned` will appear in timeline data fetched via `fetch_timeline.py`.

The `inferred 2 y` / `inferred 4 y` values encode the year-threshold rule (2 years for inferred shelved, 4 years for inferred cancelled) directly into the substatus string. `stale_sweep.py` uses these.

### CapacityUnits

For LNG terminals (Fuel = `LNG`): **use `mtpa` (preferred) or `bcm/y`.**

Full enum seen: `mtpa` · `bcm/y` · `bpd` · `bcf/d` · `MMcf/d` · `gal/day` · `tpa` · `MWh/d` · `TJ/d`

Non-LNG units (`bpd`, `bcf/d`, `MMcf/d`, etc.) appear on the 51 non-LNG rows (oil, NGL, NH3, LH2, eLNG). If a new value is needed for an LNG terminal, the methodology says to flag Rob/Baird rather than invent a unit.

### FacilityType

`import` (753) · `export` (509)

### Fuel

For standard work: filter to `LNG` (1,212 rows). Other values exist but are out of scope: `Oil` (35), `NGL` (5), `NH3` (6), `LH2` (2), `eLNG` (1), `Oil+NGL` (1), `Oil+Fuels` (1).

### FIDStatus

Blank (1,056) · `Pre-FID` (111) · `FID` (96)

Per methodology FAQ: only set when there's explicit reporting. Historical "pre-FID by default" entries were cleaned in the 2025 cycle.

### ShelvedCancelledStatusType

Blank (842) · `inferred` (262) · `confirmed` (159)

Denormalized — duplicates Substatus information. Both should be kept in sync.

### Accuracy

`exact` (594) · `approximate` (639)

### Country/Area

Free text but stable. Use ISO country names where possible. Top 15 countries (US, China, Japan, Canada, Australia, Russia, Indonesia, India, Vietnam, Brazil, Nigeria, Mexico, Papua New Guinea, Italy, South Korea) cover ~60% of all units.

### Boolean fields

Encoded as `True` or blank (not `False`). The boolean columns are:

```
Offshore, Floating, ImportExportOnly, CaptiveGasPower, TempFacility (enum-bool),
Opposition, Defeated, LH2, NH3, SyntheticLNG, RetrofitProposed,
AltFuelPrelimAgreement, AltFuelCallMarketInterest, CCS
```

To set false, write the empty string, not the literal `False`.

## ID and URL formats

- **TerminalID**: `T100000NNNNNN` (e.g. `T100000130274`)
- **UnitID**: `G100002NNNNNN` (e.g. `G100002027401`)
- **Wiki**: `https://www.gem.wiki/<TerminalName_with_underscores>` — matches the TerminalName per methodology. Updated automatically when TerminalName changes.

The IDs are assigned by the GEM database backend. Never invent or modify them.

## [ref] columns — fill priorities

24 [ref] columns paired with data columns. Blank-percentage indicates fill priority (high-blank with high-populated paired data = good [ref]-fill targets).

| [ref] column | % blank | Fill priority |
|---|---:|---|
| CaptiveGasPower [ref] | 99.7% | Low — paired field is essentially unpopulated |
| TotTerminalCost [ref] | 100% | Skip — paired field is a computed rollup |
| AssociatedTerminals [ref] | 95.0% | Low — paired field also sparse |
| VesselOperator [ref] | 94.8% | Med — relevant for FSRU/FLNG only |
| VesselOwner [ref] | 94.7% | Med — relevant for FSRU/FLNG only |
| ShelvedYear [ref] | 93.4% | Med — relevant when shelved status confirmed |
| FloatingVesselName [ref] | 92.2% | Med — FSRU/FLNG only |
| Financing [ref] | 92.0% | Med — financing data sparse to begin with |
| CancelledYear [ref] | 90.5% | Med |
| Pipelines [ref] | 89.6% | Low |
| Source [ref] | 89.1% | Low — refers to gas field source, sparsely populated |
| PowerPlantsSupplied [ref] | 88.6% | Low |
| Cost [ref] | 88.4% | **High** — paired Cost data is broadly populated |
| StopYear [ref] | 86.9% | Low |
| FIDYear [ref] | 86.2% | Med — FIDYear is sparse, but when present should have ref |
| Capacity [ref] | 85.7% | **High** — paired Capacity is densely populated |
| ConstructionDate [ref] | 77.5% | **High** — Construction year is densely populated |
| Operator [ref] | 66.1% | **High** — Operator is densely populated |
| ProposalDate [ref] | 49.1% | **High** — Proposal year is densely populated |
| StartDate [ref] | 31.9% | **High** — Start year is densely populated |
| Status [ref] | 24.4% | **High** — Status is universal |
| Owner [ref] | 8.6% | Med — already mostly populated |
| Location [ref] | 9.7% | Med — already mostly populated |
| FacilityType [ref] | 9.6% | Med — already mostly populated |

**[ref]-fill targets in order of expected yield: Capacity, ConstructionDate, ProposalDate, Operator, Cost, StartDate, Status.**

## Schema drift detection

`pull_gem_db.py` derives the column-index map from the header row on every pull. If a known column doesn't appear, the script flags it. The expected-column list lives in `pull_gem_db.py`'s `EXPECTED_COLUMNS` dict — update it when GEM adds or renames a column.

Indicators of meaningful schema drift:
- New column appears that's not in `EXPECTED_COLUMNS` → review whether it's a new in-scope field or a backend-only addition
- A column expected by `EXPECTED_COLUMNS` disappears → likely renamed; check the live DB edit UI
- A column's value distribution shifts dramatically (e.g. `Substatus` gains a new enum value) → may indicate the methodology has changed

Before running a batch after detected drift, view the live DB unit edit page for one or two units to confirm the schema is what you expect, and update `EXPECTED_COLUMNS` plus this schema doc.
