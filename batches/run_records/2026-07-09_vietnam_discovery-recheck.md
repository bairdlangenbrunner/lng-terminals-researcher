# 2026-07-09 — Vietnam discovery re-check (final miss sweep)

## Plan

User: "do one more discovery pass for Vietnam and check whether I've potentially missed any new terminals. I am now done with the research and the database is up-to-date." A verification-style Discovery run against a fresh export, after the 2026-07-02 exhaustive-update+discovery batch and its 2026-07-09 follow-ups (timeline punts resolved; Quang Trach II withdrawn as power-plant≠terminal).

Setup (deterministic):
- Fresh pull: `gem_query.py --all-fields lng` → 1,290 rows; colmap re-derived. **31 distinct Vietnam terminals** (was 29 pre-batch; Cong Thanh + Dung Quat landed; Quang Trach II correctly ABSENT — the withdrawal was applied; Vung Ang present as proposed).
- `completeness_sweep.py --country Vietnam`: Vietnam is covered (no coverage gap); **12 dead sites** to revival-check (0 dead 5+ y).
- `dedup_index.py` built.

Research: 3 parallel subagents — (1) Ring A regulatory + PDP8 reconciliation; (2) Ring B trade press + Ring C sponsor/upstream IR; (3) dormant-revival watch (12 sites) + gem.wiki coverage cross-check. All given the 31-terminal reference list + scope gates (marine cross-border; power-plant≠terminal) + anti-circularity rules.

## Status / outcomes

**One genuine miss found: Hiep Phuoc LNG Terminal (HCMC).**

- Surfaced by the Ring A / PDP8 pass. HPPC (chairman Le Van Tam) is upgrading the existing 40,000 DWT petroleum port at Hiep Phuoc IP (Nha Be, HCMC, Soai Rap river) into a dedicated LNG **import** port — own jetty (carriers 10,000-75,000 m³) + marine unloading arms + onshore storage + regas — feeding the 2,700 MW Hiep Phuoc LNG plant (Phase 1 1,200 MW). First HCMC terminal in GEM; distinct from the Ba Ria-Vung Tau terminals.
- **Scope gate resolved BEFORE staging** (not stage-with-doubt, unlike the Quang Trach II miss): it is a marine import terminal because LNG carriers berth and discharge at Hiep Phuoc's own jetty — categorically unlike Quang Trach II (piped regas from Vung Ang, no berth). Two independent sources, one primary: **baochinhphu.vn** (Government of Vietnam paper, Wayback snapshot — "cảng nhập LNG" PASS) + **vir.com.vn** ("import terminal" + "40,000" PASS). Concrete step well past threshold: revised PDP8 (Decision 768, 2025-04-15); HCMC People's Committee approval; **EVN–HPPC PPA signed + groundbreaking 2026-03-26** (vietnamenergy.vn + en.evn.com.vn PASS); PM Nov-2025 acceleration directive; plant ~60% civil complete.
- **Status = proposed** (terminal component approved but its own construction not independently confirmed; power plant broke ground, terminal is pre-construction — honest classification, reviewer may upgrade).
- **Entity reuse**: Owner = existing entity **100000003214 "Hiep Phuoc Power"** (via Postgres entity_history; the `--remote` "not found" was the known degraded-Heroku false negative). No new entity staged.
- **Capacity left blank**: developer states 2.15 mtpa / 150,000 m³ / 40,000 DWT jetty, but only on HPPC's own site (self-source) — not independently corroborated (qa note).
- Dedup: matcher gave manual_review 0.656 vs Cat Hai FSRU (Hai Phong) — false geographic match; judged discovery_new by hand.

**Everything else clean — no other missed terminals.**
- **Ring A / PDP8**: every other LNG-power project maps to one of the 31 terminals or is a power plant fed by an existing terminal (Nhon Trach 3&4→Thi Vai; Quang Trach II→Vung Ang; Hai Phong 4,800 MW→Haiphong FSRU; etc.).
- **Ring B/C**: no stageable miss. "Nam Do Son FSRU" (Vingroup) dedups to the tracked **Haiphong FSRU** (T100001061416, Vingroup/VinEnergo, same city/coords) — a progress-update, not a new terminal. Vung Tau FSRU (PV Gas) reaffirmed as monitor (below threshold).
- **Dormant-revival (12 sites)**: no different-sponsor/different-design new project at any dead site. Stavian Chan May has a same-sponsor revival signal → Update, not discovery.
- **gem.wiki cross-check**: 18 wiki pages all map to the 31 rows; "Thanh Hóa"=Nghi Son, "North Central"=Vung Ang. No Durban-class gap. (Hiep Phuoc is on gem.wiki only as a *power station*, not a terminal page — which is why the wiki check didn't catch it; PDP8 reconciliation did.)

**Update-side signals flagged to qa (NOT staged — discovery pass):** Haiphong FSRU possible construction→shelved (Vingroup ~Apr-2026 proposal to scrap the LNG plant for renewables); Northern Vietnam LNG Terminal (JAPEX exit ~Mar 2026, reinforces shelved); Stavian Chan May (same-sponsor revival → consider shelved→proposed); Dung Quat sponsor confirm.

## Deliverable

- `batches/lng_terminals_batch_20260709_1810_ET_vietnam_discovery.xlsx` — sheets README / new_terminals(1) / monitor_list(1 new + 26 prior) / qa_review(6). recalc OK, zero formula errors.
- Staging: `batches/staging/vietnam-discovery/` (staged_new_terminals / staged_qa_review / staged_monitor_list / empty staged_entity_additions / prior_monitor_list).
- URL gate honest: all 4 staged [ref] URLs PASS url_verifier with the claimed value as token; anti-circularity grep clean (no gem.wiki / globalenergymonitor).
- Monitor store updated → 26 durable entries (Vung Tau matched existing; 0 promoted).
- `docs/country_notes/vietnam.md` updated (PDP8-as-discovery-backbone, Hai Linh/Le Van Tam cluster, Hiep Phuoc, province mergers, count 31).
