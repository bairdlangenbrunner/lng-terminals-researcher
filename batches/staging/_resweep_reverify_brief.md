# Re-verification subagent brief — fix sourcing on already-staged sweep records

A prior sweep staged research records for your assigned slug. Two sourcing rules were NOT enforced and
must now be applied to every record you own. You do NOT re-pick what to research — you re-source the
values that are already staged, rewriting the files in place. Output stays STAGED for human review; never
touch the live DB.

## The two rules you are enforcing (CLAUDE.md hard requirements)

1. **NO gem.wiki / globalenergymonitor.org — anywhere.** Citing GEM's own publication as evidence for the
   GEM database is circular and forbidden. Remove every `gem.wiki`/`globalenergymonitor.org` URL from
   `ref_urls`, `source_urls`, `best_lead_url`, and from any qa/issue/notes prose used as a citation. A
   source that merely republishes/footnotes GEM (Wikipedia, IEEFA, news citing GEM) is NOT independent —
   chase the primary source it points to and cite THAT.
2. **≥2 INDEPENDENT working URLs per staged value, each explicitly containing the value (3 when findable).**
   Independent = different publishers/origins — not two pages of one outlet, not a primary + its own press
   echo. A single source is the disfavored exception.

## What to do, per staged record in your files

1. Read each value the record asserts (the `new_value` in an `updates` row; the data fields in a
   `new_terminals`/`new_units` row; the claim in a `wiki`/`monitor` entry).
2. Web-research that exact value from NON-GEM sources (sponsor IR, regulator, trade press: LNG Prime,
   Reuters, S&P Global, Argus, Upstream, local-language outlets). Use WebSearch/WebFetch (ToolSearch to load).
3. VERIFY each URL with the value as the token — the datum MUST appear on the page:
   `python /Users/baird/Dropbox/_git_ALL/_github-repos-gem/lng-terminals-researcher/scripts/url_verifier.py "<url>" "<the actual value>"`
   Only PASS urls go in records. (Verifier handles PDFs; "no extractable text" = scanned = failed citation.)
4. Rewrite the record's URL list to **≥2 independent PASSing non-GEM URLs** (3 if found).
   - If you find ≥2 independent corroborations → keep the value; confidence `green`.
   - If only ONE non-GEM source corroborates → keep the value but set confidence `yellow` and note single-source.
   - If the value's ONLY support was gem.wiki / a GEM-derivative and you find NO independent source →
     do NOT keep a fabricated/uncited value: BLANK the `new_value` (drop the updates row entirely) and add a
     `qa` entry (category `unsourced_after_reverify`) explaining the value could not be corroborated off-GEM.
   - Never leave an orphan `[ref]` (a URL with no value) or a value with a gem.wiki URL.
5. For `monitor`: replace a gem.wiki `best_lead_url` with the best non-GEM lead; if none exists, keep the
   monitor entry but set `best_lead_url` to "" and note it in `notes`.
6. For `qa`: if the prose cites gem.wiki as a source, reword to cite the primary source (or drop the URL);
   describing what GEM's *record* says (without a gem.wiki URL) is fine.

## Files you own
Listed in your task prompt (absolute paths). Rewrite each in place with the SAME schema
(`json.dump(..., ensure_ascii=False, indent=2)`). Keep every key that was there; only the URL lists,
confidence, and (where uncorroborable) the presence of the value/row change. Do not invent new edits or
new terminals beyond what was staged — this is a sourcing fix, not a fresh sweep.

## After rewriting all your files
Write `<slug>.reverify.done.json` LAST (slug = exactly as given in your prompt) next to them:
`{"slug": ..., "files_fixed": N, "gemwiki_removed": N, "values_corroborated": N, "values_blanked": N, "notes": "..."}`
Its presence is the resume marker — a slug without it is re-dispatched.

RETURN ONLY a terse ≤12-line summary: slug; files touched; #gem.wiki citations removed; #values now
≥2-corroborated; #downgraded to yellow; #blanked (uncorroborable); 1-line headline; blockers. Do NOT paste records.
