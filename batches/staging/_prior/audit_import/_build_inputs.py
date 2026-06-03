"""Builds the staged_*.json inputs for the ChatGPT-audit import UPDATE batch.

Provenance: records distilled from the user's ChatGPT "LNG Research Assistant"
audit (Google Doc 1IWGXG...), matched against the fresh GEM export and
URL-verified by per-cluster agents on 2026-06-03. Run from anywhere:
    python batches/staging/_prior/audit_import/_build_inputs.py
Writes the five staged_*.json files next to this script.
"""
import json
from pathlib import Path

OUT = Path(__file__).parent
RI = "AI-draft (ChatGPT-audit import)"

# ---------------------------------------------------------------- updates
updates = []

# --- Woodside Louisiana LNG: Parent restructuring (GENUINE, green) — project-level, both units
_wls_parent_old = "Woodside Energy Group Ltd [60.0%]; Stonepeak Partners LP"
_wls_parent_new = ("Woodside Energy Group Ltd [54.0%]; Stonepeak Partners LP [40.0%]; "
                   "The Williams Companies Inc [6.0%]")
_wls_notes = ("Two-tier structure from primary ASX docs: HoldCo (Louisiana LNG LLC) is 90% Woodside / "
              "10% Williams and owns 60% of InfraCo (= GEM Owner 'Louisiana LNG Infrastructure LLC'); "
              "Stonepeak holds the other 40% of InfraCo. Effective InfraCo interests: Woodside 54%, "
              "Stonepeak 40%, Williams 6%. GEM Parent is stale (omits Williams; Stonepeak has no %). "
              "Williams is also 80% of Driftwood Pipeline LLC (pipeline-level, excluded from terminal owner).")
for uid, uname in [("G100002021901", "Phase 1 (T1-T3)"), ("G100002021902", "Phase 2 (T4-T5)")]:
    updates.append({
        "terminal_id": "T100000130219", "unit_id": uid,
        "terminal_name": "Woodside Louisiana LNG Terminal", "unit_name": uname,
        "country": "United States", "field_name": "Parent",
        "old_value": _wls_parent_old, "new_value": _wls_parent_new,
        "confidence": "green", "source_tier": "Tier 1 — sponsor regulatory/IR (Woodside ASX)",
        "ref_field": "Owner [ref]",
        "ref_urls": [
            "https://www.woodside.com/docs/default-source/asx-announcements/2025/038-woodside-completes-louisiana-lng-sell-down-to-stonepeak.pdf",
            "https://www.woodside.com/docs/default-source/asx-announcements/2025/woodside-announces-louisiana-lng-partnership-with-williams.pdf",
        ],
        "source_notes": _wls_notes,
        "scope_note": "Project-level — apply to BOTH unit-rows. Reviewer: confirm effective-% vs literal-tier encoding; add Stonepeak % and Williams entity ID to the Parent GEM Entity ID cell.",
        "researcher_initials": RI,
    })

# --- Port Arthur LNG Phase 2: Parent consortium (YELLOW, single-source) — T3 + T4
_pa_parent_old = "KKR & Co. Inc; Sempra; Sempra Infrastructure Partners LP"
_pa_parent_new = ("Sempra Infrastructure Partners LP; Blackstone Inc; KKR & Co. Inc; "
                  "Apollo Global Management Inc; The Goldman Sachs Group Inc")
_pa_notes = ("Phase 2 (T3/T4) FID Sept 2025 announced new equity: Sempra Infrastructure 50.1%; a "
             "Blackstone Credit & Insurance-led consortium 49.9% (with KKR, Apollo-managed funds, and "
             "Private Credit at Goldman Sachs Alternatives). GEM Parent still shows Phase-1-era ownership. "
             "Consortium membership is loosely worded in the source and percentages are single-source — do "
             "NOT hard-code %; run entity_lookup before adding any entity. Yellow pending corroboration.")
for uid, uname in [("G100002023703", "T3"), ("G100002023704", "T4")]:
    updates.append({
        "terminal_id": "T100000130237", "unit_id": uid,
        "terminal_name": "Port Arthur LNG Terminal", "unit_name": uname,
        "country": "United States", "field_name": "Parent",
        "old_value": _pa_parent_old, "new_value": _pa_parent_new,
        "confidence": "yellow", "source_tier": "Tier 2 — sponsor press release / project site",
        "ref_field": "Owner [ref]",
        "ref_urls": [
            "https://portarthurlng.com/sempra-announces-strategic-transactions-advancing-goal-of-building-leading-u-s-utility-growth-business/",
            "https://semprainfrastructure.com/what-we-do/lng/port-arthur-lng/",
        ],
        "source_notes": _pa_notes,
        "scope_note": "Phase 2 (T3+T4) — apply to both unit-rows. Phase 1 (T1/T2) ownership is a separate question (see qa: possible missing ConocoPhillips parent).",
        "researcher_initials": RI,
    })

