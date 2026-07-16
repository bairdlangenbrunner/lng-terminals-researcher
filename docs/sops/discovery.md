# LNG Terminals Discovery SOP

Last revised: 2026-07-09 (rev 3 — added the "power-plant ≠ terminal / supplier terminal may already exist" scope-gate sub-rule §3, from the Quang Trach II ← Vung Ang correction; rev 2 2026-06-24 added domestic-only scope gate §3, upstream-oil-operator/associated-gas FLNG sweep §4.3, gem.wiki coverage cross-check §4.0b, from the africa-discovery follow-up corrections)

Operational rules for finding LNG terminals (both import and export, all scales except bunkering) that are NOT yet in the GEM database. Discovery feeds candidate terminals into a staging xlsx for human review and addition to the live DB.

The methodology doc (LNG Terminals Manual) is authoritative for what counts as a terminal, the "sufficient information to add" threshold, and how new units are named. This SOP is operational — describes how to execute the discovery work, citing the methodology rather than restating it.

## §1 When to run this SOP

Trigger conditions:
- Triage SOP has scoped a country/region for discovery work this batch
- A reconciliation batch produced `to_follow_up_on` findings routed to Discovery (GIIGNL-only candidates)
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

**Scope gate — apply BEFORE the threshold.** First ask "is this even an LNG *terminal* in GEM's sense?", then ask "is there enough to add it?". A candidate is in scope only if it moves LNG across a border by ship — i.e. an **import** terminal (marine LNG in) or an **export**/liquefaction terminal (marine LNG out). A facility whose only function is **domestic gas distribution** — a small-scale liquefaction skid feeding cryogenic ROAD TANKERS to inland regas points, a "virtual pipeline", a trucking/peak-shaving plant with no marine LNG import or export — is **out of scope**, no matter how concrete its sponsor/location/step. `FacilityType = import`/`export` REQUIRES cross-border marine LNG movement; do not assign `export` to a plant that only liquefies gas for domestic trucking. **Resolve scope doubt BEFORE staging — never stage-with-doubt.** If you find yourself writing a researcher note like "reviewer may prefer a small-scale/peak-shaving classification," that is the signal to resolve the scope question first, not to stage the row and defer it. (Canonical miss: the **Dar es Salaam Small-Scale LNG Terminal** — a Rosetta Energy virtual-pipeline skid trucking LNG inland — was wrongly staged as `export` in the June-2026 africa sweep; it moves no LNG by ship across a border and is out of scope.)

**Power-plant ≠ terminal (and its supplier terminal may already exist).** An LNG-to-power *project* is not an LNG terminal. When a gas-power project description lists an "LNG storage + receiving port" component (Vietnamese `kho, cảng LNG`; similar bundled line items elsewhere), do NOT reflexively stage that component as a new import terminal. Ask **where the marine LNG import physically happens**: if the plant is fed by *regasified gas delivered by pipeline* from another terminal, then the marine-import scope gate FAILS at the plant's site — the power station belongs in GOGPT, and the import point is the *supplying* terminal, which is frequently **already in GEM** (so the correct action is `PowerPlantsSupplied` on the existing terminal, not a new record). A bundled `kho, cảng LNG` figure with tank/berth specs that never verify is a red flag that the "terminal" is downstream regas, not an independent marine import. Only stage a new terminal when the site genuinely receives LNG *by ship* itself. **The research isn't wasted** — the power-plant supply relationship (which plants, MW, first-gas date) is useful `wiki` Background *on the supplier terminal*, so stage a wiki entry there alongside the `PowerPlantsSupplied` fill rather than discarding the candidate's sourcing. (Canonical miss: **Quang Trach II**, Vietnam July-2026 discovery — staged as its own `import` terminal (EVN, Hon La EZ) when the LNG is in fact piped as regas from the existing **Vung Ang LNG Terminal**, T100000131060; it is a power plant, not a terminal. Compounding the error, the batch *flagged the supply-chain tension in a qa note and staged the candidate anyway* — the stage-with-doubt violation below.)

Per the methodology FAQ, a candidate that passes the scope gate qualifies for addition to GEM when all three are present:

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
- **Domestic-only small-scale / virtual-pipeline plant** (liquefaction-for-trucking, peak-shaving, no marine LNG in or out) — **fails the scope gate above** (not the threshold). Do NOT stage, not even with a hedged note. Drop it, or record a `scope_correction` qa note if it was wrongly staged in a prior batch.
- **LNG-to-power project fed by pipeline regas from another terminal** — the power plant is GOGPT, not a terminal; its marine import point is the *supplying* terminal (often already in GEM). Fails the scope gate at the plant's site. Add `PowerPlantsSupplied` to the existing terminal instead of staging a new record. See the "Power-plant ≠ terminal" rule in §3 (canonical miss: Quang Trach II ← Vung Ang, Vietnam July-2026).

