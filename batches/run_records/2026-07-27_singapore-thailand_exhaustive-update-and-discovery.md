# 2026-07-27 — Singapore + Thailand exhaustive update + discovery

## Plan

- User-requested deep sweep ("like Türkiye and the Gulf countries"): exhaustive-tier
  Update + full Discovery for Singapore and Thailand, gulf-turkiye pattern
  (ad-hoc region dir `batches/staging/singapore-thailand/`).
- Supersedes the never-applied 2026-07-10 `thailand/` + `thailand-discovery/`
  standard-tier batches — their staged findings were re-verified and carried forward;
  both dirs' meta.json now say `superseded`. **Do not apply the 07-10 workbooks.**
- Fresh pull 2026-07-27 18:13 ET (1,273 unit rows, 115 cols, colmap re-derived).
  Scope: 10 terminals (3 SG, 7 TH). Methodology doc confirmed in context
  ("Last updated: Baird and Rob, May 2026").

## Status

- 4 subagents (SG update, TH update, SG discovery, TH discovery — Sonnet) dispatched
  ~18:15 ET, all complete by 18:33 ET with done markers (pruned after close-out).
- Merge-time QC gate (workflows §5 step 3a) run by orchestrator ~18:35–18:42 ET.
- Built 18:42 ET; monitor store rolled forward; meta.json `built`/`status` set.

## Outcome

**Deliverables (apply these):**

- `batches/lng_terminals_batch_20260727_1842_ET_singapore-thailand_exhaustive_update.xlsx`
  — 83 updates (17 green / 13 yellow / 53 blue), 2 timeline appends, 24 qa, 5 wiki.
- `batches/lng_terminals_batch_20260727_1842_ET_singapore-thailand_discovery.xlsx`
  — 0 new terminals, 1 new monitor candidate (Thailand ASEAN re-export hub aspiration,
  merged into `monitor_list/current.json`), 4 discovery qa.
- An interim `…_1840_ET_…exhaustive_update.xlsx` (pre-QC-repair, carries REF-DROP
  warnings) is superseded — prune it.

**Headline findings:**

- **SLNG 2 LNG Terminal (SG, T100000130890): proposed → construction STAGED**
  (Status + ConstructionYear 2026 + ConstructionMonth March + timeline append,
  green, 3 corroborating sources — onshore infrastructure work at Jurong Port
  started March 2026). Planned start 2030 re-verified unchanged (MOL FSRU
  delivery ~Oct 2027, moored 2030).
- **Map Ta Phut LNG Terminal 3 Phase I (TH): proposed → construction STAGED**
  (green; EPCC superstructure contract Jul 2025, consistent with Apr-2025 FID
  already on file); Phase II stays proposed (blue). Carries forward the
  2026-07-10 finding that was never applied.
- Thailand dead/shelved fleet re-confirmed: Chana cancelled, Gulf of Thailand FSRU
  cancelled, Songkhla FSRU cancelled, Surat Thani FSRU shelved (all blue or
  ref-repair only).
- Discovery: 15 candidates examined across both countries, **zero missing terminals**;
  gem.wiki coverage cross-check clean in both; 5 dormant sites all still dead;
  no new entities.

**QC gate results:**

- gem.wiki/GEM/abarrelfull citation scan: clean (3 prose mentions in disc qa only).
- Bare-homepage scan: clean. No new entities → no Postgres entity re-check needed.
- url_verifier spot-check: 6 non-blue records, all citations verified (3 initial
  FAILs were weak-token artifacts, resolved with page-matched tokens).
- **Caught + fixed:** the SG update agent had "verified" `slng.com.sg/node/317`
  with the bare token `['5']` (weak-token false positive); orchestrator re-verified
  the page's actual content via Wayback (Oct-2023 release: FSRU concept, 5 MTPA,
  "operational by end of decade") — supports Capacity/Owner/StartDate uses, not
  construction; the construction claim rests on the 3 other refs (all PASS).
- **Caught + fixed:** first build's REF-DROP guard flagged 13 undeclared existing-URL
  drops across 10 value-shape records (the shape `audit_ref_drops.py` can't see —
  tool gap flagged below). All 13 probed: 7 live URLs merged back per SOP §7.2a
  (node/317 ×2, 2b1stconsulting ×2, bangkokpost, eeco.or.th, dx.doi.org),
  5 declared dead (EMA cmsmedia PDF 404; `Gas_Terminal_Development.aspx`
  200-but-content-gone ×4), 1 bot-blocked-unverifiable DOI kept + qa note
  (OnePetro 429, no Wayback snapshot). Declared drops audit: 8/8 `drop_ok_dead`.
- fsru_sync_check.py: gem_only mode (no carrier backend), graceful skip.

**Follow-ups:**

- ~~`scripts/audit_ref_drops.py` value-shape support~~ — DONE same session:
  the tool now audits both record shapes like the guard (`--gem-csv` reads the
  target ref cell for value records) and skips already-declared drops;
  regression re-run on this staging dir is clean. (This batch's 13 value-shape
  drops were repaired by hand at the QC gate before the tool was extended.)
- Unresolved TH capacity conflict (5 vs 8 mtpa) left as qa item for reviewer.
