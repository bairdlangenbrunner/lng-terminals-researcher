# LNG Terminals Discovery SOP

Last revised: 2026-05 (rev 1, initial draft)

Operational rules for finding LNG terminals (both import and export, all scales except bunkering) that are NOT yet in the GEM database. Discovery feeds candidate terminals into a staging xlsx for human review and addition to the live DB.

The methodology doc (LNG Terminals Manual) is authoritative for what counts as a terminal, the "sufficient information to add" threshold, and how new units are named. This SOP is operational — describes how to execute the discovery work, citing the methodology rather than restating it.

## §1 When to run this SOP

Trigger conditions:
- Triage SOP has scoped a country/region for discovery work this batch
- A reconciliation batch produced `giignl_to_action` findings routed to Discovery (GIIGNL-only candidates)
- The user explicitly requests a discovery run for a country, region, or sponsor
- A specific news event suggests new project activity in a region not covered by an upcoming Update batch (a major sponsor's quarterly announcement, a country opening a new round of bids)
- A "catch-up sweep" after a long period without coverage of a particular region

## §2 Confirm parameters at batch start

Discovery is more sensitive to scope choices than Update, because the "what's in scope?" question genuinely affects what candidates surface. Confirm before any tool runs:

1. **Geographic scope** — country, region, or global. Global discovery is expensive; if the user requests global, push back unless triage justifies it.
2. **Project type scope** — import, export, or both. Defaults to both per the project-wide scope (excluding bunkering).
3. **Lifecycle stage threshold** — how early-stage to accept candidates. Options:
   - **Tight** (default): require the methodology's "sufficient information to add" — sponsor identified + approximate location + concrete step taken
   - **Permissive**: include early-rumor-stage candidates in a `monitor_list` sheet for future tracking
   - **Operating-only**: only accept candidates already commissioned (rare — usually combined with reconciliation backlog)
4. **Time window** — how far back to search. Defaults to "anything not in the current GEM export, regardless of age" but practically the highest yield is announcements from the last 12-24 months.
5. **FSRU handling** — if scope includes import discovery in countries with FSRU activity, sync rule applies (CLAUDE.md).
6. **Reconciliation-fed candidates** — if any GIIGNL-only findings from a prior reconciliation are pending, list them in scope at batch start. Discovery for these is partly pre-done (GIIGNL provided the initial lead); workflow focuses on verification and threshold testing.

These parameters get written into the staging xlsx README sheet.

## §3 The "sufficient information to add" threshold

Per the methodology FAQ, a candidate qualifies for addition to GEM when all three are present:

1. **Sponsor identified** — a specific company or entity (not "consortium being formed" or "TBD")
2. **Approximate location** — at minimum, a country + region/state/port (latitude/longitude can be approximate; methodology accepts `Accuracy = approximate`)
3. **Concrete step taken** — beyond pure verbal intent. Examples that count: MOU signed, site selected, FEED contract awarded, environmental permit applied for, public consultation initiated, regulatory pre-filing, land lease secured.

Candidates that fall short go in `monitor_list` (see §5) with a note on which threshold elements are missing. This is the equivalent of the Update SOP's "yellow → leave blank" discipline: not everything we find should result in an add.

**Edge cases:**
- **Vague sponsor** (e.g. "a Chinese consortium") — fails the sponsor test. Monitor list.
- **Multiple alternative sites under consideration** (e.g. "Site A or Site B in Vietnam") — usually fails the location test unless one is clearly the leading candidate per recent reporting.
- **Verbal intent only** (e.g. "X country's energy minister said the country will build an LNG import terminal by 2030") — fails the concrete step test. Monitor list.
- **Genuine pre-FID with sponsor, location, FEED contract** — passes. Add as `proposed`, FID status `Pre-FID` only if explicitly reported.
- **Project announced years ago but no apparent activity since** — passes the threshold but enters as `shelved` with substatus `inferred 2 y` or `confirmed`. The age of the most recent news drives the status, not the age of the project itself.

## §4 The four-ring discovery model

Borrowed from the carrier project's discovery structure, adapted for terminals. The rings are searched in order; later rings catch what earlier rings miss.

### §4.1 Ring A — country-level regulatory sweep

The most authoritative ring. National regulators publish concrete project information (filings, permits, environmental assessments) that establishes both existence and several key data fields at once.

For each country in scope, consult:

- **United States**: FERC eLibrary (`elibrary.ferc.gov`) for import/export terminals; DOE Office of Fossil Energy & Carbon Management export authorizations
- **European Union**: PCI list portal (`energy.ec.europa.eu`); per-country TSOs (e.g. GRTgaz for France, Snam for Italy)
- **United Kingdom**: Ofgem decisions; Planning Inspectorate (NSIP project list)
- **Canada**: CER (Canada Energy Regulator) for export licenses; provincial environmental assessment agencies (BC EAO, etc.)
- **Australia**: NOPSEMA for offshore; state EPA decisions; AEMO gas statement of opportunities
- **Japan**: METI announcements; JOGMEC strategic reserve plans
- **South Korea**: MOTIE; KOGAS IR
- **China**: NDRC press releases; CNPC, Sinopec, CNOOC quarterly disclosures; provincial development & reform commissions for inland regas
- **India**: MOPNG; PNGRB tariff orders (which require regulatory filings before operation)
- **Brazil**: ANP terminal authorizations; EPE planning documents
- **Mexico**: CRE permits; SENER strategic outlooks
- **Russia**: Limited public regulatory data post-sanctions; check IISS, FACTS Global Energy secondary coverage
- **Middle East / Gulf**: state oil company IR (Saudi Aramco, ADNOC Gas, QatarEnergy); ENOC for UAE
- **Africa**: country-by-country highly variable; check IEA Africa Energy Outlook, Reuters Africa, sponsor IR
- **Southeast Asia**: per-country, e.g. Philippines DOE, Vietnam MOIT, Indonesia ESDM

This list is not exhaustive. `docs/country_notes/` is the working memory for country-specific regulator URLs, filing patterns, and update cadences. Contribute findings back to that file.

### §4.2 Ring B — trade press sweep

For each country/region in scope, search trade press for new-project announcements in the time window:

- **Workhorses**: LNG Prime, Reuters Energy, S&P Global Commodity Insights, Argus Media, Upstream Online, Energy Intelligence
- **Regional specialists**: Splash247 (shipping angle), Riviera Maritime Media (technical), Hellenic Shipping News (Europe), Hydrocarbons Africa, Energy Voice (UK)
- **Tier 1b regulatory press**: en.sedaily.com (Korean DART proxies), iMarine (Asia)

Search patterns that work:
- `"LNG terminal" "<country>" "announced" "<year>"`
- `"<country>" "regasification" "MOU"`
- `"FSRU" "<country>" "deployment"`
- `"<sponsor name>" "LNG" "<country>"`
- `"<country>" "liquefaction" "FEED"`

Trade press often leads regulator filings by weeks-to-months for early-stage projects; regulators trail trade press but offer harder evidence.

### §4.3 Ring C — sponsor IR / corporate sweep

For sponsors known to be active in LNG, walk their IR materials directly. The methodology's "established LNG developer" list as a starting point:

- **US-focused exporters**: Cheniere, Venture Global, NextDecade, Sempra, Freeport LNG, Tellurian, Energy Transfer
- **Integrated majors**: TotalEnergies, Shell, BP, ExxonMobil, Chevron, ConocoPhillips, Eni
- **Asian state-linked**: QatarEnergy, ADNOC Gas, Petronas, Pertamina, CNPC, Sinopec, CNOOC, KOGAS, JERA
- **FSRU operators**: Excelerate Energy, Höegh Evi, BW LNG, Energos Infrastructure, Karpowership/KARMOL, New Fortress Energy
- **Import-side**: ENGIE, Naturgy, Snam, Fluxys, Enagas, RWE, Uniper, Sempra Infrastructure

For each sponsor in scope:
- IR press releases (last 12-24 months)
- Quarterly earnings calls (transcripts via Seeking Alpha, sponsor IR site)
- Annual reports / sustainability reports
- Investor day decks (these often disclose pipeline projects pre-PR)

Sponsor IR is often the earliest credible signal — sponsors disclose to investors before broad press release.

### §4.4 Ring D — broader scan (optional, when prior rings underyield)

When rings A-C don't surface enough candidates to justify the batch (or when scope is intentionally broad), expand to:

- **Industry conference materials** (LNG2026, Gastech, World Gas Conference) — presenter lists often include emerging projects
- **Lender / financier announcements** — JBIC, KEXIM, ECAs, multilateral development bank disclosures often pre-date sponsor PR
- **EPC contractor backlogs** — Bechtel, McDermott, KBR, JGC, Worley, Saipem, Technip, Wood, Fluor occasionally disclose project wins
- **Equipment supplier wins** — GTT (containment), Air Products (liquefaction), Chart Industries, Wärtsilä (FSRUs)
- **NGO / opposition research** — Reclaim Finance, IEEFA, Oil Change International often track LNG projects (including unconfirmed ones); use as a lead, NOT as a primary citation

Ring D candidates tend to need the most verification — early-stage signals from supplier/financier channels are real but often refer to pre-public projects that shouldn't yet be added.

## §5 Monitor list (candidates that don't meet threshold)

Candidates that fail any threshold element from §3 go in `monitor_list` sheet with:
- Sponsor (if known)
- Country/Region
- Source URL(s)
- Which threshold elements are missing
- Date first noticed
- Suggested re-check date (typically 6-12 months later)

Purpose: avoid re-discovering the same vague-rumor project in every batch, and create a re-check trigger when the project may have firmed up.

The `monitor_list` is intended to roll forward across batches — the build script should read the prior batch's monitor_list and merge with the current batch's additions, dropping items that have since moved to the real `new_terminals` sheet.

## §6 Dedup against existing GEM

Before staging a candidate as new, verify it's not already in GEM under a different name. `dedup_index.py` builds two indexes for this purpose:

- **Project index**: `(country_normalized, terminal_name_normalized)` → TerminalIDs
- **Sponsor-country index**: `(country_normalized, sponsor_normalized)` → list of TerminalIDs

For each candidate:
1. Normalize the candidate's country, name, and sponsor per `normalize.py`
2. Check project index for exact match → likely duplicate
3. Check sponsor-country index → list of all GEM terminals from this sponsor in this country
4. For each sponsor-country match, compare:
   - Location (if both have lat/lng, distance in km)
   - Capacity (if both have a value, ratio)
   - Lifecycle status (cancelled GEM unit + new sponsor announcement = possible dead-and-revived)
5. If similarity is high → likely duplicate, route to Update workflow (per docs/reference/lifecycle_rules.md dead-and-revived rules)
6. If similarity is low → genuinely new candidate

**Expansion vs new project** is a common ambiguity:
- A new train at an existing terminal → new **unit** within an existing terminal (use `new_units` sheet, not `new_terminals`)
- A new terminal at the same site as an existing one (e.g. import terminal added next to existing export terminal) → genuinely new terminal, but with `AssociatedTerminals` link to the existing one
- A new phase of the same terminal proposal (e.g. NextDecade Phase 2) → new units, not new terminal

The methodology FAQ has examples; consult when ambiguous.

## §7 Building a candidate row

For each verified candidate that meets the threshold, build a row with as many fields populated as the sources support. **Minimum required fields** to stage in `new_terminals`:

- `TerminalName` (per methodology naming conventions: usually `<Site> LNG Terminal` or `<Site> FSRU`)
- `Country/Area`
- `FacilityType` (`import` or `export`)
- `Status` (typically `proposed` for newly-discovered)
- `Substatus` (blank for `proposed`)
- `Owner` (at least one entity — entity lookup mandatory per Update SOP §8)
- `Location` (at minimum a free-text location string; lat/lng if available with appropriate `Accuracy`)
- `Source [ref]` or `Status [ref]` (at least one cited URL covering the threshold elements)

Other fields populated when sources support:
- `Capacity` + `CapacityUnits` (usually MTPA for LNG)
- `ProposalYear` (year of the public announcement that establishes the project)
- `Operator` (often same as Owner for newly proposed)
- `Parent` (if Owner is a subsidiary)
- `Offshore` / `Floating` booleans + `FloatingVesselName` if FSRU
- `OriginalPlannedStartYear` (if sponsor has stated a target)
- `FIDStatus = Pre-FID` only if explicitly stated; otherwise leave blank
- `Pipelines`, `PowerPlantsSupplied`, `Source` (gas field) — populate when known, fine to leave blank

For multi-unit projects discovered at once (e.g. a 3-train liquefaction proposal), build one row in `new_terminals` plus N rows in `new_units` (one per train). Methodology naming: trains get `UnitName` = `T1`, `T2`, `T3` typically; phases get `Phase 1`, `Phase 2`.

## §8 URL verification gate (mandatory)

Every URL goes through `url_verifier.py` per Update SOP §7. Discovery has the additional risk of citing sources that mention the project name but don't actually establish it (e.g. a sponsor's investor day deck mentions "expansion opportunities including a potential terminal in X" — passes a naive name-match, fails the threshold).

