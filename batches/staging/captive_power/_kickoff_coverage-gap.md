# Kickoff — captive-power coverage gap: americas-gap (+ europe top-up)

Stage directions for closing the coverage hole found by the first coordinate-first audit
(2026-08-01). Written the day the user mandated coordinate-anchored universe accounting
(SOP §3 step 0, `scripts/captive_coverage_audit.py`). Read this whole file plus the ME/Gulf
kickoff's mechanics section before dispatching.

## Why this exists

`captive_coverage_audit.py --pending africa,oceania` on the 2026-08-01 export: 843-terminal
universe, 582 crawled, 261 uncrawled — of which 156 americas + 1 europe are NOT in any
planned increment. Root cause: the americas increments' scope was a hand-curated 15-country
list, and the early Louisiana/Texas increments recorded only their *confirmed* subset in
`captive_terminal_first.json` (a memo-only NO is not coverage). "americas-complete" was
complete only relative to its own list.

## Scope A: `captive_power/americas-gap` — 156 terminals

Regenerate the exact worklist from the audit on the batch's FRESH pull (`--csv` dump, filter
`crawled_by` empty + region americas) — do NOT paste a stale list here; the universe moves.
Composition on 2026-08-01 (expect drift): ~60 US (incl. **Cameron LNG** and **Lake Charles**
— operating/major, research first; many cancelled East-Coast/West-Coast proposals), ~25
Canada (the BC export wave: Kitimat, Pacific NorthWest, Prince Rupert, Aurora, Grassy Point…),
~19 Brazil FSRUs, ~10 Colombia, Chile/Mexico/Argentina/Venezuela/Caribbean remainder, and
~14 crude-oil deepwater ports (SPOT, LOOP, Blue Marlin, Texas GulfLink…) which get recorded
**SCREENED** verdicts with the scope-error evidence — recorded, so they leave the queue.

Backfill-with-verification, don't re-research blind: Freeport and Texas LNG have researched
NO verdicts in the TX memo (`batches/captive_power_memo_20260710_1410_ET_texas.md`) that were
never recorded in terminal_first — port them into `captive_terminal_first.json` records, re-run
their URLs through `url_verifier.py`, and mark `confirmed_how` accordingly. Everything else is
net-new research under the standard brief (`_captive_power_brief.md`), fuel gate, FSRU-onboard
convention, grid-access prior (SOP §4b — most BC/US-East proposals will be documented
e-drive NOs), and no-stage-with-doubt.

## Scope B: `captive_power/europe-topup` — 1 terminal (+ audit drift)

Port of Vlora FSRU 2 (T100001084613, Albania) postdates the europe increment. Run it as a
tiny separate staging dir so europe's meta stays honest. Any additional post-europe records
the fresh audit surfaces join it.

## Mechanics (same as ME/Gulf kickoff)

1. Fresh pull → `captive_coverage_audit.py --pending americas-gap,europe-topup,africa,oceania`
   → regenerate worklists from its CSV.
2. Staging dirs + meta.json at creation. 3. Priors + nearest-2 neighbors WITH `gogpt_plant_id`
   (whole-country pulls, never `--subnational`). 4. Shard dispatch max ~8 terminals (≈20
   shards; cheapest good-enough model; expect WebSearch-pool exhaustion → WebFetch/DDG chain;
   plan the recovery pass as a standard phase). 5. QC gate (overturn re-verification, fuel-gate
   audit of every NO, screened-evidence audit, citation sweeps). 6. Assemble → build →
   recalc → tests. 7. Memo + run record + meta + `captive_power_colocation_workflow` +
   `coordinate_first_coverage_universe` memory updates. 8. **Re-run the audit before claiming
   done** — it must show americas/europe fully crawled with only africa+oceania pending.

## Remaining after this

`_kickoff`-style sessions for **africa (67 — incl. New Fortress Angola T100000130823, which
has NO coordinates: incorporate it explicitly, and georeference per workflows §10 as a
side-find if sources allow)** and **oceania (37 — Australia-dominated, expect the highest YES
density of any region)**. Full-database coverage = all four scopes closed + a clean audit.
