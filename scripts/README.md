# Scripts

All scripts are standalone (no install step). Each has a `--help` and a
top-of-file docstring.

## Typical invocation order in a batch

```
# 1. Always start with a fresh pull (no cookies needed for the all-fields path)
python gem_all_fields.py -o gem_export.csv
python pull_gem_db.py --map-only --out gem_export.csv   # derive the .colmap.json

# 2. Build the matching indexes
python dedup_index.py

# 3. Run any triage/discovery/update/reconciliation-specific scripts:
python stale_sweep.py                                       # for triage or update
python giignl_extract.py <report.pdf> --output giignl_extracted.csv --year 2026   # recon phase 1
python report_diff.py --report giignl --extracted giignl_extracted.csv \
    --gem-csv gem_export.csv --output report_diff.json      # recon phase 2
python fsru_sync_check.py                                    # if batch touches FSRUs

# 4. Build the xlsx
python build_review_package.py --mode update --output ../batches/...

# 5. Verify no formula errors
python recalc.py ../batches/...
```

## Script-by-script

### Data acquisition

| Script | Purpose |
|---|---|
| `gem_query.py` | Queries the GEM read-only Postgres database directly and exports to CSV. Lowest-level acquisition tool. |
| `gem_all_fields.py` | Reproduces the website's "all-fields" LNG terminal CSV. **No cookies needed** — preferred fresh-pull path. |
| `gem_export_via_web.py` | Downloads the all-fields CSV from the running GEM website. Cookie-based (auth from `.env`). |
| `pull_gem_db.py` | Wraps a data-pull and derives the 115-column index map, writing `.colmap.json` next to the CSV. Use `--map-only` to derive the colmap from an existing CSV without re-pulling. |
| `fetch_timeline.py` | Pulls the full status timeline for a single UnitID from the live DB web UI. Required before any status timeline edit — the CSV export doesn't include timeline data. **Parser is heuristic — verify against the live UI for at least one unit per batch.** |
| `giignl_extract.py` | Parses the GIIGNL annual-report PDF into a flat CSV with GEM-aligned columns. Uses `pdftotext -layout` + column-position row partitioning; per-country capacity subtotals act as block-boundary budgets. (The 2026 edition is a real PDF v1.7 with a clean text layer. The legacy zip-of-JPEGs + OCR vision pipeline lives in git history if a future edition reverts.) |

### Normalization and validation

| Script | Purpose |
|---|---|
| `normalize.py` | Canonical names for countries, entities (owners/operators), capacity units, and terminal names. Also transliterates non-Latin names (e.g. Chinese `LocalNames`) to English via jieba + pypinyin for cross-script alias matching. Import as a library; CLI runs smoke tests. |
| `capacity_normalize.py` | mtpa/bcm/y conversion, range parsing (records max per methodology). |
| `status_timeline.py` | Validates legal state transitions, anchor year invariants, current-status derivation. Used by build_review_package.py. |

### Search and dedup

| Script | Purpose |
|---|---|
| `dedup_index.py` | Builds project/sponsor-country/unit indexes from the GEM CSV. Used by discovery batches to check if a candidate already exists. |
| `entity_lookup.py` | Searches local CSV (and optionally remote entity system) for an entity name. Run before staging any new entity. |
| `url_verifier.py` | HTTP 200 + content check + soft-error detection. Every cited URL must pass before being staged. |
| `imo_tracker.py` | Look up FSRU/FLNG vessel IMO via marinetraffic.org. |

### Workflow-specific

| Script | Purpose |
|---|---|
| `stale_sweep.py` | Flags units exceeding lifecycle dormancy thresholds. Used by triage and stale-driven update batches. |
| `report_diff.py` | Reconciliation diff between an industry report (GIIGNL or IGU) and current GEM data. Parameterized on report type. Three-pass matching (canonical name → alias via `OtherNames`/`LocalNames` + transliterations → fuzzy); project key includes `section_type` so a mixed liquefaction+regasification terminal splits into two projects rather than summing. Report rows ending in "Expansion"/"Extension" fold into their base `<Site>` row (when a base partner resolves) so phased terminals sum correctly; the `report_sites_merged` field records each fold. Set iterations are sorted, so the diff is reproducible run-to-run. |
| `fsru_sync_check.py` | Cross-checks FSRU records between the LNG Terminals project and the LNG Carrier Tracker project. Graceful degradation if carrier backend unavailable. |

