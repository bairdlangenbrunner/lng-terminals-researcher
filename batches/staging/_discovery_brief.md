# Country LNG DISCOVERY — subagent brief

You run a PROPER discovery sweep for your assigned country/countries: actively HUNT for LNG
terminals/projects MISSING from GEM (not just dedup the known ones). Output is STAGED candidates a
human reviews; never touch the live DB. Leads are not pre-trusted; verify.

## First read (repo SOPs)
- `docs/sops/discovery.md` — the discovery workflow (§4 country-regulator sweep, §5 trade-press sweep,
  §6 sponsor-IR sweep, and the "sufficient information to add" threshold).
- `docs/reference/source_roster.md` (source tiers) and `docs/country_notes/<country>.md` if it exists
  (regulator URLs, local-language tips, gotchas).

## Inputs
- GEM export: `/Users/baird/Dropbox/_git_ALL/_github-repos-gem/lng-terminals-researcher/scripts/gem_export.csv`
  (open `utf-8-sig`; country col `Country/Area`). FIRST list the country's EXISTING GEM terminals so you
  know what's already covered.
- `python /Users/baird/Dropbox/_git_ALL/_github-repos-gem/lng-terminals-researcher/scripts/dedup_index.py`
  to check candidates against existing project/unit indexes (catches alias/local-name matches).

## Method (per country)
1. Enumerate GEM's existing terminals for the country.
2. SEARCH for terminals NOT in that list, three ways (use WebSearch/WebFetch; load via ToolSearch if needed):
   a. Regulator / govt / port-authority / EIA-equivalent; EU-PCI-style lists; tender & licensing announcements.
   b. Trade press — LNG Prime, Reuters, S&P Global, Argus, Upstream, Riviera, + local-language outlets.
      Queries like `"<country>" LNG (terminal|FSRU|import|export|regasification) (proposed|announced|MOU|FID) <year>`.
   c. Sponsor IR — LNG developers active in the country.
   d. ALSO sweep these (often the EARLIEST signal, esp. for emerging-market & floating terminals):
      - Development-bank / DFI pipelines (World Bank/IFC, AfDB, ADB, EBRD) — they fund import terminals before any sponsor IR.
      - National gas master-plans / power IRPs (energy-ministry strategy docs) — forward signal of planned terminals.
      - FSRU/FLNG newbuild & conversion ORDERBOOKS (class societies DNV/ABS/LR; shipyards) + any FSRU reported
        chartered/deployed to your country: a built/chartered floating unit implies a terminal — check it has a GEM terminal; if not, it's a lead.
      - Local-language press (search in the country's own language, not just English).
   Prioritize the last 24 months, but include any not-yet-in-GEM project regardless of age.
   ANTI-CIRCULARITY: a source that derives from or cites GEM (GEM.wiki; IEEFA/Wikipedia/news footnoting GEM) does
   NOT count as independent evidence for adding/verifying a terminal — find the primary source it points to.
3. DEDUP every candidate against GEM (grep + dedup_index + alias/local/diacritic check). GEM coverage is
   comprehensive, so MOST candidates are already in GEM → those are NOT discoveries; note briefly in qa, move on.
4. For a GENUINE gap:
   - Meets the bar (sponsor identified + approximate location + a concrete step taken) AND you have a VERIFIED
     source → stage a `new_terminal` (+ `new_units`).
   - Below the bar (vague/rumored/pre-sponsor) → `monitor_list`.
5. VERIFY every URL (`url_verifier.py "<url>" "<token>"`; PDF → `curl -sL <url> -o /tmp/x.pdf && pdftotext -layout /tmp/x.pdf - | grep -i <token>`). Cite only verified URLs.

## HARD RULES
- >5 genuine new candidates in ONE country → stage as `monitor_list` + set escalation=true in your summary;
  do NOT mass-generate `new_terminal` records (CLAUDE.md trigger).
- `new_terminals`/`new_units` keys = exact GEM headers (read `build_new_terminals_sheet` ~L657 and
  `build_new_units_sheet` ~L699 in `scripts/build_review_package.py`); fill only sourced fields; NEVER
  read-only cols (LH2/NH3/SyntheticLNG/RetrofitProposed/AltFuel*/PCI*/CCS/computed totals/Wiki/TerminalID/UnitID);
  capacity baseload/nameplate; optional `confidence_per_field` {Header:color}.
- `entity_lookup.py "<name>" --country "<C>" --remote` before naming any new owner/operator/parent
  (lookup_was_run starts "RUN" if inconclusive).
- Conservative: a candidate you can't verify or confidently distinguish from an existing GEM record →
  qa/monitor, never a fabricated new_terminal.

## OUTPUT — write files, return terse
Write to `/Users/baird/Dropbox/_git_ALL/_github-repos-gem/lng-terminals-researcher/batches/staging/<REGION>/<slug>.<type>.json`
(REGION given in your prompt; `mkdir -p` first; slug = lowercase country, hyphens for spaces). Types you'll
mostly produce: `newterminals`, `newunits`, `monitor`, `entity`, `qa`, `wiki`. Schemas:
- new_terminals / new_units: keys = exact GEM headers (see above).
- monitor: {country, candidate_name, sponsor_or_proposer, first_observed_batch:"2026-06 discovery",
  last_observed_batch:"2026-06 discovery", current_state, missing_threshold_elements, watch_for, best_lead_url, notes}
- qa: {category, terminal_id, unit_id, terminal_name, issue, severity:"high|medium|low", suggested_action, researcher_initials:"AI-draft"}
- wiki: {country, terminal_id, terminal_name, unit_id, topic, wiki_text, verification_status, source_urls:[..], researcher_initials:"AI-draft"}
- entity: {entity_name, entity_type, country_of_hq, parent_entity, rationale_for_new_entity, lookup_was_run, lookup_result_summary, referenced_by_terminals, referenced_by_units, researcher_initials:"AI-draft"}
researcher_initials = "AI-draft (discovery sweep)". Each file is a JSON list; `json.dump(..., ensure_ascii=False, indent=2)`.
RETURN ONLY a terse summary (≤12 lines): country; #existing GEM terminals; #candidates examined; #already-in-GEM;
#new_terminals staged; #monitor; escalation (true/false); 1-line headline; blockers.
