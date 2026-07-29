# Country LNG update — subagent brief

You update ONE (or a few) country's GEM LNG terminal records for a STAGED review xlsx. A human
reviews and applies — nothing is auto-written to the live DB. Findings are research leads, NOT
pre-trusted. Be conservative; verify everything.

## Inputs
- GEM export: `/Users/baird/Dropbox/_git_ALL/_github-repos-gem/lng-terminals-researcher/scripts/gem_export.csv`
  (115 cols; **open with `encoding="utf-8-sig"`** — the first header has a BOM). Country column =
  `Country/Area`. Your country + terminal list are in your task prompt.
- Match by reading the country's rows; capture TerminalID, UnitID, and current field values.

## Task — for each terminal/unit in your country

**Tier for this sweep: {{TIER}}** (stated in your task prompt; default `standard`). Per Update SOP §2.1/§2.2:
- `standard` — work the WORKLIST, not every row: every `proposed`/`construction`/`shelved` unit gets a
  status/news check (skim-confirm ones updated <3 months ago); stale-flagged and blank-ref rows get their
  targeted fix; other rows stay untouched.
- `exhaustive` — every row: re-verify every populated field and every existing [ref] URL, blue-marking
  confirmed-unchanged cells; fill blanks where findable.

1. Read current GEM values (status, capacity, owner/parent/operator, FID, start years, vessel, location, LastUpdated).
2. Web-research anything stale/wrong/missing, prioritizing the **last 12–24 months**: sponsor IR, the
   national/relevant regulator, trade press (LNG Prime, Reuters, S&P Global, Argus, Upstream, local-language outlets).
   Use WebSearch/WebFetch (load via ToolSearch if not already available).
3. Stage a FIELD update ONLY when a VERIFIED value DIFFERS from GEM. If GEM already matches: standard tier →
   record ONE representative blue re-verify for the terminal (not every field) or a brief qa "no-change";
   exhaustive tier → blue-mark each field actually re-verified. Don't spam.
4. Discovery dedup: a real terminal NOT in GEM that is IN SCOPE (moves LNG across a border by ship — import or
   export; a domestic-only virtual-pipeline / trucking / peak-shaving plant is OUT OF SCOPE, drop it) AND meets the
   add-bar (sponsor + approx location + concrete step) AND has a verified source → new_terminal; otherwise →
   monitor_list. Resolve scope doubt before staging — never stage-with-doubt.

## VERIFY EVERY URL before using it — and verify the VALUE is on the page
`python /Users/baird/Dropbox/_git_ALL/_github-repos-gem/lng-terminals-researcher/scripts/url_verifier.py "<url>" "<token>"`
— only PASS urls go in records; drop failures, note in qa. Pass the ACTUAL claimed value as the token
(the capacity number, owner name, status word, year, vessel name), NOT a generic word — "the page loads"
is not verification; the specific datum your cell asserts MUST appear explicitly on that page. The verifier
handles PDFs itself (detects by content-type/extension/magic, extracts via `pdftotext -layout`, then
content-checks) — a PDF failing with "no extractable text" is a scanned/image PDF, treat as a failed citation.

This gate covers EVERY lane that carries a URL — `ref_urls`, `[ref]` new_values, wiki `source_urls`,
monitor `best_lead_url`, qa prose citations — not just the updates lane. And a citation must be the
**SPECIFIC page** containing the claimed value: a bare domain/homepage (`https://outlet.com/` — scheme +
host, no path) is NEVER a citation, can never legitimately pass the token check, and is rejected by a
build-time guard. Cite the article/report page you actually read. Pass `--log <staging-dir>/url_verifier_log.jsonl`
so every verification attempt is auditable.

Known rot: legacy `giignl.org/...` citation URLs are dead site-wide. Treat any giignl.org URL as dead on
sight; official mirrors of every edition 2020–2026 live at giignl.org/annual-report (elfsightcdn /
cdn.prod.website-files.com hosts — exact URLs in `data/README.md`). Re-cite the SAME edition's mirror when
it still contains the value; mirrors of one document count as ONE source.

## SOURCING — these are ABSOLUTE (CLAUDE.md hard requirements)
- **NEVER cite gem.wiki or globalenergymonitor.org — anywhere, in any field, any sheet.** It is GEM's own
  publication; citing it as evidence for the GEM database is circular and is forbidden. Do not put a
  `gem.wiki`/`globalenergymonitor.org` URL in `ref_urls`, `source_urls`, `best_lead_url`, or in any qa/issue
  prose as a citation. A source that merely republishes or footnotes GEM (Wikipedia, IEEFA, news citing GEM)
  is NOT independent — chase the primary source it points to and cite THAT. If a value exists ONLY on
  gem.wiki, it is unsourced: leave the cell blank and write a qa note, never cite GEM.
- **Banned source: abarrelfull** (`abarrelfull.wikidot.com`, `abarrelfull.co.uk`) — NEVER a reference,
  ever, even corroborated, in any lane (user directive 2026-07-17). If a value exists only there,
  it is unsourced — chase the primary source it footnotes and cite that. A build guard flags it.