# --- West Delta LNG: Offshore flag (GENUINE, green) — data-consistency fix
updates.append({
    "terminal_id": "T100000130987", "unit_id": "G100002098701",
    "terminal_name": "West Delta LNG Deepwater Port Terminal", "unit_name": "--",
    "country": "United States", "field_name": "Offshore",
    "old_value": "", "new_value": "True",
    "confidence": "green", "source_tier": "primary/regulatory (MARAD Federal Register) + sponsor site",
    "ref_field": "Location [ref]",
    "ref_urls": [
        "https://www.govinfo.gov/content/pkg/FR-2019-09-26/pdf/2019-20929.pdf",
        "https://lng21group.com/west-delta/",
    ],
    "source_notes": ("MARAD/USCG deepwater-port notice (FR-2019-20929): an offshore deepwater port with thirteen "
                     "fixed bridge-connected platforms offshore Louisiana. GEM convention encodes deepwater ports "
                     "as Offshore=True / Floating='' (cf. Gibbstown, Gulf Gateway); GEM's Offshore is currently "
                     "blank — a consistency fix, not a new finding. Floating stays blank (fixed, not floating). "
                     "FR PDF content confirmed via pdftotext (url_verifier has no PDF text path)."),
    "scope_note": "Single-unit terminal. Capacity unchanged (FR nominal 5.0 mtpa; 6.1 'optimized' is a sponsor figure → wiki).",
    "researcher_initials": RI,
})

# --- BLUE re-verifications (lead already matches GEM; re-checked this batch) ---
def blue(tid, uid, tname, uname, country, field, val, ref_field, urls, note):
    return {"terminal_id": tid, "unit_id": uid, "terminal_name": tname, "unit_name": uname,
            "country": country, "field_name": field, "old_value": val, "new_value": val,
            "confidence": "blue", "source_tier": "re-verified (sponsor/operator/regulatory)",
            "ref_field": ref_field, "ref_urls": urls, "source_notes": note,
            "scope_note": "Unchanged — re-verified this batch.", "researcher_initials": RI}

# Texas LNG — all leads already in GEM
for field, val, rf in [("FIDStatus", "Pre-FID", "FIDYear [ref]"), ("FIDYear", "2026", "FIDYear [ref]"),
                       ("LatestPlannedStartYear", "2030", "StartDate [ref]"), ("Capacity", "4.00", "Capacity [ref]")]:
    updates.append(blue("T100000130238", "G100002023801", "Texas LNG Terminal", "T1-T2", "United States",
                        field, val, rf, ["https://www.texaslng.com/"],
                        "Lead matches GEM (Pre-FID / FIDYear 2026 / 4.0 mtpa / start 2030). texaslng.com PASSED verification. NOTE: $5.7B is a bank-debt package, NOT capex — Cost left unchanged (see qa)."))

# Alaska LNG — ownership + FID already current (Owner is project-level across 3 units)
for uid, uname in [("G100002020601", "T1"), ("G100002020602", "T2"), ("G100002020603", "T3")]:
    updates.append(blue("T100000130206", uid, "Alaska LNG Terminal", uname, "United States",
                        "Owner", "Alaska Gasline Development Corp [25%]; Glenfarne Alaska LNG LLC [75%]",
                        "Owner [ref]", ["https://alaska-lng.com/"],
                        "Lead's Glenfarne 75% / AGDC 25% already in GEM. Conoco/Exxon/Hilcorp/Great Bear are feedgas counterparties, NOT equity — correctly absent."))
updates.append(blue("T100000130206", "G100002020601", "Alaska LNG Terminal", "T1", "United States",
                    "FIDYear", "2027", "FIDYear [ref]", ["https://alaska-lng.com/"],
                    "Lead's terminal FID 2027 already in GEM (pipeline FID 2026 is a separate asset). Exports ~2031 = LatestPlannedStartYear."))

# Port Kembla FSRU — operator/vessel roles already correct
for field, val, rf, urls, note in [
    ("Operator", "Reganosa Servicios", "Operator [ref]",
     ["https://www.reganosa.com/en/squadron-energy-chooses-reganosa-to-operate-and-maintain-a-new-lng-terminal-in-australia/"],
     "Squadron Energy chose Reganosa Servicios to operate the onshore terminal. Squadron modeled via Parent=Tattarang."),
    ("FloatingVesselName", "Höegh Galleon", "FloatingVesselName [ref]", ["https://hoeghevi.com/about/fleet/"],
     "FSRU sync touchpoint; IMO not stated on fleet page (leave unconfirmed)."),
    ("VesselOwner", "Höegh Evi", "VesselOwner [ref]", ["https://hoeghevi.com/about/fleet/"],
     "Owner's own fleet page (single source); vessel legal-entity ownership stays single-source."),
    ("VesselOperator", "Höegh Evi", "VesselOperator [ref]", ["https://hoeghevi.com/about/fleet/"], ""),
]:
    updates.append(blue("T100000130606", "G100002060600", "Port Kembla FSRU", "--", "Australia",
                        field, val, rf, urls, note))

# Geelong FSRU — Pre-FID confirmed
updates.append(blue("T100000130982", "G100002098200", "Geelong FSRU", "--", "Australia",
                    "FIDStatus", "Pre-FID", "FIDYear [ref]",
                    ["https://www.argusmedia.com/en/news/2166473-viva-adds-partners-to-geelong-lng-import-terminal-plan"],
                    "Argus: Viva securing partners — consistent with Pre-FID. 'winter 2028' start year NOT re-verified (only source paywalled) — see qa."))

# Pluto T2 — capacity confirmed
updates.append(blue("T100000130338", "G100002033802", "Pluto LNG Terminal", "T2", "Australia",
                    "Capacity", "5.00", "Capacity [ref]",
                    ["https://www.ogj.com/pipelines-transportation/lng/article/17276335/woodside-lets-feed-contracts-for-pluto-lng-trains-2-3",
                     "https://lngprime.com/australia-and-oceania/woodside-bechtel-kick-off-work-on-second-pluto-lng-train/59909/"],
                    "5.0 mtpa confirmed (OGJ + LNG Prime). Adds LNG Prime as corroboration."))

