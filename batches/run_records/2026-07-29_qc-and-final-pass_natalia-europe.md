# 2026-07-29 — QC + final exhaustive update + discovery, Natalia's Europe scope

**Plan:** the three passes the user asked for over the 13 countries assigned to Natalia Fretz,
now that her research is finished — (1) a QC pass, (2) an **exhaustive**-tier Update, (3) a final
Discovery pass. Scope: Albania, Belgium, Croatia, France, Germany, Gibraltar, Greece, Italy, Malta,
Montenegro, Netherlands, Portugal, Spain — 67 terminals / 96 unit-rows in the fresh 2026-07-29 pull
(1,274 unit-rows / 843 terminals DB-wide). Sequencing per the user's call: **QC memo first, then fold
its fixes into the update.** Dispatch per `docs/workflows.md` §5 — one subagent per country, on
efficient models (never Fable), 26 agents total across the update and discovery waves.

Standing note from the user on refs: *"most of the refs should work so you don't have to add more if
they do"* — so re-verified-clean refs were left alone rather than padded with extra corroboration.

## Deliverables

| Pass | Output |
|---|---|
| QC | `batches/qc_20260729_1345_ET.md` (memo only — QC never edits) |
| Exhaustive Update | `batches/lng_terminals_batch_20260729_1918_ET_natalia-europe_exhaustive_update.xlsx` |
| Discovery | `batches/lng_terminals_batch_20260729_1914_ET_natalia-europe_discovery.xlsx` |

Staged evidence: `batches/staging/natalia-europe/` (per-country JSONs + `meta.json`); QC evidence in
`batches/staging/qc-natalia-europe/`.

**Two earlier update builds are SUPERSEDED — do not paste from either** (also listed in `meta.json`
under `superseded_builds`): `…_1858_ET` predates the ref-drop repairs and carries 31
undeclared-ref-drop violations; `…_1913_ET` predates the Mugardos ref-restore and the Eagle FSRU
deletion grade. **`…_1918_ET` is the one to use.**

## What's in the workbooks

- **Update** (265 update records over 51 in-scope terminals — 104 green / 50 yellow / 111 blue,
  no red and none ungraded): 2 status-timeline additions, 1 entity addition, 56 qa_review items,
  4 wiki updates. Builds with **zero** `GUARD:` / `REF-DROP:` / bare-domain / banned-domain
  warnings; `recalc.py` clean.
- **Discovery**: 3 new terminals, 0 new units, 3 entity additions, 1 new monitor candidate
  (+4 rolled forward), 51 qa_review items. `recalc.py` clean.

## Merge-time QC gate (§5 step 3a) — all four parts ran

1. **Banned/circular-source scan — clean.** gem.wiki appears in 17 prose mentions, 0 as a URL;
   abarrelfull appears only in `old_value` / `dropped_urls_dead` removal positions, and is absent
   from every `new_value`.
2. **Entity re-check against read-only Postgres** — found exactly one real gap, now staged:
   `Gas Natural Rigassificazione Italia S.p.A.` (needed by a Zaule LNG Terminal `Owner` edit;
   0 Postgres hits, nearest matches are the Naturgy parent lineage). **Caveat:**
   `GEM_PROJECT_DB_BASE_URL` is not set this session, so `entity_lookup.py --remote` was
   unavailable — every subagent `no_remote_match` is a *skipped* check, not a negative. Postgres
   was the substitute.
3. **`url_verifier.py` spot-checks** on non-blue records, each using the record's own claimed value
   as the token — **7/7 PASS**.
4. **Done markers** — 26/26 dispatched slugs wrote theirs.

Two duplicate-entity clusters found in the shared entity system and logged to qa (live, non-deleted,
not ours to merge): Tree Energy Solutions ×2, Vitol Holding ×3, JERA vs JERA Co.

## Two orchestrator corrections to subagent work (post-gate, from a workbook read-through)

- **Mugardos LNG Terminal `Owner [ref]` — an improper drop of a LIVE URL, reversed.** The Spain
  agent dropped `reganosa.com/en/shareholders` because the page doesn't contain the token
  "Mugardos", and declared it in `dropped_urls_dead`. Both were wrong: the page is live (PASS on
  `Reganosa` / `Shareholders` / `Xunta`) and it is Reganosa's *own* shareholder disclosure — the
  primary source for the very cap table the cell cites. Name-absence is advisory (QC SOP §3.2), never
  grounds for a drop, and declaring a live page as dead is a false declaration. Restored; the record
  went red-on-one-URL → **yellow on two retained sources, one primary**, with the Owner *value* still
  flagged in qa. Only `giignl.org/2021` (404) stays dropped. **This is the class to watch for in
  future sweeps: agents treating `name_miss` as rot.** A sweep of every other `dropped_urls_dead`
  entry in the batch found 2 more candidates, both legitimate — `gie.eu/…/lng-investment-database`
  and `giignl.org/…GIIGNL-2024-Annual-Report-1.pdf` are each a real 404 (re-verified by hand).
