# SOP Pointer Index

Quick lookup for "which SOP section governs X" without re-reading the whole SOP set. The SOPs themselves are authoritative; this file just indexes them.

**The GEM LNG Terminals Manual** (the methodology doc, authoritative over everything below):
<https://docs.google.com/document/d/18BvRBWLhXVgj92y5XOv98Co1QtMFj3ny20pmN9XbDko> — "Last updated: Baird and Rob, May 2026" as of this writing. Confirm it is in context before any batch (CLAUDE.md "Read the methodology + relevant SOPs first").

Last reconciled against:
- Reconciliation SOP rev 1 (2026-05)
- Update SOP rev 2 (2026-06 — standard/exhaustive tiers)
- Discovery SOP rev 2 (2026-06-24 — scope gate §3, gem.wiki coverage cross-check §4.0b, upstream-oil-operator FLNG sweep §4.3)
- Triage SOP rev 2 (2026-06 — QC signals, tier-named options)
- QC SOP rev 1 (2026-06)
- Ref-sweep SOP rev 1 (2026-06-30 — missing-year status-timeline backfill; read-only Postgres)
- CLAUDE.md (2026-06-09 — second slim pass; pull/FSRU/color detail deduplicated to `docs/workflows.md` + `docs/reference/workbook_conventions.md`; workflow recipes in `docs/workflows.md`, script table in `scripts/README.md`)

Abbreviations:
- **REC** = `docs/sops/reconciliation.md`
- **UPD** = `docs/sops/update.md`
- **DSC** = `docs/sops/discovery.md`
- **TRG** = `docs/sops/triage.md`
- **QCS** = `docs/sops/qc.md`
- **RSW** = `docs/sops/ref_sweep.md`
- **SKL** = `CLAUDE.md`
- **WFL** = `docs/workflows.md`
- **WBC** = `docs/reference/workbook_conventions.md`
- **SCH** = `docs/reference/gem_db_schema.md`
- **LFC** = `docs/reference/lifecycle_rules.md`
- **SRC** = `docs/reference/source_roster.md`
- **ENT** = `docs/reference/entity_canonical_map.md`
- **UNT** = `docs/reference/unit_conventions.md`
- **CNT** = `docs/country_notes/`

## Hard rules (cross-SOP)

| Rule | Primary location | One-line summary |
|---|---|---|
| Never modify live GEM database | SKL "Hard requirements", UPD §12, DSC §11 | All outputs are staging xlsx |
| Pull fresh GEM CSV every batch | SKL "Hard requirements", UPD §11.3, DSC §10.3 | Schema and data drift between batches |
| Re-derive column-index map every batch | SKL "Hard requirements", SCH "Schema drift detection" | 115-col schema is not stable |
| URL verification gate on every URL | SKL "Hard requirements", UPD §7, DSC §8, REC §3.9 | HTTP 200 + content check + soft-error detection |
| No orphan [ref] cells (Rule F) | UPD §3.1, §12 | Never fill a [ref] without paired data |
| Status timeline edits require timeline pull | SKL "Hard requirements", UPD §3.2, LFC "Anchor years vs timeline" | Export doesn't contain timeline; use fetch_timeline.py |
| No duplicate entities | UPD §8, DSC §9 | Run entity_lookup.py (bare + `--remote`) before staging new entity; `--country` annotates, never filters |
| Out-of-scope fields are read-only | UPD §10, SCH "Read-only column list" | LH2/NH3/SyntheticLNG/PCI/RetrofitProposed/AltFuel*, all computed totals |
| Project-level field edits apply to all unit-rows | UPD §9, SCH "Field classification" | Mixed-class fields trigger read-before-write |
| Cluster coherence on URLs (Rule E) | UPD §5 | URL must verifiably reference project AND contain value |
| GIIGNL/IGU never auto-applied | REC §3.8, UPD §6.1 | Tier 1 but not authoritative per methodology |
| FSRU edits trigger sync check | SKL "FSRU sync rule", WFL §7, UPD §11.11 | Cross-check against carrier project backend |
| QC stages no edits and builds no xlsx | QCS §5, §7 | Memo only; fixes route to a follow-on Update ("QC detects, Update fixes") |
| Standard tier is the Update default | UPD §2, SKL "Workflow router" | Exhaustive only when the user / triage / QC escalation says so |
| Multi-train projects → one terminal + N units | DSC §7, UNT "When to create new unit vs new terminal" | Not N terminals |
| Capacity range → record the MAX | UNT "Capacity conventions" | If a range is found, stage the **highest** value in the backend `Capacity` (cost range → median); the full range goes only in the wiki Background narrative — never stage the low end |
| Sufficient information threshold for new candidates | DSC §3 | Sponsor + approximate location + concrete step |
| Discovery scope gate (before the threshold) | DSC §3, SKL "Workflow router" | Must move LNG across a border by ship; domestic-only virtual-pipeline/trucking/peak-shaving is OUT OF SCOPE; resolve scope doubt before staging |
| gem.wiki coverage cross-check | DSC §4.0b, WFL §3 | Reconcile gem.wiki LNG pages vs the export CSV — a wiki page with no row is a discovery candidate (gem.wiki detects the gap, never the citation) |
| Upstream-oil-operator FLNG sweep | DSC §4.3, WFL §3 | In coastal hydrocarbon producers, sweep field operators monetizing associated gas (Gas Code / flaring-reduction tell), not just established LNG developers |

