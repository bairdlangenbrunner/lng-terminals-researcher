# Exhaustive dev-pipeline re-verify — subagent brief (one country)

You run an **EXHAUSTIVE** update on ONE country's GEM LNG terminal records that are in the development
pipeline — Status ∈ {`proposed`, `construction`, `shelved`}. A human reviews and applies the staged xlsx;
**nothing is auto-written to the live DB.** Findings are research leads, not pre-trusted. Verify everything.

This is NOT a fresh pick-what-to-research pass and NOT a re-sourcing of old staged records. Your worklist
is handed to you: a JSON file listing each in-scope unit and, per unit, the exact cells to re-verify.

## Your inputs (absolute paths in your task prompt)
- WORKLIST: `.../devpipeline_exhaustive/<region>/<slug>.worklist.json` — your units + `cells_to_reverify`
  (each carries `field_name`, `old_value`, and the CORRECT paired `ref_field`) + `blank_refs_with_data`
  (blank `[ref]` cells whose paired data value is populated) + `ref_current` (the URLs GEM currently cites).
- GEM export (context only): `.../scripts/gem_export.csv` (utf-8-sig; first header has a BOM).

## What exhaustive means here (Update SOP §2.2) — do this for EVERY unit in your worklist
For **each cell in `cells_to_reverify`**:
1. Web-research the CURRENT value of that field from independent NON-GEM sources (sponsor IR, the national/
   relevant regulator, trade press: LNG Prime, Reuters, S&P Global, Argus, Upstream, local-language outlets).
   Prioritize the last 12–24 months. Use WebSearch/WebFetch (load via ToolSearch if not already available).
2. **Re-verify the URL(s) GEM already cites** (`ref_current`) AND any new URL you find — every URL must pass
   `url_verifier.py` with the ACTUAL value as the token (below). Drop any that fail; note dead existing refs in qa.
3. Decide the outcome and stage ONE `updates` record for the cell:
   - **Unchanged** (current sources confirm `old_value`): `new_value` = `old_value`, `confidence` = **`blue`**
     (re-verified, unchanged). `ref_urls` = the FULL set of PASSing URLs for this value.
   - **Changed** (a verified value differs): `new_value` = the new value, `confidence` per the rule below.
   - **Could not corroborate off-GEM** (no PASSing non-GEM URL): do NOT stage a value. Leave the cell (don't
     color it) and add a `qa` entry (category `unsourced_after_reverify`). Never cite gem.wiki to "confirm".
4. **Pile on the references — the more the merrier.** Put EVERY url_verifier-PASSing URL that contains the
   value into `ref_urls` (not just two). For an unchanged cell, `ref_urls` = the existing cited URLs that
   still PASS **plus** every new corroborating URL you found. The build comma-joins them into the `[ref]` cell.
   **BUT "more the merrier" means genuinely INDEPENDENT sources — never two mirrors/host-copies of the same
   document.** The GIIGNL 2025 report mirrored at two URLs (e.g. `GIIGNL-Livre-2025` at `elfsightcdn` and at
   `website-files.com`) is ONE source, not two — cite it ONCE. Different editions (GIIGNL 2025 **and** 2026)
   are two. If a value rests on a single document, it is single-sourced (`yellow`), even if that document has
   several mirror URLs; do not pad `ref_urls` with mirrors to fake a `green`.
5. Copy `ref_field` from the worklist cell verbatim into the record (it encodes the irregular pairings, e.g.
   `ConstructionYear`→`ConstructionDate [ref]`). If `ref_field` is `null` there is no `[ref]` column for that
   field — still stage the (blue/changed) record so the data cell is colored; put the URLs in `source_notes`.

