# LNG sweep — progress ledger

## ✅ CLOSED — 2026-07-16 (this file is now historical; do not resume from it)

This Asia sweep was **formally closed** during the 2026-07-16 repo audit
(`docs/repo_audit_2026-07-16.md`) after sitting stalled since 2026-07-08 with 4 of 22
groups landed (japan, south-korea, taiwan, + a trivial vietnam touch). Coverage state
now lives in the **coverage ledger** — per-dir `batches/staging/*/meta.json` +
`python scripts/coverage_status.py` — which supersedes this file as the "what was last
done where" source. `batches/staging/asia/meta.json` records what this sweep actually
covered; `asia/_archive_pre20260708/meta.json` credits the June full-tracker vintage
for the countries this sweep never reached.

- The remaining scope (china ×4 shards, indonesia, malaysia, myanmar, cambodia,
  singapore, brunei, hong-kong, turkmenistan, + discovery incl. maldives / north korea /
  japan / south-korea / taiwan) is **a future batch, dispatched fresh from the ledger's
  stale list** — not a resume of this sweep. Worklists under `asia/_worklists/` are
  stale (2026-07-08 export) and must be regenerated from a fresh pull.
- The done-markers this file calls "authoritative for resume" were pruned 2026-07-16
  (coverage recorded in meta.json); the resume recipe below is void.
- Everything below is preserved as the historical record of the sweep as dispatched.

## ⚠ STATE NOTE — 2026-07-14 (read before resuming the Asia sweep below)

- **Two environment bullets below are now STALE — do not propagate them into dispatch prompts:**
  `fetch_timeline.py` reads the read-only Postgres (a confirmed status change is STAGED, never punted
  to qa — briefs updated 2026-07-14), and `entity_lookup.py --remote` is reachable again but has
  intermittent FALSE NEGATIVES — the orchestrator re-checks staged entities against Postgres
  `entity_history` at the merge-time QC gate (workflows.md §5 step 3a).
- **Only 4 of 22 update/discovery groups ever landed** (markers: japan, south-korea, taiwan, vietnam).
  The 15:05 ET fan-out of U1–U12 did not complete; no findings files exist for the other groups.