## §4 The four-ring discovery model

Borrowed from the carrier project's discovery structure, adapted for terminals. The rings are searched in order; later rings catch what earlier rings miss.

### §4.0 Country coverage — sweep the gaps, not just the covered

Before the rings, settle **which countries** to search. Every dedup/index tool keys off countries already in the GEM export, so a country with ZERO GEM LNG terminals is invisible to them — a first-time importer signing an FSRU charter would never surface. Run `python completeness_sweep.py` and read its `coverage_gap` block: `uncovered_coastal` lists coastal countries (the marine-access universe in `scripts/country_universe.py`) that have **no** GEM LNG terminal. Add the in-scope uncovered countries to the search so discovery covers **covered ∪ uncovered**, not only countries already tracked.

The list is deliberately broad (it includes micro/island states that will realistically never build LNG) — triage it, don't treat every entry as a lead. For a global or regional run the uncovered set IS part of scope; for a single-country run it's a no-op. If `coverage_gap.gem_countries_outside_reference` is non-empty, a GEM-covered country is missing from the reference list — add it to `country_universe.py` (or fix a name) so it never reads as a false gap. This precedes the rings below, which then research each in-scope country (covered or newly added).

### §4.0a Dormant-revival watch — recheck dead sites, not just the gaps

The coverage gap finds countries with *zero* GEM terminals; this finds the other blind spot — **dead sites inside covered countries**. A terminal that GEM holds as wholly `cancelled`/`shelved` is a dead SITE, and the routine workflow never circles back to ask "did something new rise here?" (the Update `dev_pipeline` re-verifies shelved records but never cancelled ones, and it refreshes the *existing* record — it does not look for a *new, distinct* project at the site). So a fresh proposal at a long-dead site — different sponsor, different design — sails past discovery unless you deliberately look.

Read `completeness_sweep.py`'s `dormant_revival_watch` block (run the script in §10.3; pass `--country`/region scope to match the batch). For each in-scope dead site, **web-search the site for new activity** — a new sponsor, a new FSRU/FSU charter, a new permit or state approval, a renamed project. `revival_priority: "high"` (dead 5+ years) is where a new proposal is most likely a genuinely *new* project rather than a true revival of the dead record (§12, fourth bullet).

Routing the result:
- **New activity, same fundamentals** (same sponsor, same design) → revival of the dead record → Update workflow (timeline entry), not a new terminal (§6 dead-and-revived).
- **New activity, significantly different** (different sponsor and/or design) → a NEW terminal per the dead-and-revived rule in `docs/reference/lifecycle_rules.md`; stage it in `new_terminals` with `AssociatedTerminals` → the dead record (which stays cancelled). This is precisely the case `dedup_index.py` mis-routes to `update_dead_and_revived` — the matcher cannot see the sponsor/design change, so override it by hand (§6.6).
- **No new activity** → leave the dead record as-is; no output.

This is the safeguard for the canonical miss: **POIC Lahad Datu** — a 2026 FSU-based import terminal (Green Oscasaba / LNG Alliance) at the site of the 2016-cancelled "Lahad Datu Sabah LNG Terminal" (Petronas/Sabah Energy) — which a trade-press-only Sabah sweep missed. The dead site sits at the top of this watch list (cancelled, 10 years dead, `high`), so the next sweep is forced to search it. The list is global and broad on a full run (hundreds of entries) — triage by priority and in-scope geography, the same way the coverage gap is triaged.

### §4.0b gem.wiki coverage cross-check — find terminals that have a wiki page but no tracker row

A third structural blind spot, distinct from the coverage gap (§4.0, *countries* with zero rows) and the dormant-revival watch (§4.0a, dead *sites*): a terminal that already has a **gem.wiki page** but is **absent from the GEM export CSV**. The web-only discovery method cannot see it from either side — the CSV-dedup step (§6) has no row to match against, and the web-search rings never surface it because gem.wiki is (correctly) excluded as a source, so GEM's own page for the project never enters the candidate pool. The result: an internally-known project that the export-driven workflow treats as if it doesn't exist.

For each in-scope country, **enumerate the gem.wiki LNG-terminal pages** (e.g. the LNG Terminals category / country listing on gem.wiki, or a site search) and reconcile that list against the export CSV. Any gem.wiki page with **no corresponding export row** is a candidate: research it from independent (non-gem.wiki) sources, dedup, threshold-test, and stage like any other discovery lead. **gem.wiki is used here ONLY to detect the coverage gap — it is reconciled to a tracker row, never cited as a source or `[ref]`** (anti-circularity rule, CLAUDE.md). The independent corroboration for the staged row must come from outside the GEM ecosystem.

