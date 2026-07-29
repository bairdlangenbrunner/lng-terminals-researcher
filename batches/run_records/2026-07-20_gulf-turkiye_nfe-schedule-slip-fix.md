# 2026-07-20 — gulf-turkiye NFE schedule-slip fix (user-flagged miss)

## Ask

User flagged that the constructionreviewonline NFE article — cited in the
gulf-turkiye batch for construction-resumption — also states the NFE first-train
startup was pushed to early 2027 (GEM had LatestPlannedStartYear=2026) and that
NFS enters service ~12–18 months after the first NFE train. Neither schedule
fact was elevated to a staged edit; the qa note deferred behind the QatarEnergy
CEO's "on track" line. Fix the batch and encode the lesson.

## What was found

- **Partially caught, wrongly deferred:** the original qa entry
  (qatar.qa.json, NFE/NFS schedule) flagged the uncertainty but concluded
  "LatestPlannedStartYear=2026 ... not clearly wrong" — the hedge-and-punt
  failure class, this time on a planned date instead of a status.
- **NFS needs NO year change:** the article's anchor is relative ("~12–18
  months after the first NFE train") → early 2027 + 12–18 mo = early-to-mid
  2028, consistent with GEM's existing 2028 and the existing newest timeline
  entry (operating/planned 2028). Article added as StartDate [ref] corroboration.
- **NEW live-DB conflict (fresh-pull find):** NFE (T1-4) was manually edited in
  the live DB on 2026-07-20 (after the batch build) to Status=operating,
  ActualStartYear=2026/H1, + a matching timeline entry (st_id 41359). No
  first-LNG/first-cargo report exists anywhere as of 2026-07-20; all reporting
  (LNG Prime pre-commissioning, MEES "hopes 3Q 2026", constructionreviewonline
  "pushed to early 2027") contradicts it. Escalated via high-severity qa entry +
  staged revert records; reviewer adjudicates.

## Staged (qatar.updates.json / qatar.timeline.json / qatar.qa.json / qatar.wiki.json)

- NFE `LatestPlannedStartYear` 2026→2027, green — 3 independent underlying
  reporters (constructionreviewonline citing MEES, Jun 2026; Bloomberg-syndicated
  via energynow.com, Mar 2026; Energy Intelligence). All url_verifier PASS on
  '2027' tokens.
- NFE operating/planned **2027 H1 timeline append** (new `qatar.timeline.json`;
  existing timeline pulled via fetch_timeline.py first).
- NFE Status **operating→construction revert** + `ActualStartYear`/`ActualStartMonth`
  deletions (paired with the live-DB-conflict qa entry; discard all four + the
  timeline append if the reviewer confirms a real first-LNG event).
- NFS Status re-verify notes re-anchored; article appended to NFS StartDate [ref]
  (url_verifier PASS 'mid-2028'). Wiki background schedule sentence updated.
- qa: original NFE/NFS entry marked RESOLVED with the staged records; new
  high-severity live-DB-conflict entry (timeline sheet is append-only, so
  st_id 41359 removal must be manual).

## Rebuild

- GIIGNL diff regenerated against the fresh 2026-07-20 export (recon-tab rule:
  refresh first). `_assemble.py gulf-turkiye`: 100 updates / 1 timeline / 26 qa.
- Workbook: `batches/lng_terminals_batch_20260720_1053_ET_gulf-turkiye_exhaustive_update.xlsx`
  (now includes `status_timeline_additions`; giignl_recon 17 rows). Guard-clean,
  recalc OK. Supersedes 1246_ET (user prunes).

## Durable rule added ("planned-start slip elevation")

Update SOP §3.2 (full rule), `_country_agent_brief.md` (subagent version),
CLAUDE.md + workflows.md §5 (one-liners), project memory. Core: read every
cited source in full for schedule content; a corroborated planned-startup slip
vs GEM's LatestPlannedStartYear = staged year edit + operating/planned timeline
append, never a qa/source-note mention; sponsor "on track" doesn't veto a
corroborated slip; relative anchors ("~12–18 months after phase A") count.
