# QC accuracy spot-check — subagent brief

You are running the **QC SOP §3.3 accuracy spot-check** for the GEM Global Gas Infrastructure
Tracker's LNG terminals dataset. This is an **audit, not an edit pass**. You produce verdicts,
not staged edits. Nothing you write touches the live database.

## Background — why these specific cells

A researcher (Natalia Fretz) has just finished a research cycle and applied her findings directly
to the live GEM database (her edits land 2026-07-24…2026-07-29). Separately, an agentic batch
(`sw-europe`, 2026-07-17) had staged its own findings for the same terminals but was **never
applied**. `apply_check.py` compared the two and found cells where they **disagree**.

Each cell in your task list therefore has up to three values:
- `db_at_0717` — what the GEM database held on 2026-07-17
- `we_staged` — what the sw-europe agentic batch concluded (NOT authoritative — an unapplied draft)
- `db_now` — what the live GEM database holds today (usually Natalia's new value)

**Your job: determine which value is correct, from independent sources.** Neither
`we_staged` nor `db_now` is presumed right. `db_now` being newer is not evidence.

## Inputs
- GEM export: `/Users/baird/Dropbox/_git_ALL/_github-repos-gem/lng-terminals-researcher/scripts/gem_export.csv`
  (115 cols; **open with `encoding="utf-8-sig"`** — first header has a BOM). Country col = `Country/Area`.
  Match rows by `UnitID`. Read the row's existing `[ref]` URLs for the field you're checking —
  the first check is always "does GEM's own cited source support GEM's current value?"
- Your terminal/cell list is in your task prompt.

## Method — per cell

1. **Read the cited `[ref]`** for that field from the export (e.g. checking `Capacity` → read
   `Capacity [ref]`). Verify it with `url_verifier.py` passing the **claimed value** as the token.
   Does the cited source actually contain and support `db_now`?
2. **One fresh independent corroboration search** — sponsor/operator IR, the national regulator or
   TSO (CRE/Elengy France, Enagás/CNMC Spain, Snam/ARERA Italy, RAE/DESFA Greece, BNetzA/DEA
   Germany, GTS/ACM Netherlands, HERA/LNG Croatia), EU transparency (GIE ALSI/LNG database, ENTSOG),
   the ACER/EU PCI portal, or trade press (LNG Prime, Reuters, S&P Global, Argus, Upstream, and
   local-language outlets — Italian/Spanish/Greek/German/Dutch/French are all fair game and often
   the primary record).
3. **Verdict** per cell, one of:
   - `supported` — the cited ref contains and supports `db_now`
   - `unsupported` — the cited ref does NOT contain/support `db_now` (transcription or
     cluster-coherence error). Say what the ref actually says.
   - `stale` — the ref supports `db_now` but a newer credible source contradicts it
   - `db_now_correct` / `we_staged_correct` / `neither_correct` — use when you can positively
     resolve the disagreement; give the correct value explicitly in `correct_value`
4. If the two values differ only in **entity naming** (e.g. `IFM Investors` vs `IFM Global
   Infrastructure Fund`, `VTTI` vs `VTTI BV`, `Tojeiro Group` vs `Grupo Gadisa`) or only in
   **unit basis** (mtpa vs bcm/y — 1 mtpa ≈ 1.36 bcm/y), say so explicitly and state whether the
   two are the same underlying fact. That's a naming/basis finding, not a data error.

## VERIFY EVERY URL — and verify the VALUE is on the page
`python /Users/baird/Dropbox/_git_ALL/_github-repos-gem/lng-terminals-researcher/scripts/url_verifier.py "<url>" "<token>"`
Pass the ACTUAL claimed value as the token (the capacity number, owner name, status word, year,
vessel name) — "the page loads" is NOT verification. The verifier handles PDFs itself. Pass
`--log /Users/baird/Dropbox/_git_ALL/_github-repos-gem/lng-terminals-researcher/batches/staging/qc-natalia-europe/url_verifier_log.jsonl`.

**Bot-block ≠ dead:** HTTP 401/403/429 or a Cloudflare/paywall interstitial = a live page refusing
bots; the verifier auto-falls back to the newest Wayback snapshot, and a pass there verifies the
LIVE url. Only a hard 404/410/DNS failure (or live-but-value-gone) is dead.

## SOURCING — ABSOLUTE
- **NEVER cite gem.wiki or globalenergymonitor.org** — anywhere, for anything. It is GEM's own
  publication; citing it as evidence for the GEM database is circular. Anything that merely
  republishes or footnotes GEM (Wikipedia, IEEFA, news citing GEM) is likewise NOT independent —
  chase the primary source it points to and cite THAT.
- **Banned source: abarrelfull** (`abarrelfull.wikidot.com`, `abarrelfull.co.uk`) — never, even
  corroborated.
- Legacy `giignl.org/...` URLs are dead site-wide; official mirrors of each edition live on
  `elfsightcdn` / `cdn.prod.website-files.com` hosts (see `data/README.md`). **Two host-variants of
  the SAME GIIGNL edition are ONE source, never two** — but different editions (2025 and 2026) do
  count as two.
- Independent = different publishers/origins, not two pages of one outlet and not a primary plus
  its own press echo.

## Status-field cells specifically
For a `Status` disagreement, pull the unit's real status timeline before judging:
`python /Users/baird/Dropbox/_git_ALL/_github-repos-gem/lng-terminals-researcher/scripts/fetch_timeline.py <UnitID>`
(reads the read-only Postgres — always available). Lifecycle rules:
`docs/reference/lifecycle_rules.md`. An **inferred** shelved/cancelled still needs a ref citing the
dormancy evidence (the stalled planning doc or newest article), not a source saying "shelved".

## OUTPUT — write the file, return terse

Write a JSON list to
`/Users/baird/Dropbox/_git_ALL/_github-repos-gem/lng-terminals-researcher/batches/staging/qc-natalia-europe/spotcheck_<GROUP>.json`
(`<GROUP>` from your task prompt). One record per checked cell, keys EXACT:

```json
{
  "terminal_id": "T…", "unit_id": "G…", "terminal_name": "…", "country": "…",
  "field": "<exact GEM header>",
  "db_at_0717": "…", "we_staged": "…", "db_now": "…",
  "verdict": "supported|unsupported|stale|db_now_correct|we_staged_correct|neither_correct",
  "correct_value": "… (the value you believe is right; empty if unresolved)",
  "checked_ref": "<the GEM [ref] URL you verified, or empty if the cell had none>",
  "checked_ref_verdict": "supports|does_not_contain_value|dead|blocked_wayback_ok",
  "corroboration_urls": ["…"],
  "naming_or_basis_only": true,
  "note": "1–3 sentences: what the sources say and why you concluded this",
  "recommended_action": "no_change|fix_value|fix_ref|leave_blank_qa_note|reviewer_judgment",
  "researcher_initials": "AI-draft (QC spotcheck)"
}
```

Use `json.dump(..., ensure_ascii=False, indent=2)`. Set `naming_or_basis_only` false unless the
disagreement really is only naming/units.

**RETURN ONLY a terse summary (≤14 lines):** group; #cells checked; verdict counts; the cells where
`db_now` is WRONG (these are the memo's headline); any dead refs found; blockers. Do NOT paste the records.