## Workflow steps

| Step | Location | What |
|---|---|---|
| Pull GEM CSV | UPD §11.3, DSC §10.3, REC §3.1, TRG §5 | Always first step every batch |
| Build dedup indexes | UPD §11.4, DSC §10.4 | `dedup_index.py` for project + sponsor-country indexes |
| Stale-sweep | TRG §3.1, UPD §3.4 | `stale_sweep.py` per LFC dormancy thresholds |
| Update tier (standard / exhaustive) | UPD §2.1 / §2.2, WFL §2 | Standard = worklist-driven (default); exhaustive = every row, every field + [ref] re-verified |
| Development-pipeline worklist | UPD §2.1, `stale_sweep.py` `dev_pipeline` block | EVERY proposed/construction/shelved unit, `recently_updated`-annotated (≤N months, default 3) |
| QC mechanical pass | QCS §3.1 | `completeness_sweep.py` + `stale_sweep.py` + `dedup_index.py` |
| QC citation link-rot sweep | QCS §3.2 | `citation_qc.py` — dead / blocked / name-miss verdicts on existing [ref] URLs |
| QC accuracy spot-check | QCS §3.3 | Stratified ~20–30 unit sample; supported / unsupported / stale per cell |
| QC post-apply check | QCS §3.4 | `apply_check.py` — applied / not_applied / diverged vs fresh export |
| Fetch timeline (per unit) | UPD §3.2, LFC "Anchor years vs timeline" | Mandatory before any status timeline edit |
| Source search by ring | DSC §4 | A: regulators, B: trade press, C: sponsor IR, D: broader |
| Source search by field | UPD §4 | Field-by-field tier guidance |
| Apply lifecycle state machine | LFC | Legal transitions, anchor year invariants, dormancy rules |
| Apply naming conventions | UNT | Terminal / unit / phase / train naming per methodology |
| Cluster coherence check | UPD §5 | URLs must reference correct project AND value |
| URL verification | UPD §7, DSC §8, REC §3.9 | `url_verifier.py` |
| Entity lookup | UPD §8, DSC §9 | `entity_lookup.py` — bare + `--remote`; `--country` annotates only |
| Country coverage gap | DSC §4.0, QCS §3.1 | `completeness_sweep.py` `coverage_gap` — countries with zero GEM terminals |
| Dormant-revival watch | DSC §4.0a, QCS §3.1 | `completeness_sweep.py` `dormant_revival_watch` — cancelled/shelved sites to revival-check (→ Discovery) |
| gem.wiki coverage cross-check | DSC §4.0b | Enumerate gem.wiki LNG pages, reconcile vs the export CSV — wiki page with no row = discovery candidate (gem.wiki never cited) |
| Capacity normalization | UPD §3.3, UNT "Capacity conventions" | `capacity_normalize.py` for unit conversion |
| FSRU sync check | SKL "FSRU sync rule" | When batch touches any FSRU terminal |
| Build review package | UPD §11.12, DSC §10.12, REC §3.10 | `build_review_package.py` |
| Recalc verification | All workflow §s | `recalc.py` before present_files |
| Missing-year ref-sweep (extract → research → build) | RSW §3–§4, WFL §8 | `refsweep_missing_year.py extract`/`build` over the read-only status timeline; year cell colored by tier; re-derive `tl_order` from DB every build |

