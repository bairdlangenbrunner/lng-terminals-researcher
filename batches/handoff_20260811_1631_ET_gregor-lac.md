# Hand-off — Latin America & Caribbean deep sweep (2026-08-11)

Two workbooks, both stamped `20260811_1631_ET`:

| File | What it is |
|---|---|
| `batches/lng_terminals_batch_20260811_1631_ET_gregor-lac_exhaustive_update.xlsx` | Exhaustive-tier update of the 87 existing terminals |
| `batches/lng_terminals_batch_20260811_1631_ET_gregor-lac_discovery.xlsx` | Discovery pass — new terminal + watch list |

Each workbook's `README` sheet explains its own sheets and the cell colours. Nothing here has been
applied to the live database; every row is a proposal for review.

## Scope

The 21 countries on the "Latin America & the Caribbean" roster in the country-assignments sheet:
Antigua and Barbuda, Argentina, Aruba, Bahamas, Brazil, Chile, Dominican Republic, Ecuador,
El Salvador, Guyana, Haiti, Honduras, Jamaica, Mexico, Nicaragua, Panama, Peru, Suriname,
Trinidad and Tobago, Uruguay, Venezuela — **106 unit rows / 87 terminals**.

**Colombia and Puerto Rico are excluded** — same subregion, but Colombia is Amalia's and Puerto Rico
is Baird's.

Discovery additionally searched the 13 LAC coastal countries that have **zero** GEM terminals today
(Barbados, Belize, Bermuda, Costa Rica, Cuba, Curacao, Dominica, Falkland Islands, Grenada,
Guatemala, Saint Kitts and Nevis, Saint Lucia, Saint Vincent and the Grenadines) — 34 countries in
all. Prior general coverage of the region was a *standard*-tier pass on 2026-06-04, so this is the
first full re-verification.

## What's in the update workbook

| Sheet | Rows | Notes |
|---|---|---|
| `updates_summary` | 332 | The review view: one row per proposed cell change, with sources, confidence colour and reasoning. 204 are `[ref]` citation edits, 128 are value changes, 4 are staged deletions (green + empty). Touches 79 of the 87 terminals. |
| `updates_in_database_format` | 94 | The same edits laid out for paste-in. |
| `status_timeline_additions` | 9 | Timeline entries to append (see below). |
| `qa_review` | 137 | Findings that are **not** edits — questions, conflicts, and data-health items. |
| `wiki_updates` | 15 | Draft `Wiki`/Background prose. |

By country, the edit volume is Brazil 52, Mexico 48, Bahamas 30, Trinidad and Tobago 25, Argentina
22, Chile 21, Venezuela 18, Panama 16, then single digits to low teens elsewhere. The 8 terminals
with no proposed edit are not gaps — each has qa/wiki findings instead (Cosan, Hidrovias do Brasil,
Porto Norte Fluminense, Tepor Macaé, Tergás Rio Grande, Nimofast Antonina, New Fortress Altamira,
Eni/Repsol Perla). Coverage is 87/87 researched.

Status-timeline additions: Antigua Power → operating (2026), TGS Puerto Galván → shelved (2024),
Aruba LNG → cancelled (2025), Clifton Pier → FID (2026), Suape FSRU → operating (2027),
Costa Azul → operating (2026), Vista Pacifico → cancelled (2025), Puerto Sandino → operating (2026).

## What's in the discovery workbook

- **1 new terminal:** **Woodbourne LNG Terminal**, Barbados (Saint Philip) — import, operating,
  Barbados National Oil Company. Note the entity: BNOCL appears to have been **renamed** Barbados
  National Energy Company Limited post-2025; that's filed as an `entity_rename` qa item so it gets
  renamed rather than duplicated (existing entity ID **100002005362**).
- **8 monitor-list candidates** (watch, not enough to add): Peru national regas tender
  (Proinversion), Bermuda Belco North LNG conversion, Curacao Bullen Bay, Trinidad NGC small-scale
  hub, Costa Rica RECOPE initiative, Panama LNG bunkering hub (Kanfer/C.B. Fenton — **rejected at
  the scope gate as bunkering**, kept only as a watch item), Mexico Guaymas, Mexico Karpowership
  Quintana Roo.
- **47 qa rows**, mostly per-country coverage verdicts — a deliberate record of *what was searched
  and found empty*, so the next sweep doesn't repeat the same blind search.

## Six items needing a reviewer decision (severity = high)

1. **New Fortress Altamira** (all 5 units) — NFE's 2026 restructuring (English scheme of
   arrangement + US Chapter 15) may change the controlling parent between BrazilCo and CoreCo.
   Not staged; needs sign-off on which entity GEM should carry.
2. **Puerto Sandino FSRU** (Nicaragua) — capacity conflict past the 20% materiality threshold:
   GEM 5.00 mtpa vs TradeWinds (Aug 2026) "3 million tonnes" for the terminal being commissioned.
3. **GNL Del Plata FSRU** (Uruguay), capacity — GEM holds 0.10 mtpa; a verified 2B1st Consulting
   page gives 10 MMm³/d (≈2.68 mtpa), ~27× larger. Not staged: single non-primary source plus a
   derived unit conversion. Needs a better source or a reviewer call.
4. **GNL Del Plata FSRU**, citation — after removing a banned source the existing capacity value
   rests on one yellow citation.
5. **Delta Caribe Oriental** (Venezuela) — four existing `[ref]` cells (FacilityType, Owner,
   Capacity, Location) cite the banned abarrelfull; the values need re-sourcing or clearing.
6. **Pecém FSRU** (Brazil) — the Eneva/Ceiba unit may have moved proposed → construction; evidence
   was suggestive, not conclusive.

## Known limitations — please read before treating a country as "done"

**The search budget ran out mid-sweep.** The session's web-search allowance (200 calls, shared
across all research agents) was exhausted partway through, so later agents fell back to direct page
fetches and HTML search scraping. Rather than let a starved agent's silence pass as a clean bill of
health, **nine country verdicts were downgraded to `coverage_verdict_search_limited` ("UNVERIFIED —
RE-SWEEP NEEDED")**:

- Panama, El Salvador, Honduras, Nicaragua
- Peru, Ecuador, Venezuela, Guyana, Suriname

For those nine, the update edits stand on their own verified sources, but **the discovery half is
incomplete** — treat them as un-swept for new-project purposes. Specific leads left unresolved:

- **Honduras — Amapala / Gulf of Fonseca** LNG-to-power lead (could not confirm or deny)
- **Nicaragua — "Puesta del Sol"** lead (could not confirm or deny)
- **Guatemala** — the highest-prospect of the 13 zero-terminal countries, under-searched
- The gem.wiki coverage cross-check (wiki page but no database row) was not completed for Peru,
  Ecuador, Venezuela, Guyana, Suriname

Genuinely complete and verified empty: the southern cone, Mexico, the Caribbean, and both
zero-terminal clusters other than Guatemala.

**Also still open:** four terminals whose live citations are bare homepages rather than specific
pages — Gato Negro Manzanillo, Manzanillo Gas & Power, Pecém, Porto Norte Fluminense (six others
were repaired in this batch); and the Argentina LNG `CaptiveGasPower` refs, which point at Argent
LNG URLs (wrong project).

**Recommendation:** run a supplementary discovery pass over the nine search-limited countries plus
Guatemala in a fresh session with a raised search budget. It's a small, well-defined follow-up — the
scope is already written down here and in the qa rows.

Full internal account of the run, including the tooling defects it exposed and their fixes:
`batches/run_records/2026-08-11_gregor-lac-deep-sweep.md`.
