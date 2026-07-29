# 2026-07-17 — ref-drop repair across all built (unapplied) batches

## Trigger

User caught the Al Zour miss in the gulf-turkiye exhaustive-update workbook: the staged
`FacilityType [ref]` replaced the existing, live citation
(`hydrocarbons-technology.com` → 301 → `offshore-technology.com`, bot-blocked 403 misread
as dead) with only the agent's new LNG Prime URL. Root causes: (1) SOP/brief encoded
replace semantics for `[ref]` edits, not merge; (2) the bot-block ≠ dead / Wayback rule
lived only in session memory, never in the brief subagents read; (3) `url_verifier.py`
had no Wayback fallback, so a live bot-blocked URL structurally could not pass; (4) no
build guard flagged dropped old URLs. 31/34 gulf-turkiye ref edits dropped ≥1 old URL.

## Changes (permanent)

- `scripts/url_verifier.py` — Wayback fallback on 401/403/429 + Cloudflare/paywall
  interstitials; a snapshot content-check pass verifies the LIVE URL (`--no-wayback` to
  disable).
- `scripts/audit_ref_drops.py` — NEW: audits staged `[ref]` edits that dropped old-value
  URLs; classifies each (rehosted_same_doc / restore_live / restore_botblocked_wayback /
  drop_ok_dead / drop_ok_content_gone / dropped_unverifiable); `--apply` merges restores
  back (existing-first) + stamps `dropped_urls_dead`.
- `scripts/build_review_package.py` — `REF-DROP:` guard: warns on any `[ref]` record whose
  new_value drops an old_value URL without a `dropped_urls_dead` declaration;
  `dropped_urls_dead` added to STAGED_KEYS.
- Update SOP §7.2 (bot-block ≠ dead) + NEW §7.2a (merge semantics, declared drops);
  `_country_agent_brief.md` hard rule + record schema; CLAUDE.md hard-requirements bullet;
  `scripts/README.md` entries.

## Repair (staged data)

Audited every built-unapplied batch (`*.updates.json`); applied restores and rebuilt the
affected update workbooks with fresh timestamps. Per-URL classifications in
`scripts/work/ref_drop_audit_<slug>.json`.

| batch | ref edits dropping URLs | restored | rebuilt workbook |
|---|---|---|---|
| gulf-turkiye | 31 | 4 (Al Zour ×3 → offshore-technology.com, Wayback-verified; Mina Al-Ahmadi ×1) | `lng_terminals_batch_20260717_0937_ET_gulf-turkiye_exhaustive_update.xlsx` |
| sw-europe | 97 rec / 106 URLs | 8 (Gibraltar S&P ×2, Alexandroupolis enerdata, Piombino/Ravenna Reuters ×3, Sines maps ×2) | `lng_terminals_batch_20260717_0951_ET_sw-europe_exhaustive_update.xlsx` |
| south-asia-iran | 47 rec / 52 URLs | 5 URLs / 4 rec (Payra ×2, Summit Owner ×2, Hambantota manifoldtimes) | `lng_terminals_batch_20260717_0947_ET_south-asia-iran_exhaustive_update.xlsx` |
| vietnam | 41 rec / 44 URLs | 2 (Thi Vai pvgas Capacity, Bac Lieu lngprime ConstructionDate) | `lng_terminals_batch_20260717_0948_ET_vietnam_exhaustive_update.xlsx` |
| levant-iraq | 21 rec / 22 URLs | 5 (Cyprus Reuters ×2, Sheikh Sabah jordantimes ×3) | `lng_terminals_batch_20260717_0952_ET_levant-iraq_exhaustive_update.xlsx` |
| africa | 1 | 0 (the one drop was genuinely dead; declaration stamped) | no rebuild needed |

(americas / europe / oceania / middleeast audited clean — 0 drops.)

Mirror cleanup after restore: 8 records (Cyprus ×2, Sheikh Sabah ×3, Piombino ×1,
Ravenna ×2) had staged a `web.archive.org` snapshot of the SAME article the restore
brought back live — live URL + its own snapshot is one source (mirror rule), so the
archive copy was dropped. All 8 ended up value-identical to the DB (or an http→https
upgrade): they now stand as blue re-verified-unchanged rows, not replacements.
sw-europe/levant-iraq were rebuilt once more after this cleanup (final filenames above;
intermediate 0946/0949 builds superseded, prune at will).

`dropped_unverifiable` (bot-blocked, no usable Wayback snapshot — cannot pass
verification, left dropped; the agents' replacement refs stand) — 22 URLs total, listed
per batch in the audit reports: south-asia-iran 12 (dhakatribune Summit-Matarbari,
manifoldtimes Hambantota, dailynews.lk archives), sw-europe 5 (S&P Global Thrace,
electrogas.com.mt Delimara, cabildo.grancanaria.com), vietnam 4 (marketscreener Son My,
S&P Global Thi Vai), levant-iraq 1 (ekathimerini Cyprus FSRU).

## Outcome

- All six audited batches repaired in staging (restores merged existing-first;
  `dropped_urls_dead` declarations stamped on every legitimate drop, so the REF-DROP
  guard builds clean). americas / europe / oceania / middleeast audited clean — 0 drops,
  nothing to do.
- gulf-turkiye, sw-europe, south-asia-iran, vietnam, levant-iraq: workbooks rebuilt with
  fresh timestamps (filenames in the table above) + recalc OK; meta.json built stamps
  updated. africa: staging declaration only — no workbook content change, no rebuild.
- Al Zour FacilityType [ref] now carries BOTH offshore-technology.com (existing,
  Wayback-verified) and lngprime.com (new) — the original miss, verified in the rebuilt
  gulf-turkiye workbook.