# Barbers Point FSRU — genuine small fix surfaced by the discovery dedup (missing alias)
updates.append({
    "terminal_id": "T100001083401", "unit_id": "G100001094271",
    "terminal_name": "Barbers Point FSRU", "unit_name": "--", "country": "United States",
    "field_name": "OtherNames",
    "old_value": "Hawaii LNG Terminal, Longboard LNG Terminal",
    "new_value": "Hawaii LNG Terminal, Longboard LNG Terminal, Kalaeloa LNG",
    "confidence": "yellow", "source_tier": "Tier 2 — trade press", "ref_field": "OtherNames [ref]",
    "ref_urls": ["https://lngprime.com/americas/jera-seeks-ok-to-start-pre-filing-process-for-hawaii-lng-project/186938/"],
    "source_notes": "Discovery dedup confirmed this terminal already exists in GEM; the audit surfaced the 'Kalaeloa LNG' alias (the project sits at Kalaeloa/Barbers Point) which GEM's OtherNames lacks. Low-stakes alias add; verify against a 2nd source before applying.",
    "scope_note": "Alias addition only — terminal already in GEM (not a new terminal).",
    "researcher_initials": RI,
})

# ---------------------------------------------------------------- qa_review
def qa(cat, tid, uid, tname, issue, sev, action):
    return {"category": cat, "terminal_id": tid, "unit_id": uid, "terminal_name": tname,
            "issue": issue, "severity": sev, "suggested_action": action, "researcher_initials": "AI-draft"}