Canonical miss: the **Durban LNG Terminal** (Port of Durban; Vitol / ACWA Power / Engen) had a `gem.wiki/Durban_LNG_Terminal` page but no export row, so the June-2026 africa sweep — driven by export-dedup + web search — never saw it.

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
- **Upstream OIL operators in coastal hydrocarbon producers** (the FLNG sponsors the "established LNG developer" list misses): the independents and NOCs that operate offshore/onshore OIL fields and monetize their *associated gas* via FLNG/onshore liquefaction. In Africa/Latin America/SE Asia this is where new export capacity actually originates — e.g. **Trident Energy** (Congo, Equatorial Guinea), **Perenco**, **Eni** (field-tied FLNG), **Wing Wah/SNPC** (Congo), **Panoro**, **VAALCO**, **BW Energy**, **Kosmos**, **Savannah Energy**, plus the relevant NOC (SNPC, GEPetrol, NNPC, etc.). For every coastal hydrocarbon-producing country in scope, run an explicit **associated-gas / gas-monetization / flaring-reduction** sweep over the country's upstream operators — a national Gas Code, Gas Master Plan, or flaring-reduction commitment is the tell that field operators are about to propose FLNG. **Do not limit Ring C to companies already known as LNG developers.**

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

The `monitor_list` rolls forward across batches via the durable store `monitor_list/current.json` and `scripts/monitor_store.py` (the two halves of the loop):

1. **Before the discovery build:** `python scripts/monitor_store.py seed <inputs-dir>` copies the durable store into `<inputs-dir>/prior_monitor_list.json`, which `build_review_package.py` merges with this batch's candidates into the `monitor_list` sheet (so the reviewer sees the accumulated watch-list, with `first_observed_batch` preserved and `last_observed_batch` bumped).
2. **After the discovery build:** `python scripts/monitor_store.py update <inputs-dir> --batch <stamp>` folds this batch's `staged_monitor_list.json` back into the durable store **and drops any candidate promoted to `new_terminals` this batch** (matched on normalized country + name). That is what keeps a vague-rumor project from being re-discovered every batch and retires it once it firms up.

Without `monitor_store.py`, the build only ever sees an empty prior list and the durable store never accumulates — the roll-forward is inert.

## §6 Dedup against existing GEM

Before staging a candidate as new, verify it's not already in GEM under a different name. `dedup_index.py` builds two indexes for this purpose:

- **Project index**: `(country_normalized, terminal_name_normalized)` → TerminalIDs
- **Sponsor-country index**: `(country_normalized, sponsor_normalized)` → list of TerminalIDs

Steps 1-6 below are implemented by `python dedup_index.py match <candidates.json>` (library: `match_candidate`) so the comparison is deterministic rather than eyeballed. Write the batch's leads to a JSON list (`country`, `name`, `sponsor`, optional `latitude`/`longitude`, `capacity_mtpa`, `status`) and run it; each candidate comes back with a `verdict` and a `recommended_route` — act on the route:

