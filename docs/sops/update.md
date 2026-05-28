# LNG Terminals Update SOP

Last revised: 2026-05 (rev 1, initial draft)

Operational rules for updating existing terminals in the GEM LNG terminals database. This is the bread-and-butter workflow of the annual cycle: refreshing data on terminals already in the database, adding new timeline entries, filling blank `[ref]` citations, and processing stale-sweep flags.

The methodology doc (LNG Terminals Manual) is authoritative for the underlying research rules. This SOP is operational — describes how to execute the work, citing the methodology rather than restating it.

## §1 When to run this SOP

Trigger conditions:
- Triage SOP has selected a country/region for update this batch
- A reconciliation batch produced `giignl_to_action` findings routed to Update
- The user explicitly requests an update batch ("refresh the Japan terminals", "fill blank Capacity refs for the EU rows")
- Stale-sweep flagged units passing dormancy thresholds (inferred shelved at 2y, inferred cancelled at 4y)
- A specific news event triggers a known-needed update (a recent FID announcement, a confirmed shelving, a vessel reassignment)

## §2 Confirm parameters at batch start

Before any tool runs, confirm:

1. **Scope** — which terminals are in scope. Options:
   - A country or set of countries (e.g. "all Japan terminals")
   - A status filter (e.g. "all `proposed` units globally with `LastUpdated > 12 months`")
   - A list of specific UnitIDs (from reconciliation routing or user-supplied)
   - A field focus (e.g. "all blank `Capacity [ref]` paired with populated Capacity")
2. **Sub-type focus** — which of the four update sub-types is primary for this batch (see §3). Many batches mix them, but understanding the primary type guides time allocation.
3. **Depth** — light refresh (verify current data, fill blank refs) vs deep refresh (re-research from sources, propose value changes). Light is faster, lower-risk, appropriate for `operating` units in stable markets. Deep is needed when triage signals a country has been neglected or when a major development is suspected.
4. **Whether timeline pulls are anticipated** — any status change requires `fetch_timeline.py` per unit. If many status changes are expected (e.g. processing a backlog of confirmed shelvings), allocate batch time accordingly — this is the slowest part of the workflow.
5. **FSRU handling** — if scope includes FSRU terminals, the FSRU sync rule applies (CLAUDE.md). Cross-check against the carrier project backend at batch end.

These parameters get written into the staging xlsx README sheet.

## §3 The four update sub-types

Most batches mix these, but it helps to understand each as a distinct recipe.

### §3.1 [ref]-fill (carrier-project parallel)

Direct port of the carrier [ref]-fill workflow. For each row in scope:
- Identify `[ref]` columns that are blank AND have populated paired data values
- Source-search for URLs that contain the value verbatim
- Apply the URL verification gate (§7)
- Stage the fill with appropriate confidence color

Priority columns by yield (from `docs/reference/gem_db_schema.md`):
1. `Capacity [ref]` — 86% blank, paired with `CapacityinMtpa` which is densely populated
2. `ConstructionDate [ref]` — 78% blank, paired with `ConstructionYear`
3. `ProposalDate [ref]` — 49% blank, paired with `ProposalYear`
4. `Operator [ref]` — 66% blank, paired with `Operator`
5. `Cost [ref]` — 88% blank, paired with `Cost`
6. `StartDate [ref]` — 32% blank, paired with `ActualStartYear`
7. `Status [ref]` — 24% blank, paired with `Status`

**Rule F (no orphan citations) applies** — never fill a `[ref]` without a paired data value in the same row. The methodology FAQ confirms: a citation must support a specific data point.

### §3.2 Status / timeline updates

Adding a new timeline entry, changing current status, or correcting a prior entry. **The most rule-bound sub-type** — `docs/reference/lifecycle_rules.md` governs end-to-end.