qa_items = [
    # Algeria
    qa("verified-no-change", "T100000130243", "G100002024300", "Arzew-Bethioua LNG Terminal",
       "Audit flagged operating total should be 20.8 not 21.7 mtpa (GL4Z retired). GEM ALREADY marks GL4Z retired (StopYear 2010). 21.7 = computed TotExport... (incl. retired); operating-only = 20.8. No GEM error.",
       "low", "No edit. TotExport... is a computed/read-only column. Close as verified no-change."),
    qa("verified-no-change", "T100000130244", "G100002024407", "Skikda LNG Terminal",
       "Audit flagged operating capacity should be 4.5 not 11.0 mtpa (legacy trains retired). GEM ALREADY marks all six legacy trains retired; only GL1K Rebuild operates at 4.5. 11.0 = computed total-incl-retired. No GEM error.",
       "low", "No edit. Close as verified no-change."),
    qa("conflicting-data", "T100000130244", "G100002024407", "Skikda LNG Terminal",
       "GL1K LNG storage: Sonatrach complex page ~246,000 m3 (one 150k + two 48k tanks) vs GIIGNL 2025 150,000 m3 (the single Sinopec-built tank). Reconcilable, not contradictory. GEM has NO storage-volume column.",
       "low", "No GEM field maps to storage volume → capture as a [CONFLICTING DATA] wiki note. 150k corroborated by committed GIIGNL 2025 PDF + Sinopec-deal source."),
    qa("needs-follow-up", None, None, None,
       "Audit open item 'Ertugrul Gazi FSRU loaned to Egypt?' — researched: it is a Turkish/Botaş FSRU at Dörtyol; Egypt (not Algeria) was in borrowing talks. No Algeria/Sonatrach link; no GEM Algeria record. Audit mis-associated it.",
       "low", "No Algeria action. Out of scope for this cluster."),
    qa("negative-result", "T100000130244", None, "Skikda LNG Terminal",
       "Audit open item: no gas-fired power plant found inside/contractually supplied by either Algeria terminal.",
       "low", "Confirms GEM's blank PowerPlantsSupplied for both. Logged as negative result."),
    # Woodside / Rio Grande
    qa("ownership_encoding_review", "T100000130219", "G100002021901, G100002021902", "Woodside Louisiana LNG Terminal",
       "Staged Parent update uses EFFECTIVE interests (Woodside 54 / Stonepeak 40 / Williams 6) from a two-tier HoldCo->InfraCo structure. GEM Owner (InfraCo) is correct. Existing researcher note already warns ownership 'may need work'.",
       "medium", "Reviewer to choose effective-% vs literal-tier encoding; add Stonepeak % + Williams ID to Parent GEM Entity ID. Williams 80% of Driftwood Pipeline is pipeline-level (excluded)."),
    qa("stale_timing_no_verified_source", "T100000130219", "G100002021902", "Woodside Louisiana LNG Terminal",
       "Phase 2 LatestPlannedStartYear=2028 looks stale (Phase 2 still proposed; first LNG target 2029). No verified current source for a Phase-2 start year this batch (project page 403).",
       "medium", "Do NOT change the year without a current source. Pull a fresh Woodside/FERC/DOE source for Phase-2 timing."),
    qa("no_change_lead_already_applied", "T100000130239", "G100002023904, G100002023905", "Rio Grande LNG Terminal",
       "All Rio Grande leads already in GEM: T4/T5 FID 2025 + construction; T6 Pre-FID/FERC pre-filing; T6-T8 proposed; CCS abandonment already in CCSNotes (read-only column).",
       "low", "No edit. CCS is read-only/out-of-scope → wiki only. Confirm T4/T5 construction timeline entries exist in the live DB."),
    # Port Arthur / Plaquemines / CP2
    qa("no_op_lead_already_applied", "T100000130237", "G100002023703, G100002023704", "Port Arthur LNG Terminal",
       "Lead's Phase 2 T3/T4 proposed->construction + FID 2025 + starts 2030/2031 ALREADY in GEM. Only the Phase-2 equity restructuring is new (staged yellow).",
       "low", "No status/FID edit. Optionally re-verify."),
    qa("owner_phase1_clarification", "T100000130237", "G100002023701, G100002023702", "Port Arthur LNG Terminal",
       "Lead: Phase 1 = ConocoPhillips 30% direct + KKR 42% indirect. GEM T1/T2 Parent omits ConocoPhillips despite GEM's own ref citing the 30% stake. ConocoPhillips EXISTS in GEM entity system (E100001011247).",
       "medium", "Reviewer: consider adding ConocoPhillips Co (E100001011247) to T1/T2 Parent. Not auto-staged (single-source %; may be a deliberate modeling choice)."),
    qa("giignl_vs_gem_capacity_conflict", "T100000130242", "G100002024201", "Plaquemines LNG Terminal",
       "GIIGNL 2026 lists Plaquemines Phase 1 at 11.3 MTPA; GEM has 13.33 nameplate (matches VG/DOE). Definitional difference (train count / in-service convention), NOT a GEM error.",
       "low", "No GEM edit. Do NOT bump GEM down to 11.3. Record as a known GIIGNL-vs-GEM gap."),
    qa("peak_vs_nameplate", "T100000130242", "G100002024201", "Plaquemines LNG Terminal",
       "FERC peak uprate 24->27.2 MTPA (Feb 2025) and a requested 35.0 MTPA — both PEAK, no new facilities. GEM tracks nameplate.",
       "low", "Do NOT bump nameplate from a peak figure. Peak-uprate history -> wiki Background only."),
    qa("expansion_already_in_gem", "T100000130242", "G100001064081", "Plaquemines LNG Terminal",
       "Lead's 16-block brownfield expansion (up to 31 MTPA peak) ALREADY in GEM as proposed unit 'Expansion (T37-60)' with an inferred 17.78 nameplate. Not a discovery gap.",
       "low", "No new unit. Corroborate the inferred nameplate when VG publishes one."),
    qa("discovery_candidate_already_in_gem", "T100000130973", "G100001094165", "CP2 LNG Terminal",
       "Lead's 'CP2 Phase 3 ~10 MTPA peak discovery candidate' ALREADY in GEM as proposed 'Phase 3 (T37-48)' (6.4 nameplate). Phase 2 already FID 2026. Not a discovery gap.",
       "low", "No new unit. 10 MTPA is peak; GEM uses 6.4 nameplate (single-source)."),
    # Glenfarne / Alaska / offshore
    qa("cost_staleness", "T100000130238", "G100002023801", "Texas LNG Terminal",
       "GEM Cost=$3.5B (2020) may be stale, but the prominent $5.7B is a BANK-DEBT financing package, NOT terminal capex — must NOT be entered as Cost. No verified updated capex figure available.",
       "medium", "Do NOT set Cost=5.7B. If refreshing capex, find a sourced post-2020 EPC value and update Cost+CostYear together."),
    qa("unverifiable_lead_parent", "T100000130922", "G100002092201", "Qilak LNG Terminal",
       "Lead: Parent -> Lloyds Energy. Lloyds Energy DOES exist in GEM (Lloyds Energy Group LLC, E100002004519) but NEITHER supplied source confirms the Qilak<->Lloyds link (qilaklng.com is a dead domain HTTP 404; Aker Arctic PDF doesn't mention Lloyds). Not staged.",
       "medium", "Find a working source naming Lloyds as Qilak's parent before changing Parent from 'Qilak LNG Inc'. If confirmed, use existing entity E100002004519 (do not create)."),
    qa("unverifiable_lead_fidyear", "T100000130922", "G100002092201", "Qilak LNG Terminal",
       "Lead says FIDYear 2025 is unsupported. GEM FIDYear=2025 is cited to a 2022 deck (predates it). No source confirms a 2025 FID. Not auto-blanked.",
       "medium", "Reviewer: blank FIDYear (+ref) or replace with a sourced value. Project shows dormancy (dead homepage)."),
    qa("dead_url_stale_project", "T100000130922", "G100002092201", "Qilak LNG Terminal",
       "qilaklng.com returns HTTP 404 (lapsed domain) and is cited in GEM's Location [ref]. A dead sponsor homepage is a stale-project signal for a proposed/pre-FID terminal.",
       "low", "Replace/remove the dead ref; run a stale check (candidate for triage/monitor; possibly inferred-shelved)."),
    qa("data_consistency_offshore_flag", "T100000130987", "G100002098701", "West Delta LNG Deepwater Port Terminal",
       "West Delta Offshore blank -> staged True. Peer 'Texas GulfLink Deepwater Port' ALSO has Offshore blank — same defect class.",
       "low", "Accept West Delta Offshore=True; separately sweep deepwater-port terminals for blank Offshore and backfill (Texas GulfLink at minimum)."),
    qa("tooling_url_verifier_pdf", None, None, None,
       "url_verifier.py has no PDF text-extraction path → false negatives on EVERY .pdf URL (govinfo FR notice, Woodside ASX PDFs, DOE/Alaska PDFs all returned 'missing content' despite HTTP 200). Content confirmed manually via pdftotext.",
       "low", "Tooling: add a pdftotext fallback to url_verifier.py for application/pdf responses (the GIIGNL pipeline already depends on pdftotext)."),
    # Australia
    qa("status_review_timeline_pull_required", "T100000130331", "G100002033101", "Darwin LNG Terminal",
       "Status question: GEM shows idled; 2026 is a restart-then-pause sequence (operating ~25 Jan 2026 on Barossa; temporary FPSO-issue shutdown ~late Feb 2026; restart targeted ~Apr 2026). GEM already encodes the churn (StopYear 2026, ActualStartYear2 2026). fetch_timeline.py returned HTTP 404 (its live-DB endpoint appears stale), so the ordered timeline could not be pulled this batch.",
       "high", "Reconcile in the live DB UI: confirm whether 'idled' is still current and whether the ~Apr 2026 restart materialized. Do NOT edit Status directly. NOTE tooling: fetch_timeline.py 404s — its endpoint needs updating."),
    qa("value_confirmed_source_unverifiable", "T100000130982", "G100002098200", "Geelong FSRU",
       "Lead's 'first gas winter 2028' matches GEM LatestPlannedStartYear=2028, but the figure traces to a Reuters article that FAILED verification (HTTP 401). FIDStatus=Pre-FID re-verified separately (Argus PASSED).",
       "low", "Did NOT re-verify the 2028 start-year cell (no verified source). Confirm 2028 against Viva IR / planning.vic.gov.au before treating it as re-verified."),
    qa("historical_not_active_confirmed", "T100000130338", "G100002033803", "Pluto LNG Terminal",
       "Lead: Pluto Train 3 (2011 FEED) is historical/conceptual, not active. GEM already models T3 as cancelled (inferred). Lead and GEM agree.",
       "low", "No field change. Do not reactivate a T3 unit."),
    qa("url_verification_failures", None, None, None,
       "URLs dropped (failed the gate, no citation invented): NextDecade investor pages (HTTP 000 host unreachable), Reuters CCS/JERA/Gunvor/ConocoPhillips/east-coast (401 paywall), Woodside project page + VG IR + BusinessWire + glenfarnegroup bank-group (403 bot-block), Rigzone Darwin (202), EIA Algeria SPA pages, qilaklng.com (404 dead).",
       "low", "Where a primary source was needed despite a block, a verified substitute was used (Federal Register for VG; sponsor pages; committed GIIGNL PDF). Re-fetch blocked URLs from a browser if needed."),
    # Discovery dedup outcome — all three audit "new terminal" leads already exist in GEM
    qa("already_in_gem", "T100001083399", "G100001094269", "Cook Inlet FSRU",
       "Audit 'new terminal' lead Cook Inlet LNG FSRU is ALREADY in GEM (proposed import, Owner Cook Inlet LNG LLC, west Cook Inlet AK). NOT new. Lead adds detail to verify/fold: Glacier Oil & Gas partner; ~22 Bcf/y sendout (convert — verify before recording); moored beside the Osprey platform; first gas mid-2029; FERC+USCG sought.",
       "low", "Route to Update, not Discovery. Source-search + verify the lead detail before applying."),
    qa("already_in_gem", "T100001083401", "G100001094271", "Barbers Point FSRU",
       "Audit 'new terminal' lead Barbers Point / Hawaii LNG is ALREADY in GEM (proposed import, Owner Longboard LNG, Parent Chubu/TEPCO, 1 mtpa, ProposalYear 2026). NOT new. Missing 'Kalaeloa LNG' alias (staged as a yellow OtherNames update). Verify storage 138-174k m3, single-point mooring + ~3-mi pipeline, FERC pre-filing 15 May 2026, online Q1 2030; run entity_lookup on 'JERA Americas'/'Longboard TerminalCo' before any owner change.",
       "low", "Route to Update. Opposition / linked power-plant context captured in wiki_updates."),
    qa("already_in_gem", "T100001061236", "G100001070151", "ST LNG FLNG Terminal",
       "Audit 'new terminal' lead ST LNG (offshore TX export) is ALREADY in GEM (proposed export, offshore+floating, 4 phases x2.1 = 8.4 mtpa, Owner ST LNG LLC, Parent Tak Investments) — GEM already models it as 4x2.1 exactly as the lead suggested. NOT new. Fold detail: Brazos OCS Lease Block 476, ~10.4 nm offshore, converted-carrier FSUs, MARAD app June 2025, 5.5-mi pipeline lateral, pre-FID.",
       "low", "Route to Update. FSRU/FSU sync rule applies if vessel records exist."),
]

