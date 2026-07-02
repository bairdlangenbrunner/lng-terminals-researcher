# Ref-sweep brief — backfill MISSING YEARS on LNG status-timeline entries

You research the **year** for a set of GEM LNG-terminal status-timeline entries that
currently have NO year, and corroborate each with verified source URLs. Read-and-stage
only — you never touch the live database.

Repo root: `/Users/baird/Dropbox/_git_ALL/_github-repos-gem/lng-terminals-researcher`
(cd there). Verifier: `scripts/url_verifier.py`.

## What each point is
Each object in your shard file is one status-timeline entry on one LNG terminal unit
that is missing its year. Fields: `st_id`, `pu_id`, `country`, `terminal`, `unit`
(`(default)` = the terminal's main/only unit), `status`, `substatus`, `timeline_order`.

## Which year to find (by `status`)
- `proposed`   → year the project/unit was first publicly **proposed / announced**.
- `construction` → year **construction (site works / ground-breaking)** began.
- `operating`  → year the unit **began operating** (commissioning / first LNG cargo /
  commercial start — prefer the commercial-operations year; note if only commissioning).
- `idled`      → year it was **idled** (stopped operating, short-term).
- `mothballed` → year it was **mothballed**.
- `retired`    → year it was **retired / decommissioned / permanently shut**.
- `shelved`    → year the project was **shelved / paused / suspended**.
- `cancelled`  → year the project was **cancelled / abandoned / terminated**.
- `FID`        → year of the **Final Investment Decision**.

A 4-digit calendar year is the target. If sources give a range or only month/quarter,
record the **year** and put the finer detail in notes.

## Rules (NON-NEGOTIABLE)
1. **Never cite GEM** (gem.wiki, globalenergymonitor.org) — circular. Never **theodora.com**,
   never **A Barrel Full / abarrelfull / any wikidot.com**. You may read them for leads but
   never cite them. Anything that merely republishes GEM is not independent — chase its
   primary source and cite that.
2. **Never fabricate a URL.** If you can't verify the year, stage it `UNRESOLVED` with a
   notes reason — no invented links.
3. **Every URL must pass the verifier before you stage it:**
   `python scripts/url_verifier.py "<url>" "<YEAR>" "<one identifying token>"`
   It requires **ALL** the substrings you pass to be present on the page (HTTP 200, no
   soft-error). So pass the 4-digit **year** PLUS one distinctive token you have confirmed
   is on the page (terminal name, operator, vessel, or city). Prints `Result: PASS ... 200`
   on success. If a good page uses a name variant, pass a token you know it contains (don't
   pad with tokens that aren't there, or it will fail).
4. **Corroborate with ≥2 independent sources** (separate publishers/origins — NOT the same
   wire story reprinted, NOT a primary + its own press echo, NOT two mirrors of one document).
   Tier:
   - ≥2 independent, both verified & year-present → `tier:"high"`, `independent:true`
   - 1 strong source (primary/regulatory) verified → `tier:"medium"`, `independent:false`
   - 1 weak / partial / conflicting → `tier:"low"`, `independent:false`
   - none verifiable → `class_out:"UNRESOLVED"` (omit tier)
5. **Search in the country's language too** when English is thin (e.g. Russian, Vietnamese,
   Persian, Spanish, Bahasa). Foreign pages still must pass the verifier (the year token is
   language-agnostic). Record `source_language` (`en`, `ru`, `vi`, `en,es`, …).
6. If sources **disagree with each other** on the year, pick the best-supported one, set
   tier `low`, and explain the conflict in notes.

## Output (write exactly this)
Write `shards/<your shard name>_result.json` under this staging dir — a JSON **list**, one
object per input point, each carrying ALL original fields PLUS:
```json
{
  "st_id":"...", "pu_id":"...", "country":"...", "terminal":"...", "unit":"...",
  "status":"...", "substatus":"...", "timeline_order":"...",
  "proposed_year": "2017",                       // "" if UNRESOLVED
  "class_out": "FILLED",                          // FILLED | UNRESOLVED
  "proposed_refs": ["https://...","https://..."], // [] if UNRESOLVED
  "verifications": [ {"url":"https://...","ok":true,"contains":["2017","Calcasieu Pass"]} ],
  "tier": "high",                                 // high|medium|low (omit for UNRESOLVED)
  "independent": true,
  "source_language": "en",
  "researcher_notes": "what the year refers to, how confirmed, any conflict/caveat"
}
```
Before finishing: `python -c "import json,glob; json.load(open(<your result file>))"` to
confirm it parses. Then return a 2-line summary: counts by class_out + tier, and list any
UNRESOLVED with a one-phrase reason.

## Quality bar
A re-verified link is not the goal — a **confirmed year** is. Make sure the page you cite
actually ties THIS terminal to THAT year for THAT milestone (e.g. don't cite a 2020 page
mentioning the terminal as evidence of a 2017 proposal). Prefer primary/regulatory
(FERC/regulator filings, sponsor press/IR, official commissioning announcements) over media,
and media over aggregators.
