# Unit Conventions (LNG Terminals)

Operational reference for terminal-naming, unit-naming, and project subdivision rules. The methodology doc is authoritative; this file is the working summary used at batch time.

## Project-level naming

### Standard onshore terminal name

Format: `<Site> LNG Terminal`

- `<Site>` is the location, sponsor, or given name. Examples: Sabine Pass LNG Terminal, Cameron LNG Terminal, Mozambique LNG Terminal.
- If a terminal has a widely-used given name, use that adapted to GEM's format.
- Alternative widely-used names go in the `Name Other` field, separated by commas.

### Exceptions

| Pattern | Format | Example |
|---|---|---|
| Officially named "LNG <Place>" | `LNG <Place> Terminal` | LNG Canada Terminal |
| Floating export (FLNG) | `<Site> FLNG Terminal` | Cedar FLNG Terminal, Coral Sul FLNG |
| Floating import (FSRU) | `<Site> FSRU` | Stade FSRU, Sharjah FSRU — no "Terminal" suffix (would be redundant) |
| FSU / FRU (variants of FSRU) | `<Site> FSU` or `<Site> FRU` | (rare; use these only when project explicitly is FSU/FRU not full FSRU) |
| Offshore but not floating (Deepwater Port) | `<Site> Deepwater Port LNG Terminal` | Gibbstown Deepwater Port LNG Terminal |
| Onshore + offshore components | Use onshore convention | (treat as `<Site> LNG Terminal`) |

### When the name is unknown

Per methodology FAQ:

| Situation | Naming |
|---|---|
| Location known, sponsor unknown | `<Location> LNG Terminal` (e.g. Jorf Lasfar LNG Terminal) |
| Sponsor known, location TBD | `<Sponsor> LNG Terminal` (e.g. NewMed FLNG Terminal) |
| Both known, location-only is fine | `<Location> LNG Terminal` |
| Both known, need to specify sponsor (e.g. multiple terminals at same location) | `<Sponsor> <Location> LNG Terminal` (e.g. New Fortress Colombo LNG Terminal) |