# ---------------------------------------------------------------- wiki_updates
def wiki(country, tid, tname, uid, topic, text, status, urls):
    return {"country": country, "terminal_id": tid, "terminal_name": tname, "unit_id": uid or "",
            "topic": topic, "wiki_text": text, "verification_status": status,
            "source_urls": urls, "researcher_initials": "AI-draft"}

wiki_items = [
    wiki("Algeria", "T100000130244", "Skikda LNG Terminal", "G100002024407", "GL1K LNG storage capacity conflict",
         "Reported GL1K storage differs by source: Sonatrach's complex page describes ~246,000 m3 total (one 150,000 m3 tank + two 48,000 m3 tanks), while GIIGNL 2025 lists 150,000 m3 (apparently only the single Sinopec-built tank). That tank stems from a Feb 2022 Sonatrach-Sinopec EPC contract.",
         "[CONFLICTING DATA]", ["https://www.offshore-energy.biz/sonatrach-and-sinopec-sign-skikda-lng-storage-tank-deal/"]),
    wiki("Algeria", "T100000130244", "Skikda LNG Terminal", "G100002024407", "New Skikda LNG jetty (2024)",
         "A new LNG loading jetty at Skikda entered service in March 2024, receiving its first large LNG carrier (Sonatrach), part of the terminal's modernization.",
         "[CONFIRMED]", ["https://lngprime.com/lng-terminals/algerias-sonatrach-says-new-skikda-jetty-gets-first-large-lng-carrier/107241/"]),
    wiki("Algeria", "T100000130244", "Skikda LNG Terminal", "G100002024407", "Sonatrach-Sinopec storage deal (2022)",
         "On 17 Feb 2022 Sonatrach signed an ~US$177.7M EPC contract with Sinopec units to build a 150,000 m3 LNG storage tank at Skikda, part of the storage/port-modernization program.",
         "[CONFIRMED]", ["https://www.offshore-energy.biz/sonatrach-and-sinopec-sign-skikda-lng-storage-tank-deal/"]),
    wiki("Algeria", None, "Algeria LNG (national context)", None, "2024 LNG exports decline",
         "Per the audit's reading of GIIGNL, Algerian LNG exports fell to ~11.5 Mt in 2024 (reduced gas availability, higher domestic power demand, Arzew maintenance). Unverified against a primary source this batch (EIA brief unverifiable; confirm against the committed GIIGNL 2025 edition).",
         "[UNVERIFIED — SINGLE SOURCE]", []),
    wiki("United States", "T100000130219", "Woodside Louisiana LNG Terminal", None, "Tellurian acquisition, partnership structure, first LNG",
         "Woodside acquired Tellurian (Driftwood) in Oct 2024 and renamed the project Louisiana LNG. FID on the 3-train, 16.5 Mtpa foundation development was taken 29 Apr 2025 (first LNG target 2029; site permitted for 27.6 Mtpa across 5 trains). Stonepeak took 40% of InfraCo (Jun 2025); Williams took 10% of HoldCo + 80%/operatorship of Driftwood Pipeline for US$250M (Oct 2025). Effective InfraCo interests: Woodside 54%, Stonepeak 40%, Williams 6%.",
         "[CONFIRMED]", ["https://www.woodside.com/docs/default-source/asx-announcements/2025/028-woodside-approves-louisiana-lng-development.pdf",
                         "https://www.woodside.com/docs/default-source/asx-announcements/2025/038-woodside-completes-louisiana-lng-sell-down-to-stonepeak.pdf",
                         "https://www.woodside.com/docs/default-source/asx-announcements/2025/woodside-announces-louisiana-lng-partnership-with-williams.pdf"]),
    wiki("United States", "T100000130239", "Rio Grande LNG Terminal", None, "CCS application withdrawn (Aug 2024)",
         "NextDecade withdrew its CCS project application from FERC for Rio Grande in Aug 2024, while saying it continued to explore CCS. (CCS is a read-only/out-of-scope GEM field; this is Background only — GEM's CCSNotes already records the abandonment.)",
         "[UNVERIFIED — SINGLE SOURCE]", []),
    wiki("United States", "T100000130237", "Port Arthur LNG Terminal", None, "April 2025 Bechtel scaffolding collapse (fatalities, litigation)",
         "On 30 Apr 2025 a scaffolding collapse at the Port Arthur LNG site killed three Bechtel workers (Felipe Mendez, Felix Lopez Sr. among them; Marcos Ramirez injured). Bechtel halted work; OSHA was notified. A wrongful-death lawsuit was filed in early May 2025 against ConocoPhillips, Port Arthur LNG LLC, and Sempra; litigation pending late 2025.",
         "[UNVERIFIED — SINGLE SOURCE]", ["https://www.houstonpublicmedia.org/articles/court/2025/05/02/520479/victims-in-deadly-port-arthur-lng-scaffolding-collapse-file-lawsuit-against-companies/"]),
    wiki("United States", "T100000130237", "Port Arthur LNG Terminal", "G100002023703", "Phase 2 FID, financing, cost",
         "Port Arthur Phase 2 (T3/T4, ~6.5 Mtpa each; facility to ~26 Mtpa) reached FID Sept 2025 (Bechtel full NTP). Phase 2 entity owned by Sempra Infrastructure Partners 50.1% and a Blackstone Credit & Insurance-led consortium 49.9% (incl. KKR, Apollo-managed funds, Private Credit at Goldman Sachs Alternatives). DOE issued the Phase 2 export authorization. Reported at ~US$12B + ~US$2B shared facilities.",
         "[CONFIRMED]", ["https://portarthurlng.com/sempra-announces-strategic-transactions-advancing-goal-of-building-leading-u-s-utility-growth-business/",
                         "https://www.energy.gov/articles/doe-issues-lng-export-authorization-port-arthur-phase-ii-advancing-president-trumps",
                         "https://semprainfrastructure.com/what-we-do/lng/port-arthur-lng/"]),
    wiki("United States", "T100000130242", "Plaquemines LNG Terminal", None, "Capacity definitions, uprates, brownfield expansion",
         "VG/DOE define Plaquemines Phase 1 as 13.33 Mtpa nameplate (12 blocks/24 trains); GIIGNL 2026 lists 11.3 Mtpa (a definitional difference). FERC approved a 24.0->27.2 Mtpa PEAK uprate (Feb 2025); VG later requested up to 35.0 Mtpa peak — both without new facilities. A proposed brownfield expansion adds 16 blocks (up to 31.0 Mtpa peak; firm nameplate not published; GEM carries an inferred 17.78 Mtpa).",
         "[CONFLICTING DATA]", ["https://www.federalregister.gov/documents/2025/12/15/2025-22816/plaquemines-expansion-llc-application-for-long-term-authorization-to-export-liquefied-natural-gas-to"]),
    wiki("United States", "T100000130973", "CP2 LNG Terminal", "G100001094165", "CP2 Phase 3 early-stage expansion",
         "Venture Global is pursuing a third CP2 phase, with additional trains reported at ~10 Mtpa peak (firm nameplate not published); early-stage via a DOE progress report and FERC pre-filing waiver. GEM tracks it as proposed unit 'Phase 3 (T37-48)'.",
         "[UNVERIFIED — SINGLE SOURCE]", ["https://ventureglobal.com/projects-cp2/cp2-facility/",
                                          "https://lngprime.com/americas/venture-global-to-add-more-cp2-lng-trains-due-to-high-demand/186462/"]),
    wiki("United States", "T100000130238", "Texas LNG Terminal", "G100002023801", "Offtake / SPAs",
         "Reported long-term offtake for Texas LNG (Brownsville): RWE 1.0 Mtpa; Glenfarne Global Commodities 1.5; EQT 0.5 (amended down from 2.0); Gunvor 0.5; Macquarie 0.5. Offtakers are commercial counterparties, NOT equity owners (owner remains Texas LNG Brownsville LLC, parent Glenfarne). In 2025 FERC re-issued the final authorization (completion ~Nov 2029); Kiewit is LSTK EPC.",
         "[UNVERIFIED — SINGLE SOURCE]", ["https://www.texaslng.com/"]),
    wiki("United States", "T100000130206", "Alaska LNG Terminal", "G100002020601", "Preliminary offtake & strategic partners",
         "Preliminary/HOA-stage offtake for Alaska LNG totals ~13 Mtpa (TotalEnergies, JERA, Tokyo Gas, CPC, PTT, POSCO; POSCO ~1 Mtpa/20-yr HOA). Strategic partners reported: Baker Hughes, POSCO, Danaos. These are offtake/partnership, NOT equity (equity: Glenfarne 75%, AGDC 25%). Conoco/Exxon/Hilcorp/Great Bear are gas-supply counterparties. Phase One = ~807-mi 42-in pipeline; NEPA/FERC permitting completed 2020.",
         "[UNVERIFIED — SINGLE SOURCE]", ["https://alaska-lng.com/"]),
    wiki("United States", "T100000130987", "West Delta LNG Deepwater Port Terminal", "G100002098701", "Capacity (nominal vs optimized) & configuration",
         "Per the MARAD/USCG deepwater-port application (FR-2019-20929), West Delta would produce 5.0 Mtpa nominal, optimized up to 6.1 Mtpa (sponsor figure). Configuration: three production platforms with six trains (two per platform) among thirteen fixed bridge-connected platforms offshore Louisiana — an offshore, fixed (non-floating) deepwater port. GEM records 5.0 Mtpa nominal; status shelved.",
         "[CONFIRMED]", ["https://www.govinfo.gov/content/pkg/FR-2019-09-26/pdf/2019-20929.pdf", "https://lng21group.com/west-delta/"]),
    wiki("Australia", "T100000130331", "Darwin LNG Terminal", "G100002033101", "2026 restart and temporary FPSO-issue shutdown",
         "Darwin LNG resumed exports in late Jan 2026 after an extended idle (Bayu-Undan depletion), now backfilled by the Santos-operated Barossa project; the first Barossa cargo departed Darwin ~25 Jan 2026 for Japan. Santos then initiated a temporary shutdown in early 2026 to rectify BW-Offshore FPSO issues (compressor dry-gas seals / commissioning), with restart targeted ~Apr 2026 — hence the current 'idled' record.",
         "[CONFIRMED]", ["https://www.santos.com/news/santos-announces-first-barossa-lng-cargo/",
                         "https://www.argusmedia.com/en/news-and-insights/latest-market-news/2778868-australia-s-santos-loads-first-barossa-lng-cargo",
                         "https://www.argusmedia.com/en/news-and-insights/latest-market-news/2805003-australia-s-santos-pauses-darwin-lng-on-fpso-issue"]),
    wiki("Australia", "T100000130338", "Pluto LNG Terminal", "G100002033802", "Pluto Train 2 labor disruption",
         "Construction of Pluto Train 2 (Woodside; Bechtel EPC; ~5 Mtpa) was affected by labor disruption — union members voted in Dec 2025 to back industrial action. Background/context only; does not by itself change the unit's status or capacity.",
         "[UNVERIFIED — SINGLE SOURCE]", []),
    wiki("Australia", "T100000130338", "Pluto LNG Terminal", "G100002033803", "Pluto Train 3 historical FEED (not active)",
         "A Pluto Train 3 was studied historically (Woodside let FEED for Trains 2 & 3 in 2011). Train 3 never reached FID and is treated as historical/conceptual; GEM records it cancelled. The Scarborough gas instead feeds Pluto Train 2.",
         "[CONFIRMED]", ["https://www.ogj.com/pipelines-transportation/lng/article/17276335/woodside-lets-feed-contracts-for-pluto-lng-trains-2-3"]),
    wiki("United States", "T100001083401", "Barbers Point FSRU", "G100001094271", "Local opposition and linked power plant",
         "The proposed Barbers Point FSRU / Hawaii LNG project (Longboard TerminalCo; JERA) drew organized local opposition in 2026 (Local Power Hawaii coalition; Earthjustice), citing >US$2B cost, diversion from renewables, and Hawaii's 2045 fossil-free goal. ENR (Apr 2026) reported JERA eyeing a ~US$2B project including a ~500 MW hybrid combined-cycle/simple-cycle power plant supported by the offshore LNG. An Energy Innovation analyst told legislators alleged HSEO-study errors 'inflate the LNG benefit by at least $1.2 billion' (the energy office and JERA disputed this).",
         "[CONFIRMED]", ["https://www.hawaiinewsnow.com/2026/05/23/anti-lng-coalition-calls-hawaii-stop-plans-import-fossil-fuel/",
                         "https://www.enr.com/articles/62857-2b-hawaii-lng-power-plant-build-on-oahu-is-eyed"]),
]