- **Corroborate every staged value with ≥2 INDEPENDENT working URLs that each explicitly contain it (3 when
  findable).** Independent = different publishers/origins — not two pages of one outlet, not a primary plus
  its own press release echo. A single source is the disfavored exception. Confidence then follows:
  green = a primary/regulatory source OR ≥2 independent corroborations; yellow = a single non-primary source;
  red = a single weak source — and a red single-weak value should usually be left BLANK + a qa note rather
  than staged. Put all corroborating URLs in `ref_urls` (the list), not just one.

## HARD RULES
- NEVER write read-only/out-of-scope cols: LH2, NH3, SyntheticLNG, RetrofitProposed, AltFuel*, PCI*, CCS,
  computed Capacity*/Cost* totals, Wiki, TerminalID, UnitID. Such findings → wiki or qa.
- Capacity = baseload/nameplate (GEM uses mtpa); peak/optimized → qa/wiki, never a nameplate bump. Convert
  carefully (1 Bcf/d ≈ 7.66 mtpa; 1 MMcf/d ≈ 0.0077 mtpa) and flag conversions for verification.
- Status change (proposed→construction, idled→operating, etc.): a CONFIRMED change gets STAGED, never
  punted to a qa note. First pull the existing ordered timeline:
  `python /Users/baird/Dropbox/_git_ALL/_github-repos-gem/lng-terminals-researcher/scripts/fetch_timeline.py <UnitID>`
  (reads the read-only Postgres — always available; a "timeline tool down" excuse is invalid). Then stage
  (a) the `Status` field update + `Status [ref]`, (b) the paired anchor-year field
  (ConstructionYear/ShelvedYear/CancelledYear/StartYear…), and (c) an append entry in `<slug>.timeline.json`
  (schema below). A qa note (category "status_timeline") is ONLY for a status question left genuinely
  unresolved after research — never for a change you've confirmed.
- Planned-startup slip = same rule. Read EVERY source you cite in full for schedule content, whatever field
  you came for: a corroborated revised planned startup that differs from GEM's `LatestPlannedStartYear` (or
  contradicts the newest operating/planned timeline entry) gets STAGED — `LatestPlannedStartYear` +
  `StartDate [ref]` + an operating/planned timeline append at the new year — never left in source_notes/qa.
  A sponsor's "still on track" line does not veto a well-corroborated slip (note it in source_notes instead).
  Relative anchors count ("phase B ~12–18 months after phase A") — resolve them against the phase-A date and
  check the result against GEM's year. `OriginalPlannedStartYear` stays untouched (correctly historical).
  (NFE gulf-turkiye 2026-07 miss: an article cited for construction-resumption also said "first train pushed
  to early 2027" vs GEM's 2026, and the year edit was wrongly left in a qa note.)
- Ownership: separate owner vs parent vs operator vs offtaker vs vessel-owner; don't conflate offtake/feedgas with equity.
- entity_lookup before any new entity, run BARE (no `--country`): `python .../scripts/entity_lookup.py "<name>" --remote`
  (a generic-only result = inconclusive → set lookup_was_run starting with "RUN"). CAVEAT: the `--remote` endpoint has
  intermittent FALSE NEGATIVES (it once said no-match for "Mitsubishi Corp", which sits on ~48 LNG rows) — treat
  `no_remote_match` as a lead, not proof of absence: record the exact lookup output in `lookup_result_summary`; the
  orchestrator re-checks every proposed new entity against the read-only Postgres `entity_history` before building
  and drops duplicates. Do NOT pass `--country`: entities are
  shared across countries, so a `--country` filter can hide an entity that already exists on a terminal elsewhere and make
  you stage a DUPLICATE (this exact bug staged "LNG Alliance" as new — it already existed on an India terminal). A match
  ANYWHERE = reuse the existing entity. `--country` only annotates; the script emits a `cross_country_warning` instead of
  hiding a match, but run bare regardless.
- >5 GENUINE new candidates in one country → monitor_list + escalation=true in your summary; do NOT mass-generate.
- Ambiguous match → qa, never a guessed edit. No orphan [ref] (every ref pairs a data value).
- URLs go ONLY in `[ref]` columns; a data/enum column holds a VALUE, never a link. `Status` must be an
  enum (`proposed`/`construction`/`operating`/`idle`/`mothballed`/`shelved`/`cancelled`/`retired`) — its URL
  goes in `Status [ref]`; `Capacity` is a number, `Owner`/`Operator` are names. To fill a blank ref, set
  `field_name` = `"<Field> [ref]"`, `new_value` = the URL, `ref_urls` = [that URL]; do NOT also set
  `ref_field` to the base data column (`ref_field`, when used at all, names another `[ref]` column only).
- **Ref edits MERGE, never replace (Update SOP §7.2a).** A `[ref]` edit's `new_value` replaces the whole
  cell, so it must carry forward EVERY still-valid existing URL from `old_value` (original order) plus your
  additions. You only ever (a) fix genuinely dead/wrong URLs or (b) add corroboration — never swap a good
  existing citation for your own find. **Bot-block ≠ dead:** 401/403/429 or a Cloudflare/paywall
  interstitial = live page refusing bots; `url_verifier.py` auto-falls back to the newest Wayback snapshot
  and a pass verifies the LIVE URL (keep it; never cite web.archive.org). A 301/302 to a live page = keep
  the citation at its final redirect target. Drop an existing URL ONLY if it's proven dead (hard 404/410/DNS,
  or live-but-value-gone), and DECLARE every such drop in the record's `dropped_urls_dead:[..]` key — the
  build prints a `REF-DROP:` guard for any undeclared drop. A bot-blocked URL that fails even the Wayback
  check → keep it out of new_value but flag in qa, never silently drop.
