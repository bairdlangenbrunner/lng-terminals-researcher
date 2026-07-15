# Thailand Discovery — research brief (tight threshold)

You are hunting for LNG import/export terminals in **Thailand** that are MISSING from GEM's Global
Gas Infrastructure Tracker, for a Discovery batch at a **tight** sufficiency threshold. Today is
**2026-07-10**. Work end-to-end; return a terse summary. Run scripts from
`/Users/baird/Dropbox/_git_ALL/_github-repos-gem/lng-terminals-researcher/scripts`.

## Hard rules (same as Update — non-negotiable)

- **Every URL passes `url_verifier.py`** against the specific claimed value before you cite it
  (`python url_verifier.py "<url>" "<token>" ...`). 401/403 = bot-block (live) → verify via Wayback.
- **≥2 independent working sources** per staged value (different publishers; two mirrors of one doc
  = ONE source). One primary/regulatory → green; one non-primary → yellow.
- **NEVER cite gem.wiki / globalenergymonitor.org** or a GEM-derivative (IEEFA/Wikipedia/news that
  just footnotes GEM). gem.wiki DETECTS gaps but is NEVER the citation — chase the primary source.
- **URLs only in `[ref]` fields.** No orphan refs.
- **New entity check:** `python entity_lookup.py "<name>" --remote` (bare, no --country) before
  staging any NEW owner/operator/parent. A match anywhere = reuse it.

## Scope gate (apply BEFORE the sufficiency threshold — resolve doubt, never stage-with-doubt)

A candidate is IN SCOPE only if it moves LNG across a border **BY SHIP** (import or export terminal).
OUT OF SCOPE and to be dropped:
- Domestic-only virtual-pipeline / LNG-by-truck / peak-shaving / satellite regas plants (no marine
  LNG import). Thailand has several small inland "LNG" distribution depots — these are out of scope.
- A gas-fired **power plant** is NOT a terminal. If an "LNG-to-power" project bundles an LNG
  storage/receiving component but is fed by regasified gas **piped from another (existing) terminal**,
  the marine-import gate fails at the plant site → it belongs to GOGPT, not here; if the supplying
  terminal is already in GEM, that's a `PowerPlantsSupplied` note on the existing terminal, not a new
  terminal. (The Quang Trach II ← Vung Ang miss.)

## Sufficiency threshold (tight)

Stage as a NEW terminal only if: **sponsor identified + approximate location + a concrete step taken**
(MOU/FEED/permit filing/land lease/FID/EPC — not merely "studying" or a minister's aspiration).
Candidates below that bar go on the **monitor_list**, not new_terminals.

## The existing GEM Thailand roster (8 terminals) — for DEDUP, do not re-stage these

1. Map Ta Phut LNG Terminal 1 (+ Expansion) — PTT LNG, operating, ~11.5 mtpa, Rayong. T100000130321
2. Map Ta Phut LNG Terminal 2 / Nong Fab — PE LNG (PTT/EGAT), operating 7.5 mtpa, Rayong. T100000130322
3. Map Ta Phut LNG Terminal 3 (Phase I+II) — Gulf Energy/PTT, proposed, Rayong. T100000130894
4. Surat Thani FSRU — EGAT/PTT, shelved. T100000131071
5. Chana LNG Terminal — KOGAS/KEPCO/TPI Polene, cancelled, Songkhla. T100000130893
6. Gulf of Thailand FSRU — EGAT, cancelled 2021. T100000130896
7. Songkhla FSRU — PTT, cancelled 2018, Songkhla. T100000130898
(These map the known PTT / EGAT / Gulf Thai LNG landscape. A candidate matching one of these under a
different name is NOT new — note it as a documented duplicate.)

## Dormant-revival watch (Discovery SOP §4.0a — web-search each for NEW activity)

These 4 dead Thai sites: a genuinely DIFFERENT new project (different sponsor/design) at one of them
is a NEW terminal (link via `AssociatedTerminals` → the dead record), not an edit to the dead record:
- Songkhla FSRU (T100000130898, cancelled 2018), Songkhla
- Gulf of Thailand FSRU (T100000130896, cancelled 2021), offshore Gulf
- Chana LNG Terminal (T100000130893, cancelled 2025), Chana/Songkhla
- Surat Thani FSRU (T100000131071, shelved 2025), offshore Surat Thani

## Search program (your ring assignment is in your dispatch prompt)

- **Regulators/planners:** Thailand ERC (Energy Regulatory Commission), EPPO, DMF/Department of
  Mineral Fuels, Thailand's PDP (Power Development Plan) & Gas Plan, EGAT, PTT, the LNG "shipper"
  licences the ERC has issued (many new LNG shippers licensed 2021-2025 — but a shipper licence ≠ a
  terminal; only a physical import facility counts).
- **Trade press:** LNG Prime, Reuters, S&P Global Commodity Insights, Argus, Upstream, Bangkok Post,
  The Nation Thailand, offshore-energy.biz.
- **Sponsor IR:** PTT / PTT LNG, EGAT, Gulf Energy Development, Hin Kong Power, Gulf-PTT JVs, B.Grimm,
  Nong Fab, and any newcomer LNG-import proponents. Also any upstream Gulf-of-Thailand gas operators
  (PTTEP, Chevron successor Hin Kong) if an FLNG/associated-gas export idea surfaces.
- **gem.wiki coverage cross-check (Discovery SOP §4.0b):** enumerate gem.wiki LNG-terminal pages for
  Thailand (browse the gem.wiki Thailand LNG category / search) and reconcile against the 8-terminal
  roster above. A gem.wiki page with NO matching roster entry is a candidate — research it from
  INDEPENDENT sources (gem.wiki is never the citation).

## Output — write your assigned file (see dispatch prompt), format:

```
{
  "new_terminals": [ {  // only threshold-clearing NEW terminals
    "TerminalName":"...","OtherNames":"...","FacilityType":"import|export","Fuel":"LNG",
    "Country/Area":"Thailand","State/Province":"...","Location":"...","Accuracy":"approximate",
    "Owner":"...","ProposalYear":"...","Status":"proposed","FIDStatus":"Pre-FID",
    "AssociatedTerminals":"T... (if reviving a dead site)",
    "<field> [ref]":"<url>", ...,  // URLs ONLY in [ref] fields
    "ResearcherNotesProject":"full rationale incl. scope verdict + why this threshold call",
    "Source":"publisher names","confidence_overall":"green|yellow",
    "confidence_per_field":{"Owner":"green",...}
  } ],
  "monitor_list": [ {"name":"...","country":"Thailand","sponsor":"...","location":"...",
      "concrete_step":"... or none yet","why_monitor_not_stage":"...","source_urls":["..."]} ],
  "entity_checks": [ {"name":"...","found":true|false,"entity_id":"...","note":"..."} ],
  "dormant_revival_findings": [ {"terminal_id":"T...","site":"...","new_activity":"none|...",
      "verdict":"still_dead|new_terminal_staged|monitor","notes":"..."} ],
  "documented_duplicates": [ {"candidate":"...","maps_to":"<roster terminal>","why":"..."} ],
  "out_of_scope_dropped": [ {"candidate":"...","why_out_of_scope":"..."} ],
  "gemwiki_crosscheck": {"pages_found":["..."],"wiki_only_gaps":["..."],"notes":"..."},
  "url_verifications": [ {"url":"...","tokens":["..."],"passed":true} ],
  "summary":"what you found; how many cleared the tight bar; dead sites still dead."
}
```

Return to the main loop ONLY your summary + counts.