# ---------------------------------------------------------------- entity_additions
RUN = "RUN — remote entity-search inconclusive (scraper returned only a generic result). VERIFY in the GEM shared entity system before creating; large firm, likely already exists."
entity_adds = [
    {"entity_name": "The Williams Companies Inc", "entity_type": "parent / shareholder", "country_of_hq": "United States",
     "parent_entity": "", "rationale_for_new_entity": "6% effective interest in Louisiana LNG Infrastructure LLC (via 10% of HoldCo); also 80% owner/operator of Driftwood Pipeline LLC.",
     "lookup_was_run": RUN, "lookup_result_summary": "Not in local export; remote scraper inconclusive. NYSE: WMB — very likely already in GEM's shared entity system.",
     "referenced_by_terminals": "Woodside Louisiana LNG Terminal (T100000130219)", "referenced_by_units": "G100002021901, G100002021902", "researcher_initials": "AI-draft"},
    {"entity_name": "Blackstone Inc", "entity_type": "parent (consortium lead)", "country_of_hq": "United States",
     "parent_entity": "", "rationale_for_new_entity": "Leads the Port Arthur Phase 2 49.9% equity consortium (Blackstone Credit & Insurance).",
     "lookup_was_run": RUN, "lookup_result_summary": "Remote scraper inconclusive; likely already exists. Source is single sponsor PR — candidate only (Port Arthur update is yellow).",
     "referenced_by_terminals": "Port Arthur LNG Terminal (T100000130237)", "referenced_by_units": "G100002023703, G100002023704", "researcher_initials": "AI-draft"},
    {"entity_name": "Apollo Global Management Inc", "entity_type": "parent (consortium member)", "country_of_hq": "United States",
     "parent_entity": "", "rationale_for_new_entity": "PR cites 'Apollo-managed funds' in the Port Arthur Phase 2 consortium — membership loosely worded.",
     "lookup_was_run": RUN, "lookup_result_summary": "Remote scraper inconclusive; likely exists. Verify entity granularity (managed funds vs parent) before adding — candidate only.",
     "referenced_by_terminals": "Port Arthur LNG Terminal (T100000130237)", "referenced_by_units": "G100002023703, G100002023704", "researcher_initials": "AI-draft"},
    {"entity_name": "The Goldman Sachs Group Inc", "entity_type": "parent (consortium member)", "country_of_hq": "United States",
     "parent_entity": "", "rationale_for_new_entity": "PR cites 'Private Credit at Goldman Sachs Alternatives' in the Port Arthur Phase 2 consortium — a fund/desk, not necessarily the parent.",
     "lookup_was_run": RUN, "lookup_result_summary": "Remote scraper inconclusive; likely exists. Verify granularity before adding — candidate only.",
     "referenced_by_terminals": "Port Arthur LNG Terminal (T100000130237)", "referenced_by_units": "G100002023703, G100002023704", "researcher_initials": "AI-draft"},
    {"entity_name": "ConocoPhillips Co", "entity_type": "parent", "country_of_hq": "United States",
     "parent_entity": "", "rationale_for_new_entity": "ALREADY EXISTS — no action. Referenced re: possible missing Port Arthur Phase 1 parent.",
     "lookup_was_run": "yes (entity_lookup.py --remote): FOUND", "lookup_result_summary": "Found in GEM entity system as E100001011247. Do NOT create. Use the existing entity if adding to Port Arthur Phase 1 Parent.",
     "referenced_by_terminals": "Port Arthur LNG Terminal (T100000130237)", "referenced_by_units": "G100002023701, G100002023702", "researcher_initials": "AI-draft"},
]

# ---------------------------------------------------------------- scope (full unit-rows for context)
scope = {"_comment": "Terminals touched by the ChatGPT-audit import batch (updates, qa, or wiki).",
         "terminal_ids": [
             "T100000130219", "T100000130237", "T100000130987", "T100000130238", "T100000130206",
             "T100000130606", "T100000130982", "T100000130338", "T100000130331", "T100000130239",
             "T100000130242", "T100000130973", "T100000130243", "T100000130244",
         ]}

# ---------------------------------------------------------------- write
for name, data in [("staged_updates.json", updates), ("staged_qa_review.json", qa_items),
                   ("staged_wiki_updates.json", wiki_items), ("staged_entity_additions.json", entity_adds),
                   ("staged_scope.json", scope)]:
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    n = len(data) if isinstance(data, list) else len(data.get("terminal_ids", []))
    print(f"wrote {name}: {n} records")