### Output

| Script | Purpose |
|---|---|
| `build_review_package.py` | Assembles the batch xlsx from staged JSON inputs. Three modes: `update`, `discovery`, `reconciliation`. Respects read-only column list. |
| `recalc.py` | Final formula-error check on generated xlsx before presenting to user. |

## Data-acquisition paths

There are three ways to pull the GEM CSV, in increasing reliance on auth:

- `gem_all_fields.py` — reproduces the website's all-fields export with **no cookies**. Preferred default.
- `gem_query.py` — hits the read-only Postgres DB directly.
- `gem_export_via_web.py` — downloads from the live website using auth cookies from `.env`.

All three are committed to the repo (no longer user-supplied). `pull_gem_db.py`
wraps a pull and derives the column-index map; run it with `--map-only` to derive
the colmap from a CSV you already pulled.

## Inter-script dependencies

```
normalize.py           ← imported by most others
url_verifier.py        ← imported by build_review_package
capacity_normalize.py  ← imported by build_review_package
status_timeline.py     ← imported by build_review_package
dedup_index.py         ← reads pull_gem_db output (.colmap.json)
stale_sweep.py         ← reads pull_gem_db output
report_diff.py         ← reads pull_gem_db output + giignl_extract output
fsru_sync_check.py     ← reads pull_gem_db output + optional carrier CSV
build_review_package.py ← reads all *.json staged outputs
recalc.py              ← reads build_review_package xlsx output
```

The simplest pattern (`sys.path.insert(0, str(Path(__file__).parent))` at the
top of each script) means scripts can import each other without any install
step. Don't refactor into a package unless you have a specific reason.

## Deep-dive: GIIGNL reconciliation internals

The two most intricate scripts in the reconciliation pipeline (`giignl_extract.py` and `report_diff.py`) carry a large catalog of edge-case fixes, each guarding against a specific real-world failure observed in the GIIGNL editions. CLAUDE.md keeps only one-line summaries to stay lean; the full rationale lives here. **Read the relevant block below before editing either script** — most of these look like over-engineering until you hit the exact PDF layout they defend against.

### `giignl_extract.py` — GIIGNL PDF parsing

