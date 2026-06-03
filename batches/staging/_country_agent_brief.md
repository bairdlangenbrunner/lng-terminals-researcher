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
1. Read current GEM values (status, capacity, owner/parent/operator, FID, start years, vessel, location, LastUpdated).
2. Web-research anything stale/wrong/missing, prioritizing the **last 12–24 months**: sponsor IR, the
   national/relevant regulator, trade press (LNG Prime, Reuters, S&P Global, Argus, Upstream, local-language outlets).
   Use WebSearch/WebFetch (load via ToolSearch if not already available).
3. Stage a FIELD update ONLY when a VERIFIED value DIFFERS from GEM. If GEM already matches, record ONE
   representative blue re-verify for the terminal (not every field) or a brief qa "no-change". Don't spam.
4. Discovery dedup: a real terminal NOT in GEM, that meets the add-bar (sponsor + approx location + concrete
   step) AND has a verified source → new_terminal; otherwise → monitor_list.

## VERIFY EVERY URL before using it
`python /Users/baird/Dropbox/_git_ALL/_github-repos-gem/lng-terminals-researcher/scripts/url_verifier.py "<url>" "<token>"`
— only PASS urls go in records; drop failures, note in qa. For a PDF that returns HTTP 200 but "missing content",
confirm via `curl -sL "<url>" -o /tmp/v.pdf && pdftotext -layout /tmp/v.pdf - | grep -i "<token>"` (verifier has no PDF path).

## HARD RULES
- NEVER write read-only/out-of-scope cols: LH2, NH3, SyntheticLNG, RetrofitProposed, AltFuel*, PCI*, CCS,
  computed Capacity*/Cost* totals, Wiki, TerminalID, UnitID. Such findings → wiki or qa.
- Capacity = baseload/nameplate (GEM uses mtpa); peak/optimized → qa/wiki, never a nameplate bump. Convert
  carefully (1 Bcf/d ≈ 7.66 mtpa; 1 MMcf/d ≈ 0.0077 mtpa) and flag conversions for verification.
- Status change (proposed→construction, idled→operating, etc.) → a qa note (category "status_timeline");
  do NOT stage a Status field edit and do NOT write a timeline file (fetch_timeline endpoint is DOWN).
- Ownership: separate owner vs parent vs operator vs offtaker vs vessel-owner; don't conflate offtake/feedgas with equity.
- entity_lookup before any new entity: `python .../scripts/entity_lookup.py "<name>" --country "<C>" --remote`
  (a generic-only result = inconclusive → set lookup_was_run starting with "RUN").
- >5 GENUINE new candidates in one country → monitor_list + escalation=true in your summary; do NOT mass-generate.
- Ambiguous match → qa, never a guessed edit. No orphan [ref] (every ref pairs a data value).
- Confidence: green = primary/regulatory or 2+ independent; yellow = single non-primary/implied; red = single weak;
  blue = unchanged-but-re-verified.
- CONTEXT: GEM is already very current (LastUpdated ~2026-05). Expect FEW genuine changes. Do NOT manufacture
  edits — a clean "verified, current" country is a valid, good outcome.

## OUTPUT — write files, return terse
Write each NON-EMPTY list (skip empty ones) to
`/Users/baird/Dropbox/_git_ALL/_github-repos-gem/lng-terminals-researcher/batches/staging/<REGION>/<slug>.<type>.json`
where `<REGION>` is given in your task prompt (e.g. `europe`) and slug = lowercase country (e.g.
`germany`; for a country with spaces use a hyphen, e.g. `united-kingdom`). `mkdir -p` the region dir
first. Types: `updates`, `qa`, `wiki`, `entity`, `monitor`, `newterminals`, `newunits`. Each file is
a JSON list. Use `json.dump(..., ensure_ascii=False, indent=2)`.

Record schemas (keys EXACT):
- updates: {terminal_id,unit_id,terminal_name,unit_name,country,field_name(exact GEM header),old_value,new_value,confidence,source_tier,ref_field,ref_urls:[..],source_notes,scope_note,researcher_initials:"AI-draft (sweep)"}
- qa: {category,terminal_id,unit_id,terminal_name,issue,severity:"high|medium|low",suggested_action,researcher_initials:"AI-draft"}
- wiki: {country,terminal_id,terminal_name,unit_id,topic,wiki_text,verification_status:"[CONFIRMED]|[UNVERIFIED — SINGLE SOURCE]|[CONFLICTING DATA]|[NOT FOUND]",source_urls:[..],researcher_initials:"AI-draft"}
- entity: {entity_name,entity_type,country_of_hq,parent_entity,rationale_for_new_entity,lookup_was_run,lookup_result_summary,referenced_by_terminals,referenced_by_units,researcher_initials:"AI-draft"}
- monitor: {country,candidate_name,sponsor_or_proposer,first_observed_batch:"2026-06 sweep",last_observed_batch:"2026-06 sweep",current_state,missing_threshold_elements,watch_for,best_lead_url,notes}
- new_terminals / new_units: keys = exact GEM headers (read `build_new_terminals_sheet` ~L657 and `build_new_units_sheet` ~L699 in `scripts/build_review_package.py`); fill only sourced fields; optional `confidence_per_field` {Header:color}.

RETURN ONLY a terse summary (≤12 lines): country; #terminals reviewed; #updates (by color); #qa; #wiki; #monitor;
#new; escalation (true/false); 1-line headline; blockers. Do NOT paste the records.