1. Normalize the candidate's country, name, and sponsor per `normalize.py` (the matcher does this)
2. Check project index for exact match → likely duplicate
3. Check sponsor-country index → list of all GEM terminals from this sponsor in this country
4. For each same-country match, compare (the matcher scores all three):
   - Location (haversine km if both have lat/lng; ≤1.5 km ≈ same physical site, ≤10 km same port/complex)
   - Capacity (ratio if both have a value; within ~15% corroborates)
   - Lifecycle status (cancelled/shelved GEM record + new proposal = possible dead-and-revived — flagged even when the name doesn't match, since revived projects are routinely renamed)
5. Route by verdict:
   - `update_existing` / `update_dead_and_revived` (high similarity) → route to the Update workflow (per `docs/reference/lifecycle_rules.md` dead-and-revived rules); do **not** stage as new
   - `manual_review` (ambiguous — e.g. same site, different sponsor) → the §12 pause-and-ask case; judge by hand
   - `discovery_new` (low similarity) → genuinely new candidate, proceed to the threshold test (§3)
6. The matcher is a gate, not an oracle — a `discovery_new` verdict on a candidate you have other reason to suspect is a duplicate still warrants a manual look (it only sees what's in the export).

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

1. **Confirm parameters** (§2). Write `meta.json` in the batch's staging dir now — every staging dir carries one (`batches/staging/README.md`).
2. **Materialize scripts** per CLAUDE.md
3. `python pull_gem_db.py` → fresh CSV, column-index map. **Mandatory every batch.**
4. `python completeness_sweep.py [--country "<C>"]` → read its `coverage_gap` (§4.0, which countries to add to scope) AND its `dormant_revival_watch` (§4.0a, which dead sites to revival-check) blocks before searching
   - **gem.wiki coverage cross-check (§4.0b):** for each in-scope country, enumerate gem.wiki LNG-terminal pages and reconcile against the export CSV; any wiki page with no export row is a candidate (research from independent sources only — gem.wiki is the gap-detector, never a citation)
5. `python dedup_index.py` → project + sponsor-country indexes (§6); score leads with `python dedup_index.py match <candidates.json>` once gathered
6. **For each ring (A → B → C → D) within the scope, PLUS the §4.0a dormant sites:**
   a. Execute the ring's search strategy (§4); also web-search each in-scope `dormant_revival_watch` site for new activity (§4.0a)
   b. For each lead, check dedup (§6) — skip if duplicate, route to Update if a true revival, stage as NEW (with `AssociatedTerminals`) if a different project at a dead site (§4.0a)
   c. Apply threshold test (§3) — pass → `new_terminals`/`new_units`, fail → `monitor_list`
   d. For passing candidates, build the row (§7)
7. `python url_verifier.py` on every staged URL (§8)
8. `python entity_lookup.py` for every new entity reference (§9) — **run it bare (no `--country`) and with `--remote`**
9. `python capacity_normalize.py` for any candidate with capacity in non-standard units
10. **If batch includes any FSRU candidates:** `python fsru_sync_check.py` against carrier project backend (CLAUDE.md FSRU sync rule)
11. **Contribute country findings** to `country_notes_contributions` sheet — new regulator URLs, search patterns that worked, country-specific gotchas
12. **Seed the monitor roll-forward** (§5): `python monitor_store.py seed ../batches/staging/<scope-slug>` → writes `prior_monitor_list.json` into the inputs-dir so the build merges the durable watch-list with this batch's candidates
13. `python build_review_package.py --mode discovery --inputs-dir ../batches/staging/<scope-slug> --output ../batches/lng_terminals_batch_<YYYYMMDD>_<HHMM>_ET_<scope>_discovery.xlsx` → staging xlsx (Eastern timestamp via `TZ=America/New_York date "+%Y%m%d_%H%M_ET"`; scope slug + mode per `docs/reference/workbook_conventions.md`; staged inputs live in `../batches/staging/<scope-slug>/`)
14. `python recalc.py` → confirm zero formula errors
15. **Update the durable monitor store** (§5): `python monitor_store.py update ../batches/staging/<scope-slug> --batch <YYYYMMDD>_<HHMM>_ET` → folds this batch's monitor candidates into `monitor_list/current.json` and drops any promoted to `new_terminals`
16. `present_files`

## §11 Hard rules

- **Scope gate before the threshold** — every `new_terminals` row must move LNG across a border by ship (import = marine LNG in; export = marine LNG out). Domestic-only virtual-pipeline / trucking / peak-shaving plants are OUT OF SCOPE (§3). Resolve scope doubt before staging — never stage-with-doubt.
- **Power-plant ≠ terminal** — an LNG-to-power project fed by pipeline regas from another terminal is GOGPT, not a new terminal; check whether the *supplying* terminal already exists in GEM and add `PowerPlantsSupplied` there instead of staging a new record (§3; Quang Trach II ← Vung Ang miss).
- **Threshold test before staging** — every `new_terminals` row must pass §3
- **Sweep upstream OIL operators, not just LNG developers** — in coastal hydrocarbon producers, run an associated-gas / gas-monetization / flaring-reduction sweep over field operators (§4.3); they are the real FLNG sponsors and the "established LNG developer" list misses them
- **gem.wiki coverage cross-check** — reconcile gem.wiki LNG-terminal pages against the export CSV per §4.0b; a wiki page with no export row is a discovery candidate (gem.wiki detects the gap, is NEVER the citation)
- **Dedup before staging** — every candidate gets checked against existing GEM per §6
- **Revival-check every in-scope dead site** — read `completeness_sweep.py`'s `dormant_revival_watch` and search each wholly cancelled/shelved in-scope site for new activity (§4.0a); a different new project at a dead site is a NEW terminal, not a record edit
- **Every URL passes the verification gate** (§8)
- **Pull a fresh GEM CSV at the start of every batch** (§10.3)
- **Don't create duplicate entities** — `entity_lookup.py` per §9, run **bare (no `--country`) and with `--remote`**; `--country` only annotates, it never hides a match (an entity on a terminal in another country is still a match)
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