For discovery citations specifically, the `expected_string` arguments should verify:
- The terminal name OR site name OR sponsor name
- A specific concrete step from the threshold (e.g. "FEED", "MOU signed", "permit filed", "FID")
- The country

Example: `python url_verifier.py <url> "Plaquemines" "Phase 2" "FERC"`

The verifier dropping a URL for missing the threshold-step keyword is a signal that the URL doesn't actually support the candidate — re-evaluate whether the candidate meets the threshold or whether a different URL needs to be found.

## §9 Entity discipline

Per Update SOP §8, every new Owner / Operator / Parent / VesselOwner / VesselOperator goes through `entity_lookup.py` before being staged. Discovery tends to surface more new entities than Update (new projects often involve new SPVs and JV structures), so expect `entity_additions` sheet to be more active.

For SPV-style entities (special-purpose vehicles set up for a single project, often a project name + "LLC" or similar):
- Create the SPV as the immediate Owner
- Set Parent to the sponsoring company/companies
- Note in the entity addition that this is an SPV (helps the Ownership Team distinguish from real operating entities)

For JV-style entities (e.g. "TotalEnergies-Petronas JV"):
- Methodology preference is to list each JV partner as a separate Owner with their percentage, NOT to create a JV entity
- Exception: if the JV operates as a real legal entity with its own staff and publications (e.g. NLNG Limited as a JV of NNPC, Shell, Total, ENI), treat as a single entity