Parses GIIGNL report into a flat CSV with GEM-aligned columns. 2026 edition is a real PDF v1.7 with a clean text layer — uses `pdftotext -layout` + column-position-based row partitioning; per-country capacity subtotals are used as block-boundary budgets so rows route to the right country even when labels appear mid-block. GIIGNL vertically *centers* each country label+subtotal within its block, so rows above the label inherit the previous country; a post-pass (`_truecup_country_subtotals`) reclaims them by *tentatively* pulling rows from the **single immediately-preceding country** and committing only if the run then reaches the country's published subtotal (within a 6%/2% reach band). This catches the case the running budget misses (the previous country's block spilled over from an earlier page so its page-local cumulative never reaches its subtotal — e.g. Brunei T1/T2 inherited Australia, whose 85.8 MTPA block began on the prior page) WITHOUT the failure mode of an earlier naive version: a multi-page country like China regas (264 MTPA, pages 55–57) looks "short" on each page and would otherwise swallow the whole USA+Bangladesh blocks above it to reach its subtotal. The two guards — never pull through more than one preceding country, and commit only on reaching the subtotal — keep it to genuine centered-label misattributions (Brunei, Ain-Sokhna, Damietta, Moheshkhali, Brazilian/Malaysian/German/UK terminals, etc.). The standalone page footer ("<page#> - GIIGNL Annual Report <year> Edition") is skipped during line classification (`_PAGE_FOOTER_RE`) — otherwise the line-merge pass folds it into the last data row of the page and the column slicer splits it across cells (e.g. "Annual" → country "… GIIGNL An" + site "nual Report 2026 Edition"), corrupting that row AND poisoning the country walk for the rest of the page (this had silently dropped QatarEnergy LNG S(2) T4 and mis-countried Ruwais/San Juan/Yamal T1/etc.). **Embedded label/subtotal-on-a-data-row + cross-page blocks (QatarEnergy fix):** GIIGNL also centers a country label+subtotal directly ONTO a data row's physical lines — Qatar's "77.0 MTPA" + "N(3) T6" sit on the N(3) T6 row. A subtotal line is now recorded but NOT skipped when its name column (col 1) carries a fragment, so the trailing train code isn't lost (this had degraded N(3) T6 / S(3) T6 to a bare "QatarEnergy LNG"; the same fix also recovers regas terminal names previously eaten by such lines — Jamaica "Old Harbour", Croatia "Krk expansion", Türkiye "Saros LNG", Ravenna's "BW Singapore" vessel). Because the centered label makes rows ABOVE it inherit the previous country and the per-page `_truecup_country_subtotals` can't repair a block that spans pages (Qatar liq spans 34-35 so neither page reaches 77.0; N(1)/N(2) stranded on Oman, Oman T1 on USA), a section-wide `_reclaim_cross_page` re-runs the reclaim over ALL pages' rows in report order, iterated to a fixpoint (Qatar pulls N(1)/N(2) from Oman → Oman then pulls Oman T1 from USA), choosing the pull count CLOSEST to the subtotal — not merely within band, else Indonesia (24.9) swallows Canada's Tilbury LNG (0.3). It keys off `_robust_subtotal_map` (each subtotal → its NEAREST data row's country, since the sequential walk otherwise mis-files Oman's 11.4 under USA). Zero-width chars are stripped (`_clean_text` + normalize) so "S(2 )" yields designator token "s(2". A regas FSRU row whose EVERY site fragment carries an (FSRU)/(FSU) tag (site "Ravenna (FSRU)" + vessel "BW Singapore (FSRU)") takes the first fragment as site, last as vessel (trailing "and" stripped for dual-FSU rows like Malaysia "Tenaga Empat … and Tenaga Satu"). **Row partitioning by name-start (APLNG/Darwin/Prelude fix):** lines are assigned to the NEAREST data line, NOT split at the midpoint between data lines (the midpoint absorbed a row's leading name into the row ABOVE when a site name spans multiple physical lines). A distance TIE is resolved by content: a capitalized name-START fragment (no capacity, opening/balanced parens, not "Expansion"/"Extension", no FSRU/FLNG tag) is the LEADING name of the row BELOW; a continuation (lowercase, dangling close-paren like "…Ahmeyim Phase 1)", a bare "Expansion", or a facility-tagged vessel like "Italis LNG (FSRU)") stays with the row ABOVE. This un-fuses "APLNG T2" from "Darwin LNG (new" (so APLNG T1+T2 group → 9.0), recovers "Darwin LNG (new supply source Barossa project)", Croatia "Krk" (main row, fixing the earlier fragmentation), "Piombino"/"Panigaglia", and un-merges cross-terminal bleeds (Al Zour+Dakar, Zeebrugge+Krk). A facility tag in PARENTHESES — "(FLNG)"/"(FSRU)" — is NOT stripped as a status hint (it's part of the name: "Prelude (FLNG)", "PFLNG Dua (FLNG)"); `normalize_terminal_name` drops a trailing parenthetical facility tag for MATCHING only ("prelude (flng)"→"prelude" exact-matches GEM "Prelude FLNG Terminal"), keeping the tag in the displayed site_name. **Non-operating status hint → `status` column (Bontang/Balhaf fix):** GIIGNL's liq/regas tables are operating-only, but a few rows are annotated as not-currently-operating with a status parenthetical — "Bontang Train E (Mothballed)", "Balhaf T1/T2 (stopped)", "Atlantic LNG T1 (Mothballed)". `_strip_train_suffix` already peels such a parenthetical off the liq name; `_status_from_hint` now maps the peeled word to a canonical GEM non-op status (`_NONOP_STATUS_HINTS`: mothballed→mothballed, stopped/idle/suspended→idled, retired/decommissioned→retired, …) written to a new LAST CSV column `status` (regas peels its own trailing status paren via `_STATUS_HINT_RE`, since facility-tag stripping leaves a "(Mothballed)" in the site name). An UNRECOGNIZED hint maps to "" (row stays operating, raw hint kept only in notes — we don't guess). report_diff then EXCLUDES a status-bearing row from the operating total. NB: facility tags "(FLNG)/(FSRU)/(FSU)/(FRU)/(FPSO)" are explicitly NOT status hints (kept as part of the name). Earlier editions shipped as zip-of-JPEGs + OCR; that pipeline lives in git history if a future edition reverts

**Read / revisit the source when:** New GIIGNL edition layout changes column positions; new country added to super-region marker list; subtotal detection misfires; true-up over/under-pulls (diff per-country row sums against subtotals across ALL pages, not one page, and watch for cross-country pulls); footer/header text bleeds into a row (re-check `_PAGE_FOOTER_RE`); a multi-line site name is split across two rows or fused with a neighbour (check the nearest-data-line tie-break in `_partition_lines_by_data` — the name-start vs continuation classification); a GIIGNL status parenthetical ("(Mothballed)"/"(stopped)") isn't recognized as non-op (extend `_NONOP_STATUS_HINTS`) or a facility tag is wrongly eaten as a status (check the `_strip_train_suffix` exclusion list)

### `report_diff.py` — alias / project matching

Project key includes `section_type` so a single GEM terminal with both liquefaction and regasification (e.g. Sabine Pass: 6 export trains + 1 import terminal) splits into two distinct projects, not one summed entry. Alias map includes GEM `OtherNames` + `LocalNames`, with CJK transliteration via jieba + pypinyin (e.g. `中石油唐山曹妃甸LNG接收站` → `zhong shiyou tangshan caofeidian lng jieshouzhan` so distinctive city tokens can match). **Row-folding (report side):** rows ending in "Expansion"/"Extension" fold into the base "<Site>" row, AND per-complex unit-code rows ("Arzew GL1Z/2Z/3Z") fold into "Arzew" (`_strip_unit_code_suffix`: trailing letters+digits token), AND explicit per-train rows ("Bontang Train E/F/G/H") fold into "Bontang" (`_strip_train_word_suffix`: trailing literal word "Train"/"Trains" + a 1-2 char code/roman numeral) — all conservative, firing only when the base resolves (a GEM key/alias, another report row, or ≥2 report peers sharing the base), so bare "expansion" artifacts are left alone. The unit-code fold deliberately ignores single-letter codes (else it eats "Senboku II"); the train-word fold needs the literal word "Train", which is what makes "Bontang Train E"→"Bontang" safe while "Corpus Christi Stage III" / "Senboku II" are left alone. **Same-name-by-owner families:** GEM disambiguates multiple distinct terminals that share a base name with a trailing first-owner parenthetical — "Tianjin LNG Terminal (PipeChina)" / "(Sinopec)" / "(Beijing Gas Group)" (common for Chinese terminals; also Salina Cruz, QatarEnergy LNG (N)/(S)). When ≥2 GEM terminals in a country+section share a base name, the parenthetical is treated as an OWNER tag, not a name token: it's added to `owners_set` and the fuzzy match-tokens are built from the base name only (so the owner word "sinopec" doesn't drag in Liuheng/Longkou (Sinopec)). Fuzzy matching strips the report-side parenthetical too, and a tie-break prefers the candidate whose GEM parenthetical owner equals the GIIGNL row's first owner. **FSRU-vs-onshore same-port split (`_FLOAT_VARIANT_SUFFIX`, `collision_regas`):** at a regas port GEM may track BOTH a floating terminal and an onshore one under names that normalize identically — `normalize_terminal_name` strips both " FSRU" and " LNG Terminal", so "Ravenna FSRU" + "Ravenna LNG Terminal" both → "ravenna" (≈12 ports: Ravenna, Stade, Hazira, Payra, Summit Matarbari, Dongying, Yantai, Paldiski, Brunsbüttel, Wilhelmshaven TES, Haldia, FGEN Batangas). A pre-scan flags such ports (a regas (country,name) with BOTH a floating and a non-floating GEM terminal); the FLOATING member is keyed under a " fsru" name suffix on the GEM side, and a vessel-bearing GIIGNL row at that port (`_report_row_is_floating`) gets the same suffix — so onshore↔onshore and FSRU↔FSRU match instead of collapsing into one merged project (this had wrongly combined GIIGNL's onshore Ravenna 0.7 + Ravenna FSRU 3.7 into a single 4.4-vs-0.7 entry). Restricted to regasification (a report row's floating-ness is undeterminable for GIIGNL liquefaction, so liq FLNG/onshore pairs — Cameroon, Rovuma — are left merged). The suffix is non-parenthetical so it doesn't trip the family logic above

**Read / revisit the source when:** New non-Latin language in LocalNames; matching needs more script support; fold over/under-merges (check `report_sites_merged`); same-name family matched to wrong sibling (check parenthetical-owner vs GIIGNL first owner); an FSRU/onshore same-port pair merges or mis-routes (check `collision_regas` membership + `_report_row_is_floating` — needs the GIIGNL row to carry a vessel/FSRU type)

### `report_diff.py` — unit-level alignment

`_align_units`: within a matched project, aligns each GIIGNL row to a specific GEM unit when the GEM unit name is a token of the GIIGNL site name (GIIGNL "Arzew GL1Z" ⊃ GEM unit "GL1Z") + capacity corroboration → `match_granularity="unit"` with a `unit_matches` list; falls back to project-total (operating-only) when GIIGNL rows don't map to GEM unit names (Taichung). **Sub-terminal designator → GEM unit (Pass 1.5, `_unit_designators`):** GIIGNL splits a complex into sub-terminals, each its own report project ("QatarEnergy LNG S(1)/S(2)/S(3)"), while GEM splits the SAME complex into one terminal with train-range units ("QatarEnergy LNG (S)" → units "S(1) T1-2"/"S(2) T3-5"/"S(3) T6-7") — a many-report-projects-to-one-GEM-terminal shape `_align_units` can't reach (GEM unit tokens {s(2,t3,5} ⊄ report site {qatarenergy,lng,s(2}), and the plain project matcher would wrongly compare each sub-terminal against the WHOLE terminal (the bogus S(2)=14.1 vs (S)=36.3 "61% conflict"). A report project carrying a parenthesized-digit designator (S(2)→"s2") that identifies exactly ONE GEM unit within a SINGLE GEM terminal in the same country+section is matched to that UNIT (`match_type="unit_designator"`, compared at unit level: S(2) 14.1 vs unit 14.1), gated on a 4+ name-token or owner overlap. The designator inherently routes n*→(N), s*→(S), so it ALSO disambiguates GEM's same-base-name siblings without the parenthetical-owner heuristic. **GEM owner parsing** now uses `parse_entity_list` (same as the report side) instead of a comma-only split: GEM cells are ";"-separated with "[NN%]" brackets ("QatarEnergy [70%]; Exxon Mobil Corp [30%]"), and the old split collapsed every multi-owner cell to a single (often wrong) tag, manufacturing false owner conflicts on nearly every match (`parse_entity_list`'s %-regex now also accepts "[…]" brackets; "qatar energy" added to the entity map). **Project-spanning guard:** a unit is accepted only if the GIIGNL row's capacity is at least as close to that unit as to the project total — stops a whole-terminal GIIGNL row from being pinned to one unit via a coincidental code token (GIIGNL "Portovaya LNG T1 (+ FSU)" = 1.5 = the whole terminal would otherwise emit a spurious unit-level 100% conflict against GEM unit "T1" = 0.75 beside the correct project-level 1.5-vs-1.5 match). **Multi-terminal FSRU site split (`_split_multiterminal_fsru_sites`):** GIIGNL labels several physically distinct FSRU terminals at one port with the SAME site name, disambiguating only by vessel — e.g. Germany "Wilhelmshaven" appears twice (Höegh Esperanza, Excelerate Excelsior), which GEM tracks as two terminals ("Wilhelmshaven FSRU" + "Wilhelmshaven TES FSRU"); Egypt "Ain-Sokhna" lists three vessels split across GEM "Ain Sokhna FSRU" (Energos Power) and "Sumed FSRU" (Höegh Galleon, Energos Eskimo). Each GIIGNL vessel row is routed to the GEM terminal whose **terminal-level `FloatingVesselName`** carries it (GIIGNL "Excelerate Excelsior" ⊇ GEM "Excelsior"), and the site is emitted as one report sub-project per GEM terminal (display name carries the vessel, e.g. "Wilhelmshaven (Höegh Esperanza)"), each force-matched. Fires only when the site's vessels resolve to **≥2 distinct GEM terminals** AND every row maps — distinguishing it from the sequential-berth case below. **FSRU operating-only (`_fsru_operating_report_capacity`):** for a genuine single-terminal berth that cycled vessels (one GEM operating unit + retired vessels) where GIIGNL lists every deployed FSRU as an operating row, the report capacity is recomputed as the sum of only the GIIGNL rows whose vessel (matched against GEM `unit_name`) maps to a GEM OPERATING unit; the others become per-vessel notes in `disagreements`. Also emits `nonoperating_units` (non-op units of matched projects) for the `giignl_diff_nonoperating` sheet. **Non-operating GIIGNL rows (Bontang/Balhaf fix):** a report row carrying a `status` (set by giignl_extract from a "(Mothballed)"/"(stopped)" hint, i.e. status ∈ `_NONOP_STATUSES`) is split out of the report project into `nonop_rows` and EXCLUDED from `total_capacity_mtpa`/`trains_count`/`rows` — so the operating comparison sums only the operating trains (Bontang report=F+G+H=8.7 vs GEM operating G+H=5.75, NOT 11.6; Balhaf both-trains-stopped → report 0 vs GEM 0, killing the old spurious 7.2-vs-0). The excluded rows surface on the match as `report_nonoperating` (operating sheet column, no red), and `_corroborate_nonop` aligns each to the GEM non-op unit whose name is a token of the row's site_name+trains (lowercased — `_simple_tokens` doesn't case-fold and `trains` isn't normalized), filling that unit's `giignl_narrative_mention` + clearing its `is_gem_only` flag (Bontang E↔unit E idled; Balhaf T1/T2↔GEM T1/T2 mothballed). Tiny blast radius — only fires when a GIIGNL row actually carries a status (≈4 rows in the 2026 edition). **§3.2.1 prose operating-status corrections (Bontang Train F fix):** GIIGNL's TABLE is operating-only but its NARRATIVE can say a train listed *untagged* in the table isn't actually operating — Bontang p.31: "only Trains G and H currently in operation" means Train F (untagged in the table, no "(Mothballed)") is idled too. The narrative pass is agent-driven (SOP §3.2.1), so this is fed via an agent-authored `giignl_prose_corrections.json` (auto-discovered next to the extracted CSV, or `--prose-corrections`): `_load_prose_corrections` + `_apply_prose_corrections` run right after the FSRU split and BEFORE matching, moving each named unit's report row from `rows`→`nonop_rows` (status from the file, default idled), recomputing the operating total, and stamping `_prose_source` (the citation flows into `report_nonoperating` and the corroboration note). This drops Bontang from a bogus report 8.7-vs-5.75 (51%) to 5.8-vs-5.75 (0.9%, just the per-train cap nuance, G+H both 2.9 in GIIGNL vs 2.8/2.95 in GEM) — F now corroborates GEM's idled F via prose. Capacity NUMBERS are never changed here (§5.6 prefers the tabular value); nothing is applied to GEM (§3.8) — it only makes the GIIGNL side internally consistent with GIIGNL's own prose. The file's second section, `nonop_corroborations`, handles the related case where a GEM non-op unit has NO GIIGNL table row because the unit already ceased (NWS Train 2: dropped from the operating table, but the narrative names it "permanently ceased") — `_load_prose_corrections` returns `{op, nonop}`, and the nonoperating-units pass fills `giignl_narrative_mention` + clears `is_gem_only` for the named GEM unit (keyed GEM terminal+unit)

**Read / revisit the source when:** Unit names don't tokenize cleanly against report site names; alignment over/under-matches (check `match_granularity` + `unit_matches`); a same-named multi-terminal FSRU port doesn't split or splits wrong (check GEM `FloatingVesselName` vs GIIGNL vessel; needs ≥2 distinct GEM terminals); FSRU vessel names don't match GEM unit names (check the FSRU notes in `disagreements`); a sub-terminal designator matches the wrong or no GEM unit (check `_unit_designators` — needs exactly one unit in one terminal + name/owner corroboration); owner deltas look systematically wrong (check the GEM cell separator/bracket format vs `parse_entity_list`); a "(Mothballed)"/"(stopped)" GIIGNL row is still summed into the operating total or doesn't corroborate its GEM non-op unit (check the `status` column in `giignl_extracted.csv`, the `_NONOP_STATUSES` membership, and `_corroborate_nonop` token match against site_name+trains); a terminal where GIIGNL's NARRATIVE corrects the table's operating status (a train listed untagged but the prose says it's down — Bontang Train F) is still over-summed (add an entry to `giignl_prose_corrections.json` keyed country+site+section with the `nonoperating_units` + citation, and confirm `_apply_prose_corrections` matched the unit token to the report row)

