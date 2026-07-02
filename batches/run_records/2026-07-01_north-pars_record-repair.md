# 2026-07-01 — North Pars LNG Terminal (Iran) targeted record repair

**Trigger:** Follow-on to the 2026-06-30 missing-year ref-sweep. The user flagged the
Iran / North Pars / "T1-T4" / FID row (st_id 1787) as confused — its DB source pointed
at a Qatar expansion project. Investigation confirmed a two-project chimera: the real
2006 Iranian NIOC-CNOOC North Pars LNG proposal contaminated with Qatar North Field
data (QatarEnergy owner, 32 mtpa, 2018 proposal). a GEM researcher began a live overhaul
2026-06-30 ~13:42 ET (unit "T1-T4" → "--", timeline reduced to a single proposed-2006
entry sourced to China Daily, st_id 1787 deleted) — which left loose ends: standing
status stuck at `proposed`, ownership wiped, one blank draft timeline row open.

## Scope

Single terminal: **T100000130584 / unit G100002058401**, standard Update-workflow
mechanics (fresh export pulled; read-only Postgres used to inspect the draft state;
zero live-DB writes).

## Research findings (all URLs url_verifier PASS)

- CNOOC-NIOC MoU Sep 2006, extended Dec 2006 to a 4-train **20 mtpa** LNG development
  (China Daily 2006 — existing ref, re-verified per SOP §7.2; OGJ 2006).
- Reported ~$16bn development contract 2008, never finalized (detail on the OilPrice
  page, PASS `$16 billion`).
- Last live plan **April 2010** (OGJ: plant in Tombak region, construction 2013,
  startup 2014) — the last-activity anchor.
- CNOOC withdrew as sanctions ramped **2011/12** (OilPrice 2021); OIES NG-78
  (June 2013): North Pars LNG "did not advance" / "made no progress".
- No LNG revival since. The 2025-26 North Pars revival is the domestic FIELD
  development (POGC), no LNG component → monitor entry, dead-and-revived rule applies
  if that ever changes.

## Staged (batches/staging/north-pars/ → workbook)

- **Timeline additions (2):** shelved `inferred 2 y` **2012** → cancelled `inferred 4 y`
  **2014** (last-activity 2010 + 2/+4; proposed→shelved→cancelled legal). Restores the
  dead standing status the overhaul lost.
- **updates_summary (16 records):** Status → cancelled (+refs), ShelvedYear/CancelledYear
  anchors (+ paired refs), ShelvedCancelledStatusType=inferred, Owner/Parent/Parent GEM
  Entity ID/ParentHQCountry = National Iranian Oil Co / E100000000556 (South Pars
  precedent; entity_lookup bare + --remote — reuse, no new entity), Capacity [ref]
  upgraded to 3 independent publishers (OilPrice + OGJ + OIES → green; value unchanged),
  Location = Tombak (OGJ, yellow; coords deliberately blank), ResearcherNotesProject
  documenting the chimera + deliberate divergence so a future reconciliation doesn't
  re-merge Qatari data.
- **qa_review (4):** blank draft timeline row left open by the overhaul; CNOOC
  "100% of shares" alternative ownership reading (OGJ 2010) documented; POGC absent from
  entity system (not needed now) + the name-variant lookup caveat ("Co" vs "Company");
  coordinate guidance (reuse Iran NIOC LNG Terminal's approximate Tombak Port coords if
  wanted).
- **monitor_list (1):** domestic North Pars field development watch (Wayback-verified
  offshore-technology profile; live page 403s).
- **wiki_updates (1):** corrected narrative for the gem.wiki page (likely carries the
  same Qatar contamination).

## Deliverable

**`batches/lng_terminals_batch_20260701_1707_ET_north-pars_update.xlsx`** (recalc OK,
no formula errors). A superseded 1706_ET build from one minute earlier exists (staging
`ref_field` metadata fix in between — same data) — prune it.

## Verification / gate notes

- OIES NG-78 PDF: fetchable by url_verifier, but "20 mtpa" line-wraps in the PDF text
  layer — verify with tokens `North Pars LNG with 20` + `no progress`.
- Year tokens: "2012" is NOT a substring of "2011/12" — the inferred-year refs document
  the basis, not the digit (flagged in validation_warnings).
- Rigzone ($16bn story) bot-challenges (HTTP 202) with no Wayback snapshot → dropped;
  the $16bn detail is covered by the OilPrice page instead.
- offshore-technology profile 403s live → cited via its 2026-01-03 Wayback snapshot
  (PASS).
- Staging lesson: on a blank-ref-fill record (`field_name="X [ref]"`), leave `ref_field`
  empty — pointing it at the base column trips the build's GUARD (correctly).