If a project later gets a more official/widely-used name, update the GEM TerminalName to match (within GEM's format). The wiki URL updates automatically.

## Unit-level naming

### Default

Single-unit terminals get `UnitName = "--"` (literally two dashes). This is the default for most import terminals and small export projects.

### Multi-unit naming options

| Pattern | Use when |
|---|---|
| `Phase 1`, `Phase 2`, ... | Project is divided into phases with distinct timelines/funding |
| `Train 1`, `Train 2`, ... | Liquefaction project is divided into trains (especially when trains have distinct contracts, FIDs, or sub-status) |
| `T1`, `T2`, ... | Equivalent to `Train N`; use consistently within a project |
| `Capacity Expansion`, `Expansion 1`, ... | An expansion added to an existing single-unit terminal |
| `Stage 1`, `Stage 2`, ... | Common in US Gulf Coast projects (e.g. Corpus Christi Stage 3) |

### Multi-unit naming rules

1. **All units within a project must have different names.** The database raises a warning if duplicates.
2. **Units are ordered alphabetically by the database backend**, so name them so the alphabetical order is logical.
3. Per methodology, the correct treatment of grouped trains is one of:
   ```
   Train 1 and Train 2     ← bundled (acceptable if research found them together)
   Train 3
   Train 4
   ```
   OR
   ```
   Train 1                  ← individual (preferred)
   Train 2
   Train 3
   Train 4
   ```
   Avoid the methodology-flagged anti-pattern:
   ```
   Trains 1 and 2           ← appears AFTER Train 5 due to the "s"
   Train 3
   Train 4
   Train 5
   ```

### Unit name local

Optional field for the local-language name of the unit. Follow the same conventions translated to local language.

## When to create a new unit vs a new terminal

The methodology FAQ + the schema empirically suggest:

| Scenario | Treatment |
|---|---|
| New train added to existing export terminal | New **unit** within existing terminal |
| New phase added (formally a phase) | New **unit** within existing terminal |
| New expansion at existing terminal | New **unit** within existing terminal |
| Same site, fundamentally different project (different sponsor, different design, separate timeline) | New **terminal**, link via `AssociatedTerminals` |
| Adjacent site, separate project | New **terminal**, link via `AssociatedTerminals` if relevant |
| Same terminal but reviving after cancellation, same fundamentals | Existing **unit**, new timeline entry (per `lifecycle_rules.md` dead-and-revived) |
| Same terminal reviving after cancellation, different fundamentals | New **unit** |

## Subdivision guideline (from the methodology)

> Units in the database should be created for the *largest subdivisions of a project that can be tracked without losing information.*

Worked examples:

- 3 phases of 6 trains each, all trains within a phase share start date / cost / capacity → 3 units (one per phase)
- 3 phases of 6 trains each, individual trains within phases have distinct start dates → 18 units (one per train)
- Single import terminal with one expansion announced years later → 2 units (default unnamed unit + expansion unit)
- FSRU terminal that has hosted multiple vessels over time → each vessel deployment is a separate unit (per the empirical pattern observed in the GEM export, e.g. T100000130685 has BW Singapore retired, Energos Power operating, Höegh Gallant retired)

## Wiki conventions

Per methodology:

- Every terminal has a single wiki page at `https://www.gem.wiki/<TerminalName_with_underscores>`
- The wiki URL is updated automatically by the data team when TerminalName changes
- The data sections above "Background" are auto-generated
- **Researchers manually edit the Background section** (and only the Background section)
- For multi-unit projects, Background can have subsections per unit

## Owner field conventions

Per Discovery SOP §9 and the methodology Ownership section:

- **Immediate Owner**: the entity that directly owns the project
- **Parent**: the ultimate corporate parent
- **ParentHQCountry**: country of the ultimate parent's HQ
- **Parent GEM Entity ID**: the link into the GEM entity system

For multi-owner projects (JVs):
- List each immediate owner in the `Owner` field, comma-separated
- Include percentages when known: `ENI 50%, EGAS 40%, EGPC 10%`
- The Parent field lists the corresponding parent for the lead owner OR the parent of the JV entity if treated as a single entity

Per the methodology emphasis: **the GEM entity system is shared across trackers**. Always run `entity_lookup.py` before staging a new entity. Add canonical name to `entity_canonical_map.md`.

## Location conventions

Per the methodology:

| Field | Convention |
|---|---|
| Latitude / Longitude | WGS 84 decimal |
| Accuracy = `exact` | Coordinate from official source OR confirmed via satellite imagery |
| Accuracy = `approximate` | Project not yet built, OR location estimated from news, OR FSRU not currently geolocatable |
| Location free text | Free description (e.g. "Port of Corpus Christi, Nueces County, Texas") |
| Region, SubRegion | GEM region taxonomy; consult schema for current values |
| State/Province, Prefecture/District | Subnational divisions where applicable |
| Location [ref] | URL or source document for the location data |

Location data is entered at the **project level by default**, not unit level. Per-unit location only when a multi-unit project has units at meaningfully different sites (uncommon).

## Capacity conventions

Per the methodology and `gem_db_schema.md`:

- Numeric value in `Capacity` field
- Unit in `CapacityUnits` — **for LNG, use `mtpa` (preferred) or `bcm/y`**
- `CapacityinMtpa` and `CapacityinBcm/y` are read-only computed columns
- Project rollups in `TotImport...` / `TotExport...` columns are read-only
- Per methodology: **record the baseload/nameplate/nominal capacity, not peak**. If peak is interesting, note in wiki Background.
- Per methodology: **if a range is found, record the MAX in the database and the range in the wiki Background**
- For multi-unit projects, prefer **unit-level capacity** entry. Project-level only when unit breakdown is unknown.
- Conversion factor: 1 mtpa LNG ≈ 1.36 bcm/y natural gas (industry standard, though there's slight variation by gas composition; `capacity_normalize.py` handles)

## Cost conventions

- Numeric value in `Cost` field
- Currency code in `CostUnits` — common values include USD, EUR, RMB, RUB, KRW, JPY
- **CostYear is required when Cost is set** — methodology says CostYear = publication year of the source, for FX conversion timing
- `CostUSD` and `CostEuro` are read-only computed columns derived from Cost + CostUnits + CostYear
- Per methodology: cost should be the terminal construction cost only, not associated pipeline/upstream costs
- If a range is found, record the median in the database and the range in the wiki Background

## Boolean fields encoding

Per `gem_db_schema.md`: booleans are stored as `True` or blank (not `False`). To set a boolean false, write empty string.

Boolean fields: `Offshore`, `Floating`, `ImportExportOnly`, `CaptiveGasPower`, `Opposition`, `Defeated`, `LH2`, `NH3`, `SyntheticLNG`, `RetrofitProposed`, `AltFuelPrelimAgreement`, `AltFuelCallMarketInterest`, `CCS`. `TempFacility` is an enum-bool with values `interim`, `permanent replacement`, blank.

## Quick-reference card

| Question | Answer |
|---|---|
| New terminal at same site as existing? | New TerminalID, link via AssociatedTerminals |
| New train at existing export terminal? | New UnitID within existing TerminalID |
| FSRU vessel swap-out at same terminal? | Often new UnitID (per observed schema pattern); prior vessel's unit gets retired status |
| Operating terminal restarts after idle? | Same UnitID, new timeline entry, ActualStartYear2/3 may apply |
| Dead-and-revived proposal (same fundamentals)? | Same UnitID, new `proposed` timeline entry |
| Dead-and-revived (different fundamentals)? | New UnitID |
| Range of capacities found? | Max in database, range in wiki Background |
| Range of costs found? | Median in database, range in wiki Background |
| Both LNG and oil at same terminal? | Out of project scope for LNG database; if LNG capacity exists, terminal is included as LNG; oil is separate |
| FSU/FRU (not FSRU)? | Use FSU or FRU in name; same rules otherwise |
| Single-unit project, want to leave UnitName blank? | Set to `--` (literal two dashes) |