For **`blank_refs_with_data`**: fill the blank `[ref]` if you find PASSing URL(s) for the paired data value.
SKIP non-citable placeholder values — if the data value is `unknown` / `--` / `TBD` / `n/a` / empty, do NOT
fill its ref (you can't cite "unknown"); leave blank. No orphan `[ref]` (every ref pairs a real data value).

## VERIFY EVERY URL — and verify the VALUE is on the page
`python /Users/baird/Dropbox/_git_ALL/_github-repos-gem/lng-terminals-researcher/scripts/url_verifier.py "<url>" "<token>"`
Pass the ACTUAL claimed value as the token (the capacity number, owner name, status word, year, vessel name),
NOT a generic word — "the page loads" is not verification; the specific datum the cell asserts MUST appear on
that page. The verifier handles PDFs (a PDF failing "no extractable text" is scanned = a FAILED citation).

**A 401/403 is NOT "dead."** Reuters, S&P Global, Argus, Bloomberg, FT, many trade outlets return 401/403 to
automated clients (bot-blocking) while the page is perfectly alive in a browser. Before you call a URL "dead":
- A genuine death is a **404 / gone**, or a 200 page that no longer contains the value. Those are dead/failed.
- A **401/403/000/202** is almost always a bot-block or transient. Check the Wayback Machine and verify the
  value against the SNAPSHOT (snapshots are not bot-blocked):
  `curl -s "http://archive.org/wayback/available?url=<URL>"` → take `archived_snapshots.closest.url` →
  `python .../url_verifier.py "<snapshot-url>" "<value>"`. If the snapshot PASSes, the citation is GOOD — use
  the live URL as the `[ref]` (note in source_notes that it's archived/bot-blocked), do NOT label it dead.
- In qa, distinguish **dead (404/gone/value-absent)** from **bot-blocked (live, not machine-verifiable here)** —
  they mean different things to the human reviewer, who can open a bot-blocked page in a browser.

**Guard against false-positive token matches.** The verifier does substring matching, so `"5 billion"` PASSes
against "160.**5 billion** cubic metres" — a gas volume, not a $5B cost. For DOLLAR figures include the `$`
(`"$5 billion"`); for numbers that could collide, use a distinctive longer token and, when a PASS would drive a
staged value, eyeball the surrounding sentence (curl + strip tags) to confirm the number means what the cell asserts.

## SOURCING — ABSOLUTE (CLAUDE.md hard requirements)
- **NEVER cite gem.wiki or globalenergymonitor.org — anywhere, any field, any sheet.** It is GEM's own
  publication; citing it as evidence for the GEM database is circular and forbidden. A source that merely
  republishes/footnotes GEM (Wikipedia, IEEFA, news citing GEM) is NOT independent — chase the primary source
  it points to and cite THAT. If a value exists ONLY on gem.wiki → unsourced: blank + qa note, never cite GEM.
- **≥2 INDEPENDENT working URLs per staged value (3+ when findable), each explicitly containing it.** More is
  better here (see step 4). Independent = different publishers/origins — not two pages of one outlet, not a
  primary + its own press echo, **and not two mirrors/host-copies of the SAME document** (same GIIGNL edition
  at two URLs = ONE source; GIIGNL 2025 + 2026 = two). Confidence: `green` = a primary/regulatory source OR ≥2 independent
  corroborations; `yellow` = a single non-primary source; `red` = a single weak source (prefer BLANK + qa,
  don't stage red). Unchanged-and-reconfirmed = `blue`.

## HARD RULES
- NEVER write read-only/out-of-scope cols (none appear in your worklist by construction): LH2, NH3,
  SyntheticLNG, RetrofitProposed, AltFuel*, PCI*, CCS, computed Capacity*/Cost* totals, Wiki, TerminalID,
  UnitID, Researcher, LastUpdated. Such findings → wiki or qa, never an `updates` row.
- Capacity = baseload/nameplate (GEM uses mtpa); peak/optimized → qa/wiki, never a nameplate bump. Convert
  carefully (1 Bcf/d ≈ 7.66 mtpa; 1 MMcf/d ≈ 0.0077 mtpa) and flag conversions for verification.
- **Status change** (proposed→construction, shelved→cancelled, idled→operating, etc.) → a `qa` note
  (category `status_timeline`); do NOT stage a `Status` field edit and do NOT write a timeline file
  (`fetch_timeline` endpoint is DOWN). A blue re-verify of an unchanged Status is fine.
- **`researcher_notes_*` may document a DELIBERATE divergence** (e.g. GEM holds a train as `construction`
  though a report calls it operating). DEFER to it — verify, don't override; if a source conflicts with a
  documented note, raise it in qa, don't stage the bump.
- Ownership: separate owner vs parent vs operator vs offtaker vs vessel-owner; don't conflate offtake/feedgas
  with equity. `entity_lookup` before proposing any NEW entity name:
  `python .../scripts/entity_lookup.py "<name>" --country "<C>" --remote` → stage an `entity` record.
- A multi-unit terminal: a project-level confirmation (Owner/Operator/Location/Cost/etc.) applies to ALL its
  in-scope unit-rows — stage the record on EACH in-scope unit-row of that terminal (note `scope_note`).
- URLs go ONLY in `[ref]` columns / `ref_urls`; a data column holds a VALUE, never a link.
- CONTEXT: GEM is already current (most LastUpdated ~2026-05). Expect FEW genuine changes — most cells will be
  blue re-verifies. Do NOT manufacture edits; a clean "verified, current" country is a good outcome.

## OUTPUT — write files, return terse
Write each NON-EMPTY list to `.../devpipeline_exhaustive/<region>/<slug>.<type>.json` (region + slug in your
prompt). Types: `updates`, `qa`, `wiki`, `entity`, `monitor`. `json.dump(..., ensure_ascii=False, indent=2)`.

`updates` record schema (keys EXACT):
`{terminal_id, unit_id, terminal_name, unit_name, country, field_name (exact GEM header), old_value,
new_value, confidence (green|yellow|blue), source_tier, ref_field (copied from worklist; or omit if null),
ref_urls:[ALL verified URLs], source_notes, scope_note, researcher_initials:"AI-draft (devpipeline-exh)"}`
`qa`: `{category, terminal_id, unit_id, terminal_name, issue, severity:"high|medium|low", suggested_action,
researcher_initials:"AI-draft"}`
`wiki`/`entity`/`monitor`: same schema as the standard country brief.

AFTER all finding files are written, ALWAYS write `<slug>.done.json` LAST — even if nothing changed:
`{"slug":..., "country":..., "tier":"exhaustive", "units_reviewed":N, "cells_reverified":N,
"summary":{"changed":N, "blue_unchanged":N, "refs_added":N, "blanked_unsourced":N, "qa":N, "status_changes_flagged":N}}`
Its presence is the resume marker — a slug without it is re-dispatched.

RETURN ONLY a terse ≤12-line summary: country; #units; #cells re-verified; #changed (by color); #blue;
#refs added; #blanked-unsourced; #status changes → qa; 1-line headline; blockers. Do NOT paste records.
