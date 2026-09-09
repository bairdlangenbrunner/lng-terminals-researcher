# run record — captive-power africa + oceania (2026-08-02)

## Plan

User directive: "go ahead and do africa and then oceania … if you run into any token
limits going forward, build in automation that picks up the research where it leaves
off. I want both africa and oceania to be completely finished before you stop."
The final two increments of the coordinate-first captive-power crawl: africa (67
terminals, incl. the missing-coords New Fortress Angola) + oceania (37). Method
identical to the americas-gap run; durable resume state machine in
`batches/staging/captive_power/_kickoff_africa-oceania.md` + session cron d6a893fa
firing :23/:53 while idle.

## Status / how it ran

- Fresh export + audit-derived worklists → neighbors/priors → dispatch (17 shards
  total) → sonnet research shards, one checkpoint file each.
- The session usage limit killed 4 in-flight recovery agents once (resets 4:10pm ET);
  the resume cron woke the session, all 4 were resumed via SendMessage with their
  context intact and completed. WebSearch was budget-exhausted (200/200) for the whole
  session — recovery agents worked via WebFetch site-search endpoints, Google News RSS,
  DuckDuckGo HTML, SEC EDGAR fts, and the Wayback save-page-now trick (Pluto: created
  snapshot 20260802182431 to cure a 403-with-no-snapshot).
- QC gate: coverage 67/67 + 37/37; banned/bare-domain scans clean; adjudications and
  declared ref drops in `{africa,oceania}/_qc_gate_done.json`; both `_assemble_*.py`
  carry the gate mechanism (VERDICT_OVERRIDES / REF_DROPS+dropped_urls_dead /
  ADJUDICATED_OVERTURNS / recovery-supersede).

## Outcome

- **Deliverables:** `batches/lng_terminals_batch_20260802_1650_ET_africa-captive_update.xlsx`
  (55 rows / 17 YES terminals) + `…_1650_ET_oceania-captive_update.xlsx` (36 rows / 14
  YES terminals) — guard-clean, recalc clean, 81 tests pass; uploaded to the shared
  Drive folder.
- Verdicts: africa 17 YES / 14 NO / 29 INSUFFICIENT / 7 SCREENED; oceania 14 YES / 1 NO
  / 18 INSUFFICIENT / 4 SCREENED. Zero overturns of live-DB Trues (Tango, Pasca, PAWA
  all adjudicated keep).
- **Final coverage audit PASSES with no pending increments: 843/843 TerminalIDs
  crawled — the captive-power crawl of the whole tracker is complete.**
- Memo: `batches/captive_power_memo_20260802_1652_ET_africa-oceania.md` (recovery
  upgrades incl. Hilli + Pluto + Crib Point, FSRU-convention scoping ruling, 4 GOGPT
  ADD candidates, Höegh Galleon/Yurralyi Maya/Browse leads).
- Convention ruling this run: the FSRU-onboard convention applies to extant/assigned
  vessels and ACTIVE projects; cancelled projects that never assigned a vessel keep
  design-based NOs (Karpowership trio + Mossel Bay), while an active vessel-less
  proposal downgrades NO → INSUFFICIENT (Richards Bay Transnet, Hadera class).
- Resume cron d6a893fa deleted at close; kickoff STATUS marked done.
