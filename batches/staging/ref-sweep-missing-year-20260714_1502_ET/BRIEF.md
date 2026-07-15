# Ref-sweep brief — backfill MISSING YEARS on LNG status-timeline entries

You research the **year** for a set of GEM LNG-terminal status-timeline entries that
currently have NO year, and corroborate each with verified source URLs. Read-and-stage
only — you never touch the live database.

Verifier: `scripts/url_verifier.py` (run from the repo root).

## What each point is
Each object in your shard file is one status-timeline entry on one LNG terminal unit
that is missing its year. Fields: `st_id`, `pu_id`, `country`, `terminal`, `unit`
(`(default)` = the terminal's main/only unit), `fuel_type` (LNG / Oil / NGL / NH3 / …
— non-LNG legacy terminals appear too; research them the same way), `status`,
`substatus`, `timeline_order`.

## Which year to find (by `status`)
- `proposed`   -> year the project/unit was first publicly **proposed / announced**.
- `construction` -> year **construction (site works / ground-breaking)** began.
- `operating`  -> year the unit **began operating** (commercial start preferred; note
  if only commissioning).
- `idled`      -> year it was **idled**.
- `mothballed` -> year it was **mothballed**.
- `retired`    -> year it was **retired / decommissioned**.
- `shelved`    -> year the project was **shelved / suspended**.
- `cancelled`  -> year the project was **cancelled / abandoned**.
- `FID`        -> year of the **Final Investment Decision**.

A 4-digit calendar year is the target. If sources give a range or only month/quarter,
record the **year** and put the finer detail in notes.

## Rules (NON-NEGOTIABLE)
1. **Never cite GEM** (gem.wiki, globalenergymonitor.org) — circular. Never theodora.com,
   never A Barrel Full / abarrelfull / any wikidot.com. Read for leads, never cite.
   Anything that merely republishes GEM is not independent — chase its primary source.
2. **Never fabricate a URL.** If you can't verify the year, stage it `UNRESOLVED` with a
   notes reason — no invented links.
3. **Every URL must pass the verifier before you stage it:**
   `python scripts/url_verifier.py "<url>" "<YEAR>" "<one identifying token>"`
   It requires ALL substrings present (HTTP 200). Pass the 4-digit **year** PLUS one
   distinctive token you confirmed is on the page (terminal/operator/vessel/city).
4. **Corroborate with >=2 independent sources** (separate publishers — NOT the same wire
   story reprinted, NOT a primary + its own press echo, NOT two mirrors of one document).
   - >=2 independent, both verified & year-present -> `tier:"high"`, `independent:true`
   - 1 strong source (primary/regulatory) verified -> `tier:"medium"`, `independent:false`
   - 1 weak / partial / conflicting               -> `tier:"low"`, `independent:false`
   - none verifiable                              -> `class_out:"UNRESOLVED"` (omit tier)
5. **Search in the country's language too** when English is thin (ru/vi/fa/es/id/…).
   Foreign pages still must pass the verifier. Record `source_language`.
6. If sources **disagree**, pick the best-supported year, set tier `low`, explain in notes.

## Second-pass note
If this shard lives under `shards_p2/`, these points already came back UNRESOLVED once.
Dig harder: Wayback (web.archive.org) for dead pages, FERC/regulator dockets, company IR
& port-authority histories, EIA series, local-language trade press. Only leave UNRESOLVED
if there is genuinely no defensible year — do NOT force a weak one.

## Output (write exactly this)
Write `<your shard name>_result.json` next to your input shard — a JSON **list**, one
object per input point, each carrying ALL original fields PLUS:
```json
{
  "st_id":"...", "pu_id":"...", "country":"...", "terminal":"...", "unit":"...",
  "status":"...", "substatus":"...", "timeline_order":"...",
  "proposed_year": "2017",                        // "" if UNRESOLVED
  "class_out": "FILLED",                           // FILLED | UNRESOLVED
  "proposed_refs": ["https://...","https://..."],  // [] if UNRESOLVED
  "verifications": [ {"url":"https://...","ok":true,"contains":["2017","Calcasieu Pass"]} ],
  "tier": "high",                                  // high|medium|low (omit for UNRESOLVED)
  "independent": true,
  "source_language": "en",
  "researcher_notes": "what the year refers to, how confirmed, any conflict/caveat"
}
```
Write INCREMENTALLY (overwrite your result file every ~3 points) so nothing is lost if
interrupted. Before finishing, confirm it parses. Then return a 2-line summary:
counts by class_out + tier, and any UNRESOLVED with a one-phrase reason.

## Quality bar
A re-verified link is not the goal — a **confirmed year** is. The page you cite must tie
THIS terminal to THAT year for THAT milestone (don't cite a 2020 page merely mentioning
the terminal as evidence of a 2017 proposal). Prefer primary/regulatory > media >
aggregators.
