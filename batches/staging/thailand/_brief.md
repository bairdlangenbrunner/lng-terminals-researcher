# Thailand standard-tier Update — research brief (per-terminal subagent)

You are researching ONE Thailand LNG terminal for a GEM Global Gas Infrastructure Tracker
standard-tier Update batch. Today is **2026-07-10**. Work end-to-end; return a terse summary.

## Hard rules (non-negotiable — these are GEM's methodology)

1. **Every URL must pass `url_verifier.py` before you cite it.** From `scripts/`:
   `python url_verifier.py "<url>" "<claimed value token>" ["<token2>" ...]`
   The page/PDF MUST explicitly contain the specific value the cell asserts (a capacity number,
   owner name, status word, year, vessel). A page that loads but lacks the value is a FAILED
   citation, not a source. For dollar figures put `$` in the token. A 401/403 is a bot-block
   (site is live) — re-check the value against a Wayback snapshot before dropping the ref.
2. **Corroborate every staged value with ≥2 independent working URLs** that each explicitly
   contain it (3 when findable). Independent = different publishers/origins. Two mirrors/host-
   variants of the SAME document = ONE source (e.g. GIIGNL 2025 mirrored twice counts once;
   GIIGNL 2025 + GIIGNL 2026 count as two). One primary/regulatory source → green; one non-
   primary → yellow; one weak → red (prefer leaving blank + a qa note over staging red).
3. **NEVER cite gem.wiki or globalenergymonitor.org anywhere.** Also not IEEFA/Wikipedia/news
   that merely footnotes GEM — chase the primary source and cite THAT. If the only evidence is
   gem.wiki, treat the value as unsourced (blank + qa note).
4. **URLs go ONLY in `[ref]` fields.** A data/enum field holds a VALUE (Status = one of
   proposed/construction/operating/idle/mothballed/shelved/cancelled/retired; Capacity = a
   number; Owner = a name). Never put a URL in a data column.
5. **No orphan [ref]** — never fill a `[ref]` without a paired data value.
6. **Never punt a confirmed status change.** The status timeline is readable from the read-only
   Postgres via `python fetch_timeline.py <UnitID>` (already pulled for you below where relevant),
   so a confirmed transition gets STAGED (Status + anchor year + a timeline entry), never deferred
   to a qa note "because a tool is down." A qa note is only for a status question you genuinely
   could not resolve.
7. **Scope gate:** the terminal must move LNG across a border BY SHIP (import/export). A domestic-
   only virtual-pipeline/trucking/peak-shaving plant is out of scope. All the Thailand terminals
   here are marine LNG import — confirm, don't assume.
8. **Inferred shelved/cancelled needs a ref** citing the dormancy evidence (the newest project-
   specific article, or a planning-doc stall), not a source literally saying "shelved." Use the
   NEWEST anchor year (event year in the source body, not the publication/URL-slug date).
9. **Capacity range → record the MAX** in the Capacity field (range text goes only in wiki
   Background). Cost range → median.
10. **New entity check:** only if you would stage a NEW owner/operator/parent name, run
    `python entity_lookup.py "<name>" --remote` (bare, no --country) first. Reusing an existing
    name needs no check.

## What "standard tier" means for your terminal

- If it's **proposed/construction/shelved** (dev-pipeline): re-verify current status against the
  newest evidence; pull/《use》the timeline; stage any confirmed transition. Apply the news-recency
  dormancy test for proposed→shelved (>2y silence) / shelved→cancelled (>4y).
- **Blank-ref fills:** for each `[ref]` column that is blank but has a paired filled data VALUE,
  find ≥2 independent working sources for that existing value and fill the ref (value usually
  unchanged → confidence "blue" if re-verified, or the normal green/yellow for a fresh source).
- **Orphan refs** (a `[ref]` filled but its paired data value blank — e.g. `StartDate [ref]` on a
  never-operated unit) are a Rule-F data-health issue: do NOT invent a value; report it as a
  qa_review data_health note (leave for a cleanup batch).
- Rows/fields NOT on your worklist stay untouched.

## Output — write `batches/staging/thailand/<slug>.research.json`

One JSON object with these keys (omit empty arrays):
```
{
  "terminal_name": "...", "terminal_id": "T...", 
  "updates": [ {
      "unit_id": "G...", "unit_name": "--" or "Expansion"/"Phase I" etc.,
      "field": "Status" | "Capacity" | "Owner" | "Status [ref]" | "Capacity [ref]" | ... ,
      "current_value": "...", "new_value": "...",
      "ref_urls": ["...","..."], "confidence": "green|yellow|red|blue",
      "source_tier": "short description", "change_summary": "why / what evidence"
  } ],
  "status_timeline_additions": [ {
      "unit_id":"G...","operation":"append","status":"construction","sub_status":"actual",
      "year":2025,"part_of_year":"Q4","notes":"...","source_url":"...","confidence":"green",
      "legal_transition_check":"proposed -> construction: legal"
  } ],
  "wiki_updates": [ {"unit_id":"G...","topic":"...","wiki_text":"...","verification_status":"green","source_urls":["..."]} ],
  "qa_notes": [ {"category":"data_health|status_verification|link_rot|unverifiable_value|missing_field",
      "unit_id":"G...","gem_field":"...","severity":"low|medium","issue":"...","suggested_action":"..."} ],
  "entity_checks": [ {"name":"...","found":true,"entity_id":"...","note":"..."} ],
  "url_verifications": [ {"url":"...","tokens":["..."],"passed":true} ],
  "scope_verdict": "in_scope",
  "summary": "3-5 sentences: what you concluded and what you staged."
}
```
- For a staged `[ref]`-fill of an existing value, emit a single record with `field` = the data
  field (e.g. "Status"), `new_value` = the unchanged value, `confidence` "blue", and the ref_urls —
  the build routes the URLs to `Status [ref]`. To fill JUST a ref column, set `field` to the
  `[ref]` column name with the URL(s) in ref_urls and the paired value in `new_value`.
- Every ref_url MUST appear in `url_verifications` with the token(s) you checked and passed:true.
- Keep `researcher_initials` implicit ("AI-draft" is added at assembly).

Return to the main loop ONLY your `summary` plus counts (n updates / n timeline / n qa) — not the
full JSON.