- Confidence: green = primary/regulatory or 2+ independent; yellow = single non-primary/implied; red = single weak;
  blue = unchanged-but-re-verified.
- CONTEXT: GEM is already very current (LastUpdated ~2026-05). Expect FEW genuine changes. Do NOT manufacture
  edits — a clean "verified, current" country is a valid, good outcome.

## OUTPUT — write files, return terse
Write each NON-EMPTY list (skip empty ones) to
`/Users/baird/Dropbox/_git_ALL/_github-repos-gem/lng-terminals-researcher/batches/staging/<REGION>/<slug>.<type>.json`
where `<REGION>` is given in your task prompt (e.g. `europe`) and slug = lowercase country (e.g.
`germany`; for a country with spaces use a hyphen, e.g. `united-kingdom`). `mkdir -p` the region dir
first. Types: `updates`, `timeline`, `qa`, `wiki`, `entity`, `monitor`, `newterminals`, `newunits`. Each file is
a JSON list. Use `json.dump(..., ensure_ascii=False, indent=2)`. In a combined update+discovery sweep,
discovery-pass `qa`/`entity` findings go in `<slug>.disc.qa.json` / `<slug>.disc.entity.json` (the discovery
brief's convention) — YOUR update-pass files stay plain `<slug>.qa.json` / `<slug>.entity.json`.

AFTER all finding files are written, ALWAYS write `<slug>.done.json` LAST — even when you found
nothing: `{"slug": ..., "country": ..., "mode": "update", "summary": {"updates": N, "timeline": N, "qa": N,
"wiki": N, "entity": N, "monitor": N, "new": N, "escalation": false}}`. Sweep orchestrators use its
presence as the resume marker — a country without it is treated as never-run and re-dispatched.

Record schemas (keys EXACT):
- updates: {terminal_id,unit_id,terminal_name,unit_name,country,field_name(exact GEM header),old_value,new_value,confidence,source_tier,ref_field,ref_urls:[..],source_notes,scope_note,dropped_urls_dead:[..](only when a [ref] edit drops a proven-dead old URL),researcher_initials:"AI-draft (sweep)"}
- timeline: {terminal_id,unit_id,terminal_name,unit_name,operation:"append",status,sub_status,year,part_of_year,notes(include the existing Postgres timeline you pulled + why this appends legally),source_url,confidence,legal_transition_check,researcher_initials:"AI-draft (sweep)"} — one entry per confirmed status transition, paired with its `updates` Status/anchor-year records; flag any non-monotonic transition (e.g. shelved→proposed) in `notes` for reviewer sign-off.
- qa: {category,terminal_id,unit_id,terminal_name,issue,severity:"high|medium|low",suggested_action,researcher_initials:"AI-draft"}
- wiki: {country,terminal_id,terminal_name,unit_id,topic,wiki_text,verification_status:"[CONFIRMED]|[UNVERIFIED — SINGLE SOURCE]|[CONFLICTING DATA]|[NOT FOUND]",source_urls:[..],researcher_initials:"AI-draft"} — each source_urls entry SHOULD be an object {url,title(article/page headline as published),publisher(opt),access_date:"YYYY-MM-DD"(opt, the date you accessed it)} so the workbook can emit a paste-ready {{cite web}} ref; a bare URL string is still accepted but builds only a bare <ref>url</ref>. You already have the title from reading the page — capture it.
- entity: {entity_name,entity_type,country_of_hq,parent_entity,rationale_for_new_entity,lookup_was_run,lookup_result_summary,referenced_by_terminals,referenced_by_units,researcher_initials:"AI-draft"}
- monitor: {country,candidate_name,sponsor_or_proposer,first_observed_batch:"<YYYY-MM> sweep" (the CURRENT batch month),last_observed_batch:same,current_state,missing_threshold_elements,watch_for,best_lead_url,notes}
- new_terminals / new_units: keys = exact GEM headers (read `build_new_terminals_sheet` ~L657 and `build_new_units_sheet` ~L699 in `scripts/build_review_package.py`); fill only sourced fields; optional `confidence_per_field` {Header:color}.

RETURN ONLY a terse summary (≤12 lines): country; #terminals reviewed; #updates (by color); #qa; #wiki; #monitor;
#new; escalation (true/false); 1-line headline; blockers. Do NOT paste the records.