- **Eagle FSRU `Capacity` staged deletion had no confidence grade**, so it rendered uncoloured.
  Set to `green` per `workbook_conventions.md` ("green + empty = staged deletion").

## Findings worth the reviewer's eye

- **Monfalcone** (discovery qa): the record's `Offshore=False` / `Floating=False` and its
  dock-anchored coordinates contradict its own description of a ~144,000 m³ floating storage vessel
  moored ~20 nm offshore. Flagged rather than guessed. The *scope* gate is not in doubt (LNG reaches
  Monfalcone across a border by ship).
- **Melilla** (discovery qa): Owner/Parent/Operator staged as the plain parents "Endesa SA; Enagas
  SA" though the sources name Endesa Generación S.A.U. and Enagás Emprende. `Status=proposed` is
  correct (not inferred-shelved) — the funding dispute is live 2025–2026 reporting.

## Tooling fixed along the way (each a permanent repo improvement)

- **`normalize.py` — capacity unit table was wrong by ~2.7×.** `bcf/d` and `MMcf/d` used `365/130`,
  giving 1 MMcf/d ≈ 0.00281 mtpa, contradicting both `unit_conventions.md` and GEM's own precomputed
  `CapacityinMtpa` (Stade/Wilhelmshaven FSRU: 750 MMcf/d → 5.75 mtpa, i.e. ≈0.00767). Now derived
  from the same 1 mtpa = 1.36 bcm/y equivalence as every other row. Found while converting Germany's
  MMcf/d rows; `tests/test_capacity_normalize.py` updated with a cross-check against the DB's figure.
- **`completeness_sweep.py` — phantom `orphan_ref`s.** `StartDate [ref]` is the shared ref for the
  whole start-date family, planned years included; omitting the planned columns made 33 of 36
  "orphans" in this pass false positives. Rule F is about a ref with no paired value *anywhere in
  its family*.
- **`url_verifier.py` — Wayback verification for bot-blocked URLs**, with a CDX fallback because the
  availability API's first answer can't be trusted. Keeps "bot-block ≠ dead" enforceable instead of
  aspirational.
- **`citation_qc.py` — new `content_gone` verdict (soft-404 / lapsed-domain detector).** HTTP 200 is
  not evidence a citation lives: `croenergo.eu/Download.ashx?FileID=…` now serves an unrelated
  "European Environment" blog, `lngworldshipping.com/news/view,croatia-considers-fsru…` is a parked
  domain, and `ec.europa.eu/…/pci_list_gas.pdf` serves the EC Energy homepage as HTML. All three had
  been grading `ok` for years. The check tests a page against its own URL slug words and only fires
  when the terminal name is *also* absent; the §6 threshold is now computed on `dead + content_gone`.
  **It abstains on opaque paths** — GUID/hex/vowel-less segments are not words a page has any reason
  to contain, and treating them as slug words initially produced a false `content_gone` on the *live*
  GIIGNL 2026 report at `files.elfsightcdn.com/<guid>/<guid>/GIIGNL-…` across 10 Croatian citations.
  Treat an abstention as unchecked, not clean (croenergo was confirmed dead by hand, not by the tool).
  Documented in QC SOP §3.2 + `scripts/README.md`; repo suite 81 passed.
- **`location_accuracy_audit.py`** (new) — coordinate-accuracy worklist for the location-improvement
  goal: all 492 `Accuracy = approximate` terminals split by edit recency, with live project-edit
  links. Deliverable kept at `batches/deliverables/location_accuracy_audit_20260729_1146_ET.xlsx`.

## Caveats to carry forward

- **The QC memo's dead-ref counts are a FLOOR.** A truncation bug in the ref extractor graded 434
  ref cells tracker-wide (40 in scope) on truncated stubs, producing false PASSes. 36 of the 40 were
  Google Maps `Location` refs; the 4 non-Maps ones were run down in this batch. Logged as
  `qc_tooling_bug` in the update book's `qa_review`.
- **`content_gone` post-dates the memo.** The memo's per-country rot figures were computed before the
  detector existed. Croatia re-runs at 0 dead / 1 content-gone (1.1% rot) — the four countries the
  memo reported at 0% dead (Croatia, Greece, Montenegro, Portugal) still hold; "0% dead" was never
  "0% bad", which is exactly the gap the detector closes.
- Subagent web searches were capped; the Greece agent worked around its search budget by driving
  DuckDuckGo through WebFetch. Worth knowing when judging coverage depth per country.
- The `20260729_1914_ET` discovery file was rebuilt in place minutes after a first attempt that
  tripped a `GUARD:` and showed every region's monitor items (missing `checked_roster.json`, now
  written for the 13 countries). Same-minute stamp collision, superseded content only — but it *did*
  overwrite, against the never-overwrite rule.

## Next

Reviewer applies the update workbook, then the discovery workbook. `meta.json` `applied` stays
`null` until then. `sw-europe` (2026-07-17, built-never-applied) is superseded for these 13
countries — its staged values predate Natalia's own live-DB edits, so its apply_check divergences
are QC input, not paste targets.