## Confidence labels (cross-SOP)

| Color | Meaning | Where applied |
|---|---|---|
| Green | Primary/regulatory source OR 2+ Tier 1 corroborating | UPD §6, DSC §7, REC §4 |
| Yellow | Single non-primary source OR value implied | UPD §6 |
| Red | Single weak source — prefer leaving blank | UPD §6 |
| Blue | Re-verified unchanged | UPD §6.2 (terminals-specific addition) |
| (none) | Searched but no confirming source | UPD §6 |

## Lifecycle rules pointers

| Topic | LFC section |
|---|---|
| The eight statuses | "The eight statuses" |
| Substatus semantics | "Substatus semantics" |
| Timeline model + ordering | "The timeline model" |
| Current status derivation | "The timeline model" — closest non-planned-non-FID to bottom |
| Anchor years vs timeline | "Anchor years vs timeline (the export gap)" |
| Legal state transitions | "Legal state transitions" |
| Forbidden transitions | "Legal state transitions" → Forbidden transitions list |
| Anchor year invariants | "Anchor year invariants" |
| FIDStatus / FIDYear ambiguity | "FIDStatus / FIDYear ambiguity" |
| Dormancy thresholds (stale-sweep rules) | "Dormancy thresholds (the stale-sweep rules)" |
| News-recency test (proposed <2y; 2–4y inferred shelved; ≥4y inferred cancelled; most-recent article = ref) | "Applying the clock during research (the news-recency test)" |
| Inferred shelved/cancelled entries | "Adding an inferred entry" |
| Shelved → Cancelled escalation | "Shelved → Cancelled escalation" |
| Dead-and-revived | "Edge cases" → first bullet |
| Multi-unit project mixed statuses | "Edge cases" → multi-unit |
| FSRU vessel reassignment | "Edge cases" → permanent-replacement scheme + SKL FSRU sync rule |

## Schema pointers

| Topic | SCH section |
|---|---|
| Row structure (one row per unit) | "Row structure" |
| Multi-unit terminals | "Row structure" → distribution table |
| Status timeline NOT in export | "Status timeline is NOT in the export" |
| Project-level vs unit-level classification | "Field classification: project-level vs unit-level vs mixed" |
| All 115 columns table | "All 115 columns" |
| Read-only columns | "Read-only column list" |
| Enum value catalogs | "Enum value catalogs" |
| [ref]-fill priority targets | "[ref] columns — fill priorities" |
| Schema drift detection | "Schema drift detection" |

## Workbook structure

| Sheet | When populated | Source SOP |
|---|---|---|
| README | Always | WBC "Sheets" |
| updates | Update workflow | UPD §3 |
| new_terminals | Discovery workflow | DSC §7 |
| new_units | Discovery or update | DSC §7, UNT |
| wiki_updates | Update or discovery | UPD §3 (narrative content → wiki Background) |
| status_timeline_additions | Any workflow touching status | UPD §3.2, LFC |
| entity_additions | Any workflow adding entities | UPD §8, DSC §9 |
| audit_operating | Reconciliation workflow | REC §3.10 |
| audit_nonoperating | Reconciliation workflow | REC §3.10 |
| giignl_fsru_fleet | Reconciliation workflow | REC §3.10 |
| edits_to_gem | Reconciliation workflow | GEM-CSV-shaped PASTE VIEW: only the rows the research pass concluded need a DB change, with resolved values in the real GEM columns, color-coded, ref URLs in [ref] cells, and a leftmost _change column explaining what changed and why |
| giignl_full_extract | Reconciliation workflow | REC §3.10 |
| routing | Reconciliation workflow | REC §3.10 |
| fsru_sync | Any batch touching FSRUs | SKL FSRU sync rule |
| monitor_list | Discovery workflow | DSC §5 |
| stale_sweep | Triage or update | TRG §3.1, UPD §3.4 |
| country_notes_contributions | Any batch developing country knowledge | CNT "How to use this file" |
| qa_review | Always | All SOPs |

(Triage and QC are memo-only — no workbook. Memos land at `batches/triage_<stamp>_ET.md` / `batches/qc_<stamp>_ET.md`; TRG §2, QCS §2.)

