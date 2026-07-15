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
- `python /Users/baird/Dropbox/_git_ALL/_github-repos-gem/lng-terminals-researcher/scripts/dedup_index.py match <candidates.json>`
  scores your leads against GEM (name + `OtherNames` similarity, haversine location distance, capacity ratio, and the
  cancelled/shelved + new-proposal "dead-and-revived" case) and returns a `recommended_route` per candidate:
  `update_existing` (already in GEM — NOT a discovery; note in qa), `update_dead_and_revived` (a proposal at the site
  of a cancelled/shelved GEM record — DECIDE by hand, see the dead-and-revived rule below; it may be a NEW terminal),
  `manual_review` (judge by hand), `discovery_new` (genuine gap — proceed). The matcher is a GATE, not an oracle: it
  scores name/location/capacity but cannot see sponsor or design, so its `update_dead_and_revived` verdict is a prompt
  to decide, not an instruction to skip. Candidate JSON fields: `country, name, sponsor, latitude, longitude,
  capacity_mtpa, status`.

## Method (per country)
1. Enumerate GEM's existing terminals for the country — and SEPARATELY list the ones GEM holds as `cancelled`
   or `shelved` (a dead SITE). These are a discovery blind spot: nothing in the routine workflow circles back to
   ask "did a NEW project rise at this dead site?" Get the list from `completeness_sweep.py`'s
   `dormant_revival_watch` block (or just filter your country's GEM rows to Status cancelled/shelved), and
   **web-search each dead site for new activity** — a new sponsor, a new FSRU/FSU charter, a new permit/state
   approval, a renamed project. Treat any hit as a candidate and run it through step 3's dead-and-revived
   decision (different sponsor/design at a dead site = a NEW terminal). This is exactly how the "POIC Lahad Datu"
   FSU terminal — a 2026 project on the site of the 2016-cancelled "Lahad Datu Sabah LNG Terminal" — was missed.
   ALSO reconcile **gem.wiki coverage** against the CSV: a terminal can have a gem.wiki page but NO export-CSV row,
   which makes it invisible to BOTH dedup (no row to match) AND web search (gem.wiki is excluded as a source, so
   GEM's own page never enters your candidate pool). Enumerate your country's gem.wiki LNG-terminal pages (LNG
   Terminals category / country listing / site search) and list any with no matching CSV row — each is a discovery
   candidate. A gem.wiki page does NOT mean the project is in the tracker. (This is how the "Durban LNG Terminal" —
   gem.wiki page, no export row — was missed.)
2. SEARCH for terminals NOT in that list, three ways (use WebSearch/WebFetch; load via ToolSearch if needed):
   a. Regulator / govt / port-authority / EIA-equivalent; EU-PCI-style lists; tender & licensing announcements.
   b. Trade press — LNG Prime, Reuters, S&P Global, Argus, Upstream, Riviera, + local-language outlets.
      Queries like `"<country>" LNG (terminal|FSRU|import|export|regasification) (proposed|announced|MOU|FID) <year>`.
   c. Sponsor IR — LNG developers active in the country, AND (do NOT skip in a hydrocarbon producer) the
      upstream OIL operators monetizing associated gas. In coastal oil/gas producers the real FLNG sponsors are
      field operators (Trident Energy, Perenco, Eni, Wing Wah, Panoro, VAALCO, BW Energy, Kosmos, Savannah + the
      NOC), NOT the "established LNG developer" list. Run an associated-gas / gas-monetization / flaring-reduction
      sweep over the country's field operators; a national Gas Code / Gas Master Plan / flaring-reduction push is
      the tell that an FLNG is coming. (This is how the "Trident Energy Congo FLNG" was missed.)
   d. ALSO sweep these (often the EARLIEST signal, esp. for emerging-market & floating terminals):
      - Development-bank / DFI pipelines (World Bank/IFC, AfDB, ADB, EBRD) — they fund import terminals before any sponsor IR.
      - National gas master-plans / power IRPs (energy-ministry strategy docs) — forward signal of planned terminals.
      - FSRU/FLNG newbuild & conversion ORDERBOOKS (class societies DNV/ABS/LR; shipyards) + any FSRU reported
        chartered/deployed to your country: a built/chartered floating unit implies a terminal — check it has a GEM terminal; if not, it's a lead.
      - Local-language press (search in the country's own language, not just English).
   Prioritize the last 24 months, but include any not-yet-in-GEM project regardless of age.
   ANTI-CIRCULARITY (ABSOLUTE — CLAUDE.md hard requirement): NEVER cite gem.wiki or globalenergymonitor.org as a
   source/URL anywhere (best_lead_url, source_urls, qa prose) — it is GEM's own publication, so it is circular and
   forbidden. A source that derives from or republishes GEM (IEEFA/Wikipedia/news footnoting GEM) is likewise NOT
   independent evidence — chase the primary source it points to and cite THAT. If a candidate's only trace is on
   gem.wiki, it is already a GEM record — not a discovery.
3. DEDUP every candidate against GEM: run `dedup_index.py match <candidates.json>` (above) for the
   name/location/capacity + dead-and-revived scoring, plus a grep + alias/local/diacritic eyeball check it can't
   catch. GEM coverage is comprehensive, so MOST candidates are already in GEM → `update_existing` is NOT a
   discovery (note briefly in qa, move on). `update_dead_and_revived` (a proposal at the site of a cancelled/shelved
   GEM record) needs a HAND DECISION per the dead-and-revived rule (`docs/reference/lifecycle_rules.md`):
   - SAME fundamentals (same sponsor, same site, same basic design) → a true revival → route to Update (timeline
     entry), NOT a new_terminal.
   - SIGNIFICANTLY DIFFERENT (different sponsor and/or different design — e.g. an FSU/FSRU replacing a cancelled
     onshore terminal, or a 5+-year-dead record) → a genuinely NEW project → STAGE AS A NEW TERMINAL, with
     `AssociatedTerminals` = the dead record's TerminalID (which stays cancelled). Do not let the matcher's
     `update_dead_and_revived` label talk you out of a real discovery.
   Only `discovery_new` (and these new-project revivals) proceed; judge `manual_review` by hand.
4. For a GENUINE gap — apply the SCOPE GATE first, then the threshold:
   - SCOPE GATE (before the threshold): the candidate must move LNG across a border BY SHIP — `import` (marine LNG
     in) or `export`/liquefaction (marine LNG out). A domestic-only plant — virtual pipeline, LNG-by-truck,
     peak-shaving, no marine import/export — is OUT OF SCOPE: drop it (or a brief qa note), never a `new_terminal`.
     RESOLVE scope doubt BEFORE staging; if you're about to write "reviewer may prefer a small-scale/peak-shaving
     classification," that hedge IS the signal to resolve the scope question first, not to stage and defer. (This is
     how the domestic-only "Dar es Salaam Small-Scale LNG Terminal" was wrongly staged as `export`.)
   - In scope AND meets the bar (sponsor identified + approximate location + a concrete step taken) AND you have a
     VERIFIED source → stage a `new_terminal` (+ `new_units`).
   - In scope but below the bar (vague/rumored/pre-sponsor) → `monitor_list`.
5. VERIFY every URL (`url_verifier.py "<url>" "<token>"`; PDF → `curl -sL <url> -o /tmp/x.pdf && pdftotext -layout /tmp/x.pdf - | grep -i <token>`).
   Pass the actual claimed datum as the token (sponsor/location/capacity/status), not a generic word — the value must be
   explicitly on the page. Cite only verified URLs, and give ≥2 INDEPENDENT corroborating URLs per staged candidate (3
   when findable) — a single source is the disfavored exception (→ monitor_list, not a confident new_terminal).

## HARD RULES
- SCOPE GATE before the threshold — a `new_terminal` must move LNG across a border by ship (import/export);
  domestic-only virtual-pipeline / trucking / peak-shaving plants are OUT OF SCOPE. Resolve scope doubt before
  staging — never stage-with-doubt (a "reviewer may prefer…" hedge = resolve first).
- gem.wiki COVERAGE cross-check — reconcile your country's gem.wiki LNG pages against the CSV; a wiki page with no
  export row is a discovery candidate (gem.wiki detects the gap, is NEVER a citation — chase independent sources).
- SWEEP UPSTREAM OIL OPERATORS in hydrocarbon producers — associated-gas/flaring-reduction sweep over field
  operators, not just established LNG developers (the FLNG-sponsor blind spot).
- >5 genuine new candidates in ONE country → stage as `monitor_list` + set escalation=true in your summary;
  do NOT mass-generate `new_terminal` records (CLAUDE.md trigger).
- `new_terminals`/`new_units` keys = exact GEM headers (read `build_new_terminals_sheet` ~L657 and
  `build_new_units_sheet` ~L699 in `scripts/build_review_package.py`); fill only sourced fields; NEVER
  read-only cols (LH2/NH3/SyntheticLNG/RetrofitProposed/AltFuel*/PCI*/CCS/computed totals/Wiki/TerminalID/UnitID);
  capacity baseload/nameplate; optional `confidence_per_field` {Header:color}.
- `entity_lookup.py "<name>" --remote` (run BARE — do NOT pass `--country`) before naming any new
  owner/operator/parent. Entities are SHARED across countries: the developer of your country's project very
  often already exists on a GEM terminal in ANOTHER country, and a `--country` filter would hide that and make
  you stage a DUPLICATE (this exact bug staged "LNG Alliance" as new when it already existed on an India
  terminal). A match ANYWHERE = reuse the existing entity, do NOT add it to `entity`. `--country` only annotates;
  the script now emits a `cross_country_warning` rather than hiding a match, but run bare regardless.
  `lookup_was_run` records that BOTH the bare-local and `--remote` checks ran. CAVEAT: the `--remote` endpoint
  has intermittent FALSE NEGATIVES — treat `no_remote_match` as a lead, not proof of absence; record the exact
  lookup output in `lookup_result_summary` (the orchestrator re-checks every proposed new entity against the
  read-only Postgres `entity_history` before building and drops duplicates).
- Conservative: a candidate you can't verify or confidently distinguish from an existing GEM record →
  qa/monitor, never a fabricated new_terminal.

## OUTPUT — write files, return terse
Write to `/Users/baird/Dropbox/_git_ALL/_github-repos-gem/lng-terminals-researcher/batches/staging/<REGION>/<slug>.<type>.json`
(REGION given in your prompt; `mkdir -p` first; slug = lowercase country, hyphens for spaces). Types you'll
mostly produce: `newterminals`, `newunits`, `monitor`, `entity`, `qa`, `wiki`. Schemas:
- new_terminals / new_units: keys = exact GEM headers (see above).
- monitor: {country, candidate_name, sponsor_or_proposer, first_observed_batch:"<YYYY-MM> discovery" (the
  CURRENT batch month), last_observed_batch:same, current_state, missing_threshold_elements, watch_for, best_lead_url, notes}
- qa: {category, terminal_id, unit_id, terminal_name, issue, severity:"high|medium|low", suggested_action, researcher_initials:"AI-draft"}
- wiki: {country, terminal_id, terminal_name, unit_id, topic, wiki_text, verification_status, source_urls:[..], researcher_initials:"AI-draft"}
- entity: {entity_name, entity_type, country_of_hq, parent_entity, rationale_for_new_entity, lookup_was_run, lookup_result_summary, referenced_by_terminals, referenced_by_units, researcher_initials:"AI-draft"}
researcher_initials = "AI-draft (discovery sweep)". Each file is a JSON list; `json.dump(..., ensure_ascii=False, indent=2)`.

SWEEP-MODE SLUG: when an update agent may run concurrently for the same country (combined sweeps),
your file slug is `<slug>.disc` — write `<slug>.disc.<type>.json` (e.g. `germany.disc.monitor.json`)
so the two agents never collide on shared types (qa/wiki/entity). `_assemble.py`'s `*.<type>.json`
globs still match the infix. AFTER all finding files, ALWAYS write `<slug>.disc.done.json` LAST —
even when empty-handed: `{"slug": ..., "country": ..., "mode": "discovery", "summary":
{"candidates_examined": N, "new_terminals": N, "monitor": N, "escalation": false}}`. Its presence is
the orchestrator's resume marker.
RETURN ONLY a terse summary (≤12 lines): country; #existing GEM terminals; #candidates examined; #already-in-GEM;
#new_terminals staged; #monitor; escalation (true/false); 1-line headline; blockers.
