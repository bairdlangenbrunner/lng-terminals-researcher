# Dev-pipeline re-check pass — subagent brief (one country)

A FOLLOW-UP pass on ONE country that was already exhaustively re-verified. You are NOT redoing the country.
You target two specific gaps the first pass left, using a tool it didn't: the **Wayback Machine**.

A human reviews the staged xlsx; nothing is auto-written to the live DB. Findings are leads, verify everything.

## Why this pass exists
The first pass labeled many bot-blocked URLs "dead" and dropped them. **A 401/403/000/202 is almost never a
dead page** — Reuters, S&P Global, Argus, Bloomberg, FT and many trade outlets refuse automated clients while
the page is alive in a browser (and usually archived). This pass recovers those, and resolves the values that
were genuinely left unsourced.

## Your inputs (absolute paths in your task prompt)
- WORKLIST: `.../devpipeline_exhaustive/middleeast/<slug>.worklist.json` — per cell: `field_name`, `old_value`,
  `ref_field`, and `ref_current` (the URLs GEM originally cited).
- FIRST-PASS UPDATES: `.../middleeast/<slug>.updates.json` — what was staged. Each record's `ref_urls` is the
  set of URLs that PASSed last time. (URL in `ref_current` but NOT in any staged `ref_urls` = a DROPPED ref.)
- FIRST-PASS QA: `.../middleeast/<slug>.qa.json` — look for `category:"unsourced_after_reverify"` (a value with
  NO working source) and dead/bot-block ref notes.
- GEM export (context): `.../scripts/gem_export.csv`.

## TASK 1 — recover dropped bot-blocked refs (do this for every dropped 401/403/000/202 URL)
For each cell, gather (a) its DROPPED `ref_current` URLs and (b) any URL the qa flagged as dead/403/401.
For each such URL:
1. Re-run `url_verifier.py "<url>" "<the cell's value>"`. If it now PASSes, great — it was transient.
2. If it FAILS with 401/403/000/202 (bot-block), check the Wayback Machine and verify the value on the SNAPSHOT:
   `curl -s "http://archive.org/wayback/available?url=<URL>"` → take `archived_snapshots.closest.url`
   → `python .../scripts/url_verifier.py "<snapshot-url>" "<the cell's value>"`.
   - **Snapshot PASSes** → the citation is GOOD. The *live* URL is the `[ref]` (not the snapshot URL); note
     "live but bot-blocked; value confirmed via Wayback <timestamp>" in `source_notes`. Recover it.
   - Snapshot 404/unavailable, or value absent on the snapshot → it stays dropped (genuinely unusable).
3. Only a real **404 / gone / value-absent-on-a-200-page** is "dead." Don't relabel those.
GUARD: `url_verifier` substring-matches, so `"5 billion"` PASSes on "160.5 billion cubic metres". For DOLLAR
figures put the `$` in the token; for collision-prone numbers, curl the page and read the sentence to confirm
the number means what the cell asserts BEFORE trusting the PASS.

## TASK 2 — resolve values left unsourced (`unsourced_after_reverify`)
For each unsourced FACTUAL value (cost, capacity, owner, operator, year, vessel, status, etc.):
1. If TASK 1 recovered a ref that confirms the GEM value → it's now sourced (see override schema).
2. Else SEARCH ELSEWHERE (fresh independent non-GEM sources) for the value:
   - **A different, corroborated value** → stage a CHANGE: `new_value` = the found value, confidence
     `green` (primary/regulatory or ≥2 independent) / `yellow` (single non-primary), `ref_urls` = its sources.
   - **The same GEM value, now corroborated** → stage it sourced (blue if unchanged), `ref_urls` = its sources.
   - **Nothing anywhere AND the existing GEM value cannot be supported** → stage a **DELETION**:
     `{"delete": true, "new_value": "", "confidence": "green", "ref_urls": []}` — this clears the cell (and its
     paired `[ref]`) and marks it green-empty, i.e. "recommend deleting this unsupported value." Say in
     `source_notes` what you searched and why $X is unsupportable. A multi-field value (Cost+CostUnits+CostYear,
     Capacity+CapacityUnits) is deleted as a SET — emit a delete record for EACH field of the set.

**DO NOT delete (these are NOT unsupported factual assertions — leave them as the existing qa note):**
- `Lat`/`Long`/`Accuracy` — GEM geocodes; the absence of an external decimal is not an error.
- GEM-*inferred* status metadata where `researcher_notes` documents the inference (e.g. a shelved unit's
  `ShelvedYear`/`StopYear`/`Substatus` inferred from a 2-year-no-news rule). Defer to the note.
- `"unknown"` / `"--"` / `"TBD"` placeholders — already non-values; not deletions, just stay blank.

## Output — one merge file + a done marker
Write `.../middleeast/<slug>.recheck.json` (a single object), then `.../middleeast/<slug>.recheck.done.json` LAST.

`<slug>.recheck.json` schema:
```
{
  "slug": "...", "country": "...",
  "update_overrides": [ <updates records — SAME schema as the first pass; one per cell you change/recover.
      For a recovered/added ref, include the cell's FULL ref_urls = its already-staged URLs (read them from
      <slug>.updates.json) PLUS the recovered ones — overrides REPLACE the first-pass record for that cell, so
      never drop the good URLs. confidence stays blue if value unchanged, green/yellow if you changed it.
      For a deletion: {..identity.., field_name, old_value, new_value:"", delete:true, confidence:"green",
      ref_field:(copy from worklist), ref_urls:[], source_notes, researcher_initials:"AI-draft (recheck)"} > ],
  "qa_add":      [ <NEW qa entries: deletions you staged, values you changed, anything still unresolved> ],
  "qa_resolved": [ <identify first-pass qa entries now RESOLVED so the merge drops them; match by
      {"terminal_id":..,"unit_id":..,"field_name":..} when present, else {"issue_contains":"<unique substring>"}> ],
  "summary": {"refs_recovered":N, "values_changed":N, "values_deleted":N, "still_unsourced":N}
}
```
Records that touch a cell OVERRIDE the first pass (the build keys by terminal_id+unit_id+field_name). Cells you
don't touch keep their first-pass record untouched — so only emit overrides for cells you actually change.

## Hard rules (unchanged)
- Every URL passes `url_verifier.py` with the actual value as token. NEVER cite gem.wiki / globalenergymonitor.org
  or a GEM-derivative — chase the primary source. ≥2 independent URLs for a staged value (more is better; pile
  them all into `ref_urls`) — but **two mirrors/host-copies of the SAME document are ONE source, never two**
  (the GIIGNL 2025 report at two URLs counts once; GIIGNL 2025 + 2026 are two). Don't pad `ref_urls` with
  mirrors to fake corroboration; a single-document value stays `yellow` and cites ONE canonical URL.
  URLs go ONLY in `[ref]`/`ref_urls`, never a data column.
- Copy `ref_field` from the worklist verbatim. Project-level value → override on EACH in-scope unit-row.
- Status change → qa note (`status_timeline`), never a staged Status edit (fetch_timeline is down).
- Read-only/out-of-scope columns are never written (none are in your worklist).

RETURN ONLY a terse ≤10-line summary: country; refs recovered (via Wayback / transient); values changed (w/
old→new + confidence); values deleted (green-empty) + why; still-unsourced count; blockers. Do NOT paste records.
