# 2026-07-20 — gem.wiki cite-error crawl (all LNG terminal pages)

## Plan

User request: crawl every unique gem.wiki page linked from the LNG terminals database and list pages whose References section shows a MediaWiki cite error (example: Lake Charles LNG Terminal). Read-only audit — no wiki edits, no GEM DB edits.

## Method

- Fresh export pulled 2026-07-20 (`gem_query.py --all-fields lng` → 1,272 unit rows).
- 842 unique `wiki` URLs extracted; each fetched and scanned for the rendered `mw-ext-cite-error` span (scratchpad crawler; percent-encodes non-ASCII page titles).

## Outcome

- **411 of 842 pages (49%) have at least one cite error** — 1,101 error instances total.
- Full list: `batches/deliverables/wiki_cite_errors_20260720.csv` (country, terminal, URL, error count, broken ref names).
- Error type is uniform: `Invalid <ref> tag; no text was provided for refs named X` (1,100 of 1,101). One outlier: Tamar FLNG has a `name defined multiple times with different content` error.
- 844 of the broken ref names are VisualEditor auto-names (`:0`, `:6`, …) — signature of edits that deleted the paragraph holding the full `<ref name=":N">…</ref>` definition while leaving later `<ref name=":N" />` reuses orphaned. Fix = recover the definition from page history (or re-cite) and restore it; the systematic scale suggests a scripted/bulk edit pass stripped definitions rather than 411 independent manual accidents.
- Worst pages: New Fortress Altamira (14), Krk FSRU (13), Stade LNG (11), Atlantic LNG Trinidad (10), Stade FSRU (9). Top countries: US 50, China 24, Brazil 23, Russia 21, Vietnam 21, India 18, Indonesia 18.
- Side finding — 4 GEM `wiki` fields point at 404 pages: `Penglai_LNG_Terminal_(Huapeike)` (page exists as `Penglai_LNG_Terminal`), `Damietta_FSRU`, `Nan'ao_LNG_Terminal`, `Sierra_Leone_LNG_Terminal` (no page found). Candidate wiki-field fixes for a future Update batch.

Status: audit complete; fixing the wiki pages is a separate (wiki-side) effort not covered by this repo's staging workflow.

## Spot check + repair prototype (same day)

History spot check (Lake Charles, Krk FSRU, New Fortress Altamira via MediaWiki API): all three broke in the same **2025-10-16 "Data Team" bot pass** ("Page edited for the lng tracker update", ~21:29 UTC). The bot regenerated the Project Details bullet section from the tracker DB; the full `<ref name="X">…</ref>` definitions that happened to live in that section were destroyed, orphaning the `<ref name="X" />` reuses in the Background prose. Affects VisualEditor auto-names (`:0`…) and human names (`EC1`, `eia`, `EurAct`) alike.