## §10 Workflow (linear)

1. **Confirm parameters** (§2)
2. **Materialize scripts** per CLAUDE.md
3. `python pull_gem_db.py` → fresh CSV, column-index map. **Mandatory every batch.**
4. `python dedup_index.py` → project + sponsor-country indexes (§6)
5. **For each ring (A → B → C → D) within the scope:**
   a. Execute the ring's search strategy (§4)
   b. For each lead, check dedup (§6) — skip if duplicate, route to Update if dead-and-revived
   c. Apply threshold test (§3) — pass → `new_terminals`/`new_units`, fail → `monitor_list`
   d. For passing candidates, build the row (§7)
6. `python url_verifier.py` on every staged URL (§8)
7. `python entity_lookup.py` for every new entity reference (§9)
8. `python capacity_normalize.py` for any candidate with capacity in non-standard units
9. **If batch includes any FSRU candidates:** `python fsru_sync_check.py` against carrier project backend (CLAUDE.md FSRU sync rule)
10. Merge the `monitor_list` with the prior batch's monitor_list (§5)
11. **Contribute country findings** to `country_notes_contributions` sheet — new regulator URLs, search patterns that worked, country-specific gotchas
12. `python build_review_package.py --mode discovery --batch-id <YYYYMMDD>` → staging xlsx
13. `python recalc.py` → confirm zero formula errors
14. `present_files`