- **Much of the remaining scope was since covered by newer, separately-recorded batches** — do NOT
  re-dispatch these slugs at standard tier without reading their run records: vietnam (07-02 exhaustive,
  07-09 discovery-recheck, 07-10 closeout), philippines (07-09 update+discovery), thailand (07-10
  update+discovery), bangladesh / india ×2 / pakistan / sri-lanka (07-14 south-asia-iran exhaustive
  update+discovery — a HIGHER tier than this sweep's standard).
- **Still genuinely uncovered from this sweep's scope:** china (4 shards), indonesia, malaysia, myanmar,
  cambodia, singapore, brunei, hong-kong, turkmenistan (update); discovery for those same countries plus
  the coverage-gap pair (maldives, north korea) and japan/south-korea/taiwan (U13 did update only).
- **Conventions added since this sweep dispatched** (apply to any resume): subagent model chosen
  at dispatch time (workflows.md "Model selection" — cheapest that's good enough);
  discovery-pass qa/entity use the `.disc.` infix (non-overlap rule);
  confirmed status changes write `<slug>.timeline.json`; discovery build takes `--checked-roster`.

## Sweep: Asia update + discovery — started 2026-07-08

- **Scope:** whole `asia` region — 19 GEM-covered countries (bangladesh, brunei, cambodia,
  china, hong-kong, india, indonesia, japan, malaysia, myanmar, pakistan, philippines,
  singapore, south-korea, sri-lanka, taiwan, thailand, turkmenistan, vietnam) + 2 uncovered
  coastal countries from `coverage_gap` (maldives, north korea). Middle East countries are
  NOT in this region (swept as `middleeast`).
- **Tier:** `standard` (user said "updated discovery and update pass for Asia"; no exhaustive request).
- **Fresh export:** pulled 2026-07-08 14:15 ET — 1,288 unit rows, 115 cols, colmap re-derived.
- **Methodology doc:** confirmed in context via Drive MCP, "Last updated: Baird and Rob, May 2026".
  SOPs update rev 2 / discovery rev 2 (2026-06-24).
- **Prior asia staging:** the June-2026 full-tracker-sweep files (93 JSON + `_build/`) MOVED to
  `batches/staging/asia/_archive_pre20260708/` so `_assemble.py` can't re-merge them. Do NOT restore.
  (Vietnam's 2026-07-02 exhaustive batch lives separately in `batches/staging/vietnam/` — untouched.)
- **Worklists:** per-country `batches/staging/asia/_worklists/<slug>.json`
  (gem_rows, dev_pipeline, stale_flags, blank_refs, other_gaps, dormant_revival_watch).
  China sharded ×4 (`china_0..3.json`), India ×2 (`india_0..1.json`); unsharded copies kept as
  `<slug>.FULL.json`. Region totals: 454 unit rows, 171 dev-pipeline units, 9 stale flags,
  339 blank-ref targets, 104 dormant sites.
- **fetch_timeline.py is DOWN** — status changes route to qa notes (category `status_timeline`).
- **entity_lookup.py --remote is BROKEN** (stale heroku host, per 2026-07-02 africa record) —
  agents run bare local lookup; orchestrator cross-checks entity candidates against the
  read-only Postgres `company` table at build time.
- **coverage_gap.gem_countries_outside_reference:** botswana, turkmenistan — FIXED, both hand-added
  to `scripts/country_universe.py`; re-run shows outside_ref empty, uncovered count unchanged (52).
- **Division of labor:** dormant-revival checks + gem.wiki cross-check + coverage-gap countries
  are the DISCOVERY wave's job; update agents work their worklist only.

## Status table

| Wave | Group | Countries/shards | Status |
|---|---|---|---|
| update | U1 | china_0 | dispatched ~15:05 ET |
| update | U2 | china_1 | dispatched ~15:05 ET |
| update | U3 | china_2 | dispatched ~15:05 ET |
| update | U4 | china_3 | dispatched ~15:05 ET |
| update | U5 | india_0 | dispatched ~15:05 ET |
| update | U6 | india_1 | dispatched ~15:05 ET |
| update | U7 | pakistan | dispatched ~15:05 ET |
| update | U8 | vietnam | dispatched ~15:05 ET |
| update | U9 | indonesia | dispatched ~15:05 ET |
| update | U10 | bangladesh, myanmar | dispatched ~15:05 ET |
| update | U11 | thailand, cambodia, singapore, brunei, hong-kong, turkmenistan | dispatched ~15:05 ET |
| update | U12 | sri-lanka, philippines, malaysia | dispatched ~15:05 ET |
| update | U13 | japan, south-korea, taiwan | DONE (3/3 markers; test-dispatch group) |
| discovery | D1 | china | pending |
| discovery | D2 | india | pending |
| discovery | D3 | indonesia | pending |
| discovery | D4 | vietnam, cambodia | pending |
| discovery | D5 | philippines, malaysia, brunei | pending |
| discovery | D6 | bangladesh, myanmar, sri-lanka, maldives | pending |
| discovery | D7 | japan, south-korea, taiwan, hong-kong, north-korea | pending |
| discovery | D8 | thailand, singapore | pending |
| discovery | D9 | pakistan, turkmenistan | pending |

Done markers: update agents write `<slug>.done.json` (shards `china_0.done.json` etc.),
discovery agents `<slug>.disc.done.json`. Markers are authoritative for resume, not
workflow return values.

Build steps (after both waves): fsru_sync_check → `_assemble.py asia` (or `_build_region.py asia <STAMP>`
for disc-isolation) → `--mode update` build → recalc → monitor_store seed → `--mode discovery` build →
recalc → monitor_store update → run record.

## Run log

- 2026-07-08 ~14:10 ET — fresh pull (14:15 ET stamp), dedup_index, stale_sweep, completeness_sweep run.
- 2026-07-08 ~14:16 ET — June asia staging archived to `_archive_pre20260708/`; worklists written; china ×4 / india ×2 shards.
- 2026-07-08 ~14:20 ET — update wave: test-dispatch U13 first (usage-limit pattern from africa sweep), fan out U1–U12 on success.
- 2026-07-08 ~15:00 ET — U13 SUCCEEDED (3/3 markers: japan, south-korea, taiwan). Japan 4 blue + 2 qa;
  South Korea 4 blue + 3 qa (KOGAS Dangjin Ph2 likely construction → status_timeline qa); Taiwan 1 green
  (Mailiao start→2029, Kawasaki/CTCI EPC) + 4 blue + 3 qa + 1 wiki. 20 URLs verified, no entities/new terminals.
- 2026-07-08 ~15:05 ET — U1–U12 fanned out concurrently (12 agents, all remaining update groups).

## Resume recipe (cold session)

1. Done markers are authoritative: `ls batches/staging/asia/*.done.json`. A group without all its
   markers was never finished → re-dispatch just that group (briefs: `_country_agent_brief.md` /
   `_discovery_brief.md`; worklists in `batches/staging/asia/_worklists/`; region `asia`; tier standard).
2. When all markers present: run the build steps above (commands in `batches/staging/README.md`).
3. Do NOT re-merge `_archive_pre20260708/` — June full-tracker findings, already applied.