## Pause-and-ask triggers

| Trigger | Primary location |
|---|---|
| Whole class of values systematically wrong | UPD §13, DSC §12, REC §6 |
| New rule would invalidate prior batches | UPD §13 |
| Source corroboration too thin even for yellow | UPD §13 |
| Discovery: >5 candidate clusters in same country | DSC §12 |
| Discovery: candidate ambiguous on threshold | DSC §12 |
| Reconciliation: >10% matched rows disagree | REC §6 |
| Reconciliation: extraction totals diverge >2% | REC §6 |
| FSRU sync: unresolvable reassignment | UPD §13, DSC §12 |
| Stale-sweep: >100 units due | TRG §8 |
| FSRU candidate not in carrier backend either | DSC §12 |
| Triage: schema drift detected | TRG §8 |
| Country regulator filings show pre-public projects | DSC §12 |
| QC: >10% sampled spot-check cells unsupported | QCS §6 (systemic flag) |
| QC: >25% dead link-rot in one country | QCS §6 (→ recommend exhaustive Update) |
| QC: multiple diverged edits in one applied batch | QCS §6 (apply-process error?) |
| Ref-sweep: whole class of timeline years look wrong | RSW §8 (schema misread, not data gap) |
| Ref-sweep: large share of UNRESOLVED are structural | RSW §8 (methodology signal — lead with it) |
| Ref-sweep: `GEM_READONLY_DB_URL` unset/unreachable | RSW §8 (no CSV fallback for timeline data) |

## Source roster pointers

| Need | SRC section |
|---|---|
| Sponsor IR for a project | "Tier 1a — Sponsor / operator / yard direct" |
| National regulator for a country | "Tier 1b — Regulators" |
| Class society for FSRU/FLNG vessel | "Tier 1c — Class societies" |
| GIIGNL / IGU handling | "Tier 1 (with caveats) — Industry reports" |
| Trade press tiers | "Tier 2 — Trade press" |
| Vessel database for FSRU | "Tier 4 — Vessel databases" |
| Forbidden sources | "Forbidden / cautioned" |
| Search query patterns | "Most productive search query patterns" |

## Country research pointers

CNT contains country-specific tips. The countries currently seeded:

China, Hong Kong, Japan, South Korea, Taiwan, Vietnam, Indonesia, Philippines, Bangladesh, India, Pakistan, Qatar, Russia, Croatia, Germany, Algeria, Egypt, Nigeria, Canada, United States, Brazil, Mexico, Australia, New Zealand, Papua New Guinea.

Other countries are stub-seeded per the GEM country-resource doc template (CNT "Empty country sections"); add full content as batches reach them.

## Entity canonical map pointers

ENT is organized by entity category. Quick lookup:

| If looking for... | ENT section |
|---|---|
| US-focused exporter (Cheniere, VG, etc.) | "US-focused exporters" |
| Integrated major (Shell, Total, etc.) | "Integrated majors" |
| State NOC (Aramco, QatarEnergy, etc.) | "State-linked sponsors / NOCs" |
| FSRU operator (Excelerate, Höegh, etc.) | "FSRU operators" |
| European import sponsor (ENGIE, Snam, etc.) | "European import sponsors" |
| Asian utility (TEPCO, JERA, etc.) | "Asian state utilities / IPPs" |
| African sponsor | "African" |
| Lender / EPC | "Lender / financier / EPC" |
| Project SPV | "SPVs (project-specific entities — common in LNG)" |
| DART regional euphemism decoder | "DART regional euphemism decoder" |

## Unit conventions pointers

| If naming a... | UNT section |
|---|---|
| Standard onshore terminal | "Standard onshore terminal name" |
| FSRU | "Exceptions" → FSRU row |
| FLNG | "Exceptions" → FLNG row |
| Deepwater Port | "Exceptions" → Deepwater Port row |
| Unknown-name project | "When the name is unknown" |
| Phase / train / expansion | "Multi-unit naming options" |
| Decision: new unit vs new terminal | "When to create a new unit vs a new terminal" |
| Owner field with JV | "Owner field conventions" |
| Location | "Location conventions" |
| Capacity | "Capacity conventions" |
| Cost | "Cost conventions" |
| Boolean field encoding | "Boolean fields encoding" |