## §11 Hard rules

- **Threshold test before staging** — every `new_terminals` row must pass §3
- **Dedup before staging** — every candidate gets checked against existing GEM per §6
- **Every URL passes the verification gate** (§8)
- **Pull a fresh GEM CSV at the start of every batch** (§10.3)
- **Don't create duplicate entities** — `entity_lookup.py` per §9
- **No orphan `[ref]` cells** (Rule F from carrier and Update SOP)
- **GIIGNL/IGU candidates require independent verification** — GIIGNL-only findings from reconciliation are leads, not authority. Source-search like any other candidate.
- **Out-of-scope fields stay blank** — never populate LH2/NH3/SyntheticLNG/PCI fields on a new candidate, even if sources mention them
- **FSRU candidates trigger sync check** — per §10.9
- **Multi-train projects → one terminal row + N unit rows**, not N terminals

## §12 Pause-and-ask triggers

Stop and consult the user when:

- More than ~5 candidate clusters surface in the same country (suggests systematic gap, not normal leading-edge lag — worth conversation about scoping a deeper sweep)
- A candidate has strong sponsor + concrete step but extremely vague location (e.g. "somewhere on the US Gulf Coast") — threshold is genuinely ambiguous
- Dedup surfaces a high-similarity match but with different sponsor (possible acquisition / project rename, possible distinct project)
- A dead-and-revived candidate has been cancelled in GEM for 5+ years (re-creating an old project under the same TerminalID may not be right — could be a new project at the same site)
- All Ring A-C sources are exhausted for a country and ring D is being relied on heavily (the candidates may be too speculative for the threshold)
- Discovery turns up candidates that would change GEM's coverage of a country by more than 30% (probably a methodology/coverage discussion needed before bulk-staging)
- FSRU sync check finds a vessel that's "deployed at" a candidate terminal but doesn't exist in the carrier project backend either (suggests a coordinated discovery effort across both projects)

---

## Quick-reference card

| Ring | What | Use when |
|---|---|---|
| A | National regulators | Always — most authoritative leads |
| B | Trade press | Always — earliest credible signal for many projects |
| C | Sponsor IR | Always — captures pre-PR investor disclosures |
| D | Conferences, lenders, EPC, equipment, NGO | When A-C underyield or scope is permissive |

| Threshold element | Must include |
|---|---|
| Sponsor | Specific entity, not "consortium TBD" |
| Location | At minimum country + region/port |
| Concrete step | MOU, FEED, permit, site selection, etc. — not just verbal intent |

| Candidate type | Output sheet |
|---|---|
| Genuinely new project | `new_terminals` (+ `new_units` for multi-unit) |
| New train at existing terminal | `new_units` only |
| Dead-and-revived (same fundamentals) | Update workflow (timeline entry) |
| Below threshold | `monitor_list` |
| Already in GEM | Drop (or route to Update if data needs refresh) |