Repair is scriptable and was validated read-only on all three pages (34/34 orphans):
1. Find orphaned ref names in current wikitext (used self-closing, never defined).
2. Walk revision history newest→oldest for the donor revision holding each full definition.
3. Prose-match: the text preceding each current use must appear verbatim in the donor revision (compute anchors on the ORIGINAL current text — adjacent refs otherwise false-fail after the first insertion).
4. Replace the first self-closing use with the full definition (definition then lives in Background prose, so a future bot regeneration of Project Details can't re-break it).
5. Validate with `action=parse` preview: all three pages render 0 cite errors (was 7/13/14).

Not covered by this recipe: Tamar FLNG's "name defined multiple times with different content" (different error, manual fix); any page whose Background prose changed post-bot (anchor check fails → manual queue); orphans never defined in any revision (`NO_DONOR`).

## First live fix (same day)

Wiki API access set up: bot password `citation-fixer` on the user's gem.wiki account, token in macOS keychain (`security find-generic-password -s gem.wiki-botpassword -w`; account field holds the login name). Repair script (session scratchpad `repair_orphan_refs.py` + `wiki_session.py`): dry-run by default (before/after/diff artifacts + parse-preview validation), `--save` submits with `nocreate` + `basetimestamp` conflict protection; refuses to save unless preview shows 0 cite errors and the diff is insertions-only.

**Lake Charles LNG Terminal fixed live** after user reviewed the dry-run diff: 7 definitions restored, edit rev 1197537 (https://www.gem.wiki/Special:Diff/1197537), live page re-verified 0 cite errors (was 7).

## Random-10 pilot (same day, user-supervised)

Seeded random sample (seed 20260720) of 10 pages, repaired sequentially with per-page gates; all 10 saved, each re-verified 0 live cite errors: Coral North FLNG (rev 1197541), Kollsnes (1197543), Kenai (1197544), Inkoo FSRU (1197545), UTM Offshore FLNG (1197546), Huizhou (1197547), Texas GulfLink Deepwater Port (1197548), Main Pass Energy Hub FLNG (1197549), Rio Grande (1197550), Jaigarh (1197551). 33 definitions restored across the 10; running total 11 pages fixed / 40 definitions.

Learnings folded into the script: (a) orphans are NOT always in Background prose — Kollsnes's was in the Expansion Project Details bullets (definition died in the regenerated Project Details section); (b) anchor gate now falls back to whitespace-normalized comparison (bot pass reflows blank lines around headings; a pure-whitespace mismatch is not a prose change).

## Batch of 50 (same day)

Next 50 alphabetically (scratchpad `batch_repair.py`, 5s throttle, per-page gates, CSV log): **46 fixed (147 definitions restored), 4 skipped to manual, 0 failures.** Two initial `diff_not_insert_only` skips (Świnoujście rev 1197598, Ahlone rev 1197599) were a false positive in the insertions-only gate — SequenceMatcher's heuristic alignment; replaced with construction-based splicing (all first-use spans computed on the original text, spliced in one pass), after which both saved clean. Manual queue (real prose changes since the donor revision — anchor mismatch): Ain Sokhna FSRU (`:0`,`:1`), Andes Energy Terminal (`:0`), Atimonan LNG Terminal (`:0`), Batangas Clean Energy LNG Terminal (`bloom`).

**Running total: 57 pages fixed / 187 definitions restored; 4 in manual queue; ~354 flagged pages remain.**

## Second batch of 50 (same day)

Brunsbüttel FSRU → Escobar FSRU (alphabetical continuation; `batch50b_log.csv`): **50/50 fixed, 151 definitions restored, zero skips/failures** — the construction-based splice + whitespace-tolerant anchor gates from batch 1 held with no new edge cases.

**Running total: 107 pages fixed / 338 definitions restored; 4 in manual queue; ~304 flagged pages remain.**

## Third batch of 50 (same day)

Etinde FLNG → Hitachi LNG (alphabetical continuation; `batch50c_log.csv`): **46 fixed (107 definitions restored), 4 skipped to manual (anchor mismatch — real prose changes since the donor revision), 0 failures.** All 46 re-verified 0 live cite errors. New manual-queue entries: Far East LNG Terminal (`:0` vs donor rev 951421), Filipinas LNG Gateway Project FSRU (`:1` vs 1011600), Gorontalo FSRU (`:0` vs 951354), Gwangyang LNG Terminal (`:0` vs 1017181).

**Running total: 153 pages fixed / 445 definitions restored; 8 in manual queue (+ Tamar FLNG's duplicate-definition outlier); 249 flagged pages remain.**

## Migrated to goit-ggit-data-ops (same day)

This wiki-side effort now lives in `goit-ggit-data-ops/gem-wiki/cite-error-fixes/` (scripts, crawl results, batch logs, README + living STATUS.md with the fixed/manual/remaining lists). Future batches run from there; this run record is the historical narrative through batch 3 and won't be extended. Still owned by this repo: the 4 broken DB `wiki`-field links (404s) queued for a future Update batch, and the deliverable CSV in `batches/deliverables/`.