Workflow:
1. `python fetch_timeline.py <UnitID>` — pull the existing timeline from the live DB (mandatory; the export doesn't contain it)
2. Verify the proposed change is a legal state transition (`docs/reference/lifecycle_rules.md` "Legal state transitions")
3. If adding a planned entry, locate the correct insertion point (typically after the most recent matching actual)
4. If adding an actual entry, append to the bottom of the timeline
5. Backfill the corresponding anchor year column if it's blank (e.g. confirming construction start → populate `ConstructionYear` if blank)
6. Backfill the paired `[ref]` column for the anchor year
7. Stage in `status_timeline_additions` sheet AND update the unit row in `updates` sheet

Special cases per `docs/reference/lifecycle_rules.md`:
- **Inferred shelved/cancelled additions** — substatus `inferred 2 y` or `inferred 4 y`; datasource can re-use the source for the latest active entry per methodology FAQ
- **Shelved → cancelled escalation** — substatus `confirmed` (not `inferred`) per methodology FAQ; same datasource as the prior shelved entry
- **Dead-and-revived** — same unit (new `proposed` entry) if same fundamental proposal; new unit if significantly different
- **FID milestone** — separate timeline entry with substatus `actual` or `planned`; does NOT change unit Status

### §3.3 Value updates (capacity, cost, ownership, etc.)

Most source-search-intensive sub-type. Adding or changing data values where the change isn't a status transition. Common cases:

- **Capacity revision** — debottlenecking, expansion of a single train, restatement of nameplate. Use `capacity_normalize.py` for any unit conversion. Per methodology, range values store the max in the spreadsheet with the range in the wiki Background section.
- **Cost addition or update** — new cost figure published, or year-stamp + currency conversion to USD/EUR. Methodology requires `CostYear` to be the publication year of the source for FX conversion purposes.
- **Ownership change** — new operator, equity stake change, JV restructuring. Run `entity_lookup.py` for every new entity name; if creating a new entity, add to `entity_additions` sheet.
- **FSRU vessel change** — vessel swap-out at an FSRU terminal. Triggers FSRU sync rule (CLAUDE.md). The prior vessel typically gets a status timeline entry on its associated terminal row (idled/retired); the new vessel gets entered on the receiving terminal row.
- **Location refinement** — coordinates becoming more precise (e.g. from `approximate` to `exact`). Always update `Accuracy` along with lat/lng.

For each value update:
- Source-search per §4
- URL-verify per §7
- Apply confidence color per §6
- Stage in `updates` sheet

### §3.4 Stale-driven sweeps

Processing `stale_sweep.py` output. Mechanical compared to the others — the rule is in `docs/reference/lifecycle_rules.md`, the work is mostly verification + entry.

For each flagged unit:
1. Quick news search to confirm genuine dormancy (sometimes units are stale because of researcher capacity, not because the project is dormant)
2. If genuinely dormant, follow the §3.2 timeline-update workflow with substatus `inferred 2 y` or `inferred 4 y`
3. If active development is found, the result is a regular value/status update (§3.2 or §3.3), and the stale flag is incidentally cleared by virtue of `LastUpdated` becoming current

Batches that are dominated by stale-sweep tend to be high-throughput, low-research-depth.

## §4 Source-search strategy by field

Different fields have different best-source-tiers. Use `docs/reference/source_roster.md` for the full ranked list; this is the field-specific quick reference.

| Field | Best primary | Best corroborator | Caution |
|---|---|---|---|
| Status (sponsor announcement) | Sponsor IR / press release | Reuters, Bloomberg, S&P Global | Trade press sometimes leads sponsor IR by hours-days |
| Capacity (nameplate) | Sponsor IR + project filings (FERC/DOE/EU PCI) | GIIGNL annual report, sponsor presentations | Operational capacity ≠ nameplate; methodology says use nameplate |
| Construction start | Sponsor PR + ground-breaking news | Trade press, regulator approval dates | "Site prep" vs "active construction" is fuzzy — see methodology |
| FID | Sponsor IR (definitive) | S&P Global, Reuters | "Pre-FID with funding lined up" ≠ FID; methodology says only mark FID with explicit announcement |
| Cost | Sponsor IR + regulatory filings (FERC, EU PCI portal) | Trade press estimates | Always record `CostYear` = publication year of source; FX conversion needs this |
| Ownership | Sponsor IR + regulatory filings + entity registries | Trade press, recent annual reports | Immediate owner vs ultimate parent — keep distinct per schema |
| Operator | Sponsor IR + regulatory filings | Trade press | Sometimes Owner ≠ Operator for FSRUs |
| Location coordinates | Regulator approval docs (FERC, EU PCI), satellite imagery | Sponsor maps | Wiki coordinates are sometimes stale; verify against satellite |
| FSRU vessel name | Marine traffic services (marinetraffic.org, vesselfinder), sponsor PR | Trade press | Vessel reassignments happen mid-year; check timeline carefully |
| FSRU vessel IMO | Marine traffic services | Class society registries (DNV, ABS, LR, KR, ClassNK) | FSRU sync rule cross-check |
| Pipelines / PowerPlantsSupplied | Operator IR, regulatory filings | Trade press, country regulator | Often missing from primary sources; secondary sources fill gaps |
| CCS | Sponsor sustainability reports, sponsor PR | Trade press | New priority for 2026; data is sparse |

For country-specific sources, consult `docs/country_notes/`. Contribute findings back to that file as part of the batch.

## §5 Cluster coherence (Rule E from the carrier project, adapted)

When a single URL is used as the citation for multiple `[ref]` cells across a project (or across multiple units within a project), the URL must be **cluster-coherent**: it must verifiably reference the project AND contain the specific values being cited.

A URL that mentions "Sabine Pass" and "23 MTPA" supports citing capacity for Sabine Pass. It does NOT support citing capacity for the adjacent Cameron LNG terminal, even if the article briefly mentions Cameron.

For multi-unit projects:
- A project-level URL (covering all units) is fine for project-level fields
- A unit-specific URL (covering only Train 3, say) is only valid for that unit's data
- The build script should track which URLs cite which units to catch over-attribution

This is operationally identical to Rule E from the carrier [ref]-fill SOP, and `url_verifier.py` enforces it via the expected-content check.

## §6 Confidence labeling

Per CLAUDE.md, the color scheme is:

- **Green** — High confidence: primary/regulatory source (sponsor IR, FERC, DOE, EU PCI portal, national regulator) OR two independent corroborating Tier 1 sources agreeing on the value
- **Yellow** — Entity-level confirmation but value implied, contested, or from a single non-primary source
- **Red** — Single weak source. **Prefer leaving the cell blank** and logging in `qa_review` rather than staging red. Per the carrier project convention, red is a signal that work is needed, not that the work is done.
- **Blue** — Value unchanged from existing DB value but re-verified this batch. The "no changes" outcome at cell granularity.

Confidence applies per cell, not per row. A row might have a green Status update, a yellow Capacity revision, and blue confirmations on Owner and Location.

### §6.1 GIIGNL and IGU as sources

GIIGNL and IGU are Tier 1 but not authoritative. Per the methodology FAQ: "if we find a more specific or current source on a terminal that conflicts with the report, that source/data should take priority." A value supported by GIIGNL alone is yellow; supported by GIIGNL + a sponsor IR confirmation is green.

### §6.2 The blue convention specifically

Blue is more important for terminals than for carriers. The methodology has a "no changes" outcome in the Record of Full Updates field, and many terminal updates are confirmations rather than changes. Using blue to mark "checked, no change" makes the staging xlsx review faster: the reviewer can scan for non-blue cells (where actual work happened) rather than reading every row.

A cell is colored blue when:
- The agent searched for current information
- The current sources confirm the existing DB value
- The `[ref]` is already populated (or got populated in this batch)
- The unit's `LastUpdated` will be bumped to the batch date

If the agent searched but did NOT find a confirming source, the cell stays uncolored — that's a research gap, not a confirmation.

## §7 URL verification gate (mandatory)

Every URL staged in the xlsx must pass `url_verifier.py` before the batch is presented. No exceptions, even for URLs that worked in prior batches — URLs decay, paywalls change, soft-errors happen.

```bash
python url_verifier.py <url> <expected_string_1> <expected_string_2> ...
```

The verifier checks:
1. HTTP 200 (not 4xx/5xx)
2. Not a soft-error page (title doesn't contain "404", "429", "Just a moment" (Cloudflare), etc.)
3. Body contains every `expected_string` (case-insensitive)

`expected_string` arguments should include the **terminal name**, the **value being cited**, and ideally the **owner or country** for cluster coherence per §5. Examples:
- For a capacity citation: `<url> "Sabine Pass" "23 MTPA"`
- For a status update: `<url> "Cameron LNG" "construction" "Train 4"`
- For an ownership change: `<url> "Plaquemines" "Venture Global" "Excelerate"`

Verification failures result in the URL being dropped from the citation. If the cell would be left blank as a result, the build script flags it in `qa_review` for human attention.

### §7.1 Specific source patterns and soft errors

Common soft-error patterns the verifier catches:
- **Paywalled sources** (Reuters, S&P Global, Wall Street Journal): often return 200 with a stub body that says "Subscribe to read more" — the verifier catches this if the `expected_string` includes the value (which won't be in the stub)
- **Cloudflare interstitials** (Riviera Maritime, sometimes LNG Prime): "Just a moment..." page with 200 status — caught by title check
- **GIIGNL members-only links**: redirect to login with 200 — caught by absence of expected content
- **Government archive pages** (regulator FOI archives, EU PCI portal): URL structure changes between portal redesigns; older URLs may 404 silently or redirect to a search page

When the verifier flags a paywall stub for a Tier 1 source like Reuters, the workaround is to find an alternative source (often Reuters' free wire copy on a syndicated site) rather than to cite the paywall.

### §7.2 Pre-existing URL re-verification

Before staging any update that touches a row with existing `[ref]` URLs in unchanged cells, **re-verify the existing URLs** (whether or not the batch is editing them). This is the equivalent of the carrier project's §3.8a 404 sweep. Rationale: a row that's getting a blue "re-verified" treatment on some cells should have its other citations confirmed too, since the reviewer will assume the row was checked in its entirety.

Existing URLs that fail re-verification go in `qa_review` with proposed action: either find a replacement URL or blank the `[ref]` cell (and the paired data if Rule F requires it).

## §8 Entity discipline

Per the methodology, GEM's entity system is shared across all trackers. Creating a duplicate entity is real cleanup work for the Ownership Team. Before staging any new Owner, Parent, Operator, VesselOwner, VesselParent, or VesselOperator:

1. `python entity_lookup.py "<entity name>" "<country>"` — searches the existing entity DB
2. If a match is found, use its existing entity ID (the schema's `Parent GEM Entity ID` column)
3. If no match is found, add to `entity_additions` sheet with the lookup attempts logged
4. The user reviews `entity_additions` before applying the batch; they create the new entity via the GEM UI and link it

For entity *name* variants (e.g. "TotalEnergies" vs "Total Energies" vs "Total"):
- `docs/reference/entity_canonical_map.md` maps known variants to canonical names
- New variants encountered in a batch get added to that file
- The build script uses the canonical name when staging, with the original-as-found preserved in a `qa_review` log entry

## §9 Project-level vs unit-level edits

Per `docs/reference/gem_db_schema.md`, fields fall into three classes: project-level (apply to all unit-rows), unit-level (apply only to the target unit-row), and mixed/context-dependent (decide per case).

The build script enforces:
- **Project-level field edits** are applied to every unit-row of the project automatically. The staging xlsx shows the edit on one representative row in `updates` with a note "project-level: applies to N unit-rows".
- **Unit-level field edits** are applied only to the targeted UnitID.
- **Mixed-class field edits** trigger a read-before-write: the script checks current consistency across unit-rows.
  - If currently consistent → apply to all unit-rows
  - If currently inconsistent → apply only to the targeted unit-row and flag in `qa_review` for human review

For Owner specifically (one of the most common mixed-class fields), the inconsistency check should distinguish JV-structure cases (where different units genuinely have different owners, e.g. a project where Phase 2 added a new equity partner) from data-entry cases (where one unit's Owner is stale or wrong). Use the timeline + datasource dates to triage.

## §10 Out-of-scope fields (read-only)

Per the methodology and `docs/reference/gem_db_schema.md`, these fields are **never written** by the build script:

**Computed / rollup columns** (DB regenerates from underlying data):
- `CapacityinMtpa`, `CapacityinBcm/y`
- `TotImportLNGTerminalCapacityinMtpa`, `TotImportLNGTerminalCapacityinBcm/y`
- `TotExportLNGTerminalCapacityinMtpa`, `TotExportLNGTerminalCapacityinBcm/y`
- `CostUSD`, `CostEuro`
- `TotKnownTerminalCostsUSD`, `TotTerminalCost [ref]`
- `TerminalID`, `UnitID`, `Wiki`

**Out-of-scope per methodology** (no longer updated as of 2026):
- `PCINotes`, `PCI3`, `PCI4`, `PCI5`, `PCI6`
- `LH2`, `NH3`, `SyntheticLNG`, `RetrofitProposed`
- `AltFuelPrelimAgreement`, `AltFuelCallMarketInterest`

If a batch would otherwise want to write one of these (e.g. a source confirms a planned LH2 retrofit), record the finding in `qa_review` with a note that the field is out-of-scope — don't stage the edit.

## §11 Workflow (linear)

Putting it together, a standard update batch looks like:

1. **Confirm parameters** (§2)
2. **Materialize scripts** per CLAUDE.md
3. `python pull_gem_db.py` → fresh CSV, column-index map. **Mandatory every batch.**
4. `python dedup_index.py` → project + unit indexes
5. `python stale_sweep.py` if the batch includes stale-driven work
6. **For each unit in scope:**
   a. Pull existing timeline with `fetch_timeline.py` if any status changes anticipated
   b. Source-search per §4 using `docs/reference/source_roster.md` and `docs/country_notes/`
   c. Apply lifecycle rules from `docs/reference/lifecycle_rules.md`
   d. Identify [ref]-fill targets per §3.1
   e. Identify value updates per §3.3
   f. Resolve any cluster-coherence questions per §5
7. `python url_verifier.py` on every staged URL (§7)
8. `python url_verifier.py` re-check on pre-existing URLs in touched rows (§7.2)
9. `python entity_lookup.py` for every new entity reference (§8)
10. `python capacity_normalize.py` for any capacity edits with unit conversion
11. **If batch touches any FSRU terminal:** `python fsru_sync_check.py` (CLAUDE.md FSRU sync rule)
12. `python build_review_package.py --mode update --output ../batches/lng_terminals_batch_<YYYYMMDD>_<HHMM>_ET.xlsx` → staging xlsx (Eastern timestamp via `TZ=America/New_York date "+%Y%m%d_%H%M_ET"`)
13. `python recalc.py` → confirm zero formula errors
14. `present_files`

## §12 Hard rules (these override anything below)

- **Never modify the live GEM database.** Outputs are always staging xlsx for human review.
- **Every URL passes the §7 verification gate** — no exceptions.
- **Pull a fresh GEM CSV at the start of every batch** (§11.3).
- **Re-derive the column-index map** from the fresh header row.
- **No orphan `[ref]` cells** — never fill a `[ref]` without a paired data value (Rule F from the carrier project, methodology FAQ).
- **Status timeline edits require pulling the existing timeline first** via `fetch_timeline.py` (§3.2).
- **Don't create duplicate entities** — run `entity_lookup.py` before staging any new owner/operator/parent (§8).
- **Out-of-scope fields are read-only** (§10).
- **Project-level field changes apply to ALL unit-rows of a multi-unit project** (§9).
- **Cluster coherence on every URL** — a URL must verifiably reference the project AND contain the value being cited (§5).
- **Never auto-apply values from GIIGNL or IGU** — they're Tier 1 sources but not authoritative (§6.1). Methodology FAQ is explicit.
- **FSRU edits trigger sync check** (§11.11).

## §13 Pause-and-ask triggers

Stop and consult the user when:

- A whole class of GEM values looks systematically wrong (suggests methodology misunderstanding or schema drift, not a research finding)
- Source corroboration is too thin to support even yellow for a key field, even after Tier 1 + Tier 2 sources searched
- A status change is proposed but the existing timeline shows the same transition was already entered (possible duplicate, possible legitimate restart)
- A capacity update would change the project total by more than 20% (possible debottlenecking — but also possible source error)
- An ownership update would change the controlling parent (possible acquisition — verify with regulatory filings before staging)
- The FSRU sync check surfaces a reassignment that doesn't have a matching event on the carrier side
- A unit's existing URLs all fail re-verification and no replacement sources are found (suggests the project may no longer be active)
- An `entity_lookup` returns no match for an entity name that obviously should exist (suggests a search issue or a genuine gap requiring user judgment)

---

## Quick-reference card

| Sub-type | Primary action | Required scripts |
|---|---|---|
| [ref]-fill | Fill blank refs paired with data | `url_verifier.py`, `build_review_package.py` |
| Status / timeline | Add timeline entry, change Status | `fetch_timeline.py`, `status_timeline.py`, `build_review_package.py` |
| Value update | Add/change data values | `url_verifier.py`, `entity_lookup.py`, `capacity_normalize.py` (if applicable), `build_review_package.py` |
| Stale sweep | Process inferred shelved/cancelled | `stale_sweep.py`, `fetch_timeline.py`, `build_review_package.py` |

| Color | Meaning | When to use |
|---|---|---|
| Green | Primary source or 2+ corroborating Tier 1 | Default for sponsor IR, regulator filings |
| Yellow | Single non-primary, or value implied | GIIGNL alone, single trade press article |
| Red | Single weak source | Prefer blank; log in qa_review |
| Blue | Re-verified, unchanged | The "no changes" outcome at cell level |
| (none) | Searched but no confirming source found | Research gap, not confirmation |
