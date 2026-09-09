# captive-power memo — africa + oceania (final two increments; tracker now 100% crawled)

Batch: `lng_terminals_batch_20260802_1650_ET_africa-captive_update.xlsx` +
`lng_terminals_batch_20260802_1650_ET_oceania-captive_update.xlsx` (guard-clean, recalc
clean, 81 tests pass). Final `captive_coverage_audit.py` (no `--pending`) **PASSES: all
843 TerminalIDs crawled** — africa (67) and oceania (37) were the last uncrawled buckets.

## verdicts

- **africa (67 terminals):** 17 YES / 14 NO / 29 INSUFFICIENT / 7 SCREENED → 55 staged
  unit-rows on 17 terminals (45 green / 10 yellow); 10 mechanical=True terminals.
- **oceania (37 terminals):** 14 YES / 1 NO / 18 INSUFFICIENT / 4 SCREENED → 36 staged
  unit-rows on 14 terminals (27 green / 9 yellow); 5 mechanical=True terminals.
- No hybrid_basis flags in either region (every staged True is a plain dedicated
  on-site/onboard arrangement).

## recovery passes (WebSearch budget exhausted session-wide; agents used WebFetch
site-search endpoints, Google News RSS, DuckDuckGo HTML, Wayback save-page-now)

- **Hilli Episeyo (Cameroon)** INSUFFICIENT → YES green: GE PGT25+G4 DLE mechanical-drive
  turbines + 2× Rolls-Royce Bergen B35:40V20AG gas gensets, vendor order releases.
  Resolves the shard 06/07 internal contradiction (Gimi's program-level yellow now
  coherent with a green Hilli precedent).
- **Pluto LNG** INSUFFICIENT → YES green: the primary pass's 403-with-no-snapshot was
  cured with a Wayback save-page-now capture (20260802182431) of the nsenergybusiness
  profile, plus Energy Aspects quoting Woodside's own Q2 2026 report ("the gas turbine
  generator completed synchronisation with the Pluto power grid").
- **Crib Point FSRU** INSUFFICIENT → YES yellow: a public EES submission
  (biosphere.org.au) quotes AGL/APA's own EES verbatim — the FSRU is "electrically
  isolated from Jetty and generates its own power", dual-fuel engines run on gas.
  Design-stage captive on a cancelled project counts per SOP; staged.
- Upgrades to green: Angola LNG (GE newsroom primary), Nguya FLNG (Baird Maritime second
  publisher), North West Shelf (boilingcold.com.au second publisher), Prelude (GE
  vendor-primary steam-turbine-driven compressors; mechanical=True).
- Unchanged INSUFFICIENT after two passes (genuine gaps, not tooling gaps): Punta
  Europa, Tango FLNG, Golar Lagos/Nigeria, Port Kembla (Höegh Galleon), Pasca, Browse,
  Fishermans Landing, Geelong.

## QC-gate adjudications (full detail in `{africa,oceania}/_qc_gate_done.json`)

- **Richards Bay Transnet FSRU: NO → INSUFFICIENT** (Hadera-class FSRU-onboard
  downgrade — active proposed FSRU, no vessel assigned; an Eskom supply-out statement
  never answers vessel machinery). Convention scoping ruled this run: **cancelled
  projects where no vessel was ever assigned keep design-based NOs** (Karpowership
  Coega/Richards Bay/Saldanha, Mossel Bay); onshore terminals (Guinea, Sierra Leone —
  Floating blank in export) are outside the FSRU convention entirely.
- **Live-DB True conflicts, all KEPT (no overturns staged):** Tango FLNG and Pasca FLNG
  (off-grid FLNG/FLSO physics prior; two research passes exhausted the leads; their
  uncorroborated live refs — marinelink, YouTube — flagged in qa_review); PAWA PNG FSRU
  (integrated FSRP barges: regas AND gas-turbine generation on the SAME vessels; the
  shard's direction-test NO is scoped to separate-vessel cases; PowerMag ref already
  live).
- **Yellow acceptances:** Marsa El Brega (Global Energy Observatory is independent;
  same-owner Sirte Oil plant inside the Brega complex defeats the host-trap concern);
  Coral North (TechnipFMC program-replication = fleet-evidence analog to Coral Sul's
  confirmed design).

## declared ref drops (`dropped_urls_dead`, REF-DROP guard clean)

- Nguya: YouTube-Shorts clip (contentless) — replaced by offshore-energy + Baird Maritime.
- Darwin LNG: generic turbolab.tamu.edu lecture PDF (never mentions Darwin).
- QCLNG: Bechtel construction YouTube video (no captive content).
- Wheatstone: Reuters platform-repair story — Wayback 20240613101004 full text proven
  contentless for the claim; the Baker Hughes technical paper is kept.
- Equus: bare homepage equusenergy.com.au stripped from staged refs (never a citation).

## GOGPT-side candidates (routes to gogpt-researcher; nothing staged GOGPT-side)

- **ADD (4):** Marsa El Brega (62 MWe same-site Sirte Oil plant, no GOGPT record);
  Australia Pacific LNG (7×~15 MW = 105 MW, Curtis Island); Gladstone LNG (6×12 MW
  ≈ 72 MW, Curtis Island); PNG LNG (44 MW base load documented).
- MAYBE 8 / REVIEWER CALL 16 across both regions (vessel-mounted FSRU/FLNG generation of
  unclear GOGPT-ontology fit dominates the reviewer calls — Prelude, Pluto's unresolved
  Yurralyi Maya linkage, Crib Point's design-stage cancelled FSRU, etc.). Seeded in
  `captive_gogpt_candidates.json` per region as usual.

## leads / follow-ups for a future pass (not actionable this run)

- **Höegh Galleon (Port Kembla):** a 2017 Wärtsilä order (2× 170,000 cbm FSRUs at
  SHI/HHI, 4× Wärtsilä 50DF each) matches the hull's specs/yard/timeline exactly but
  never names the vessel — circumstantial, correctly not cited. SEC EDGAR (browser
  User-Agent) or the Höegh Evi annual report/20-F is the likeliest resolver.
- **Yurralyi Maya power station (200 MW, GOGPT captive=True, 16.9 km from Pluto):**
  whether it is Pluto's fenceline plant remains unsourced either way.
- **Pluto Train 2 commissioning is in progress in 2026** (Energy Aspects satellite
  analysis + Woodside Q2 report) — status lead for whichever batch tracks Pluto T2.
- **Geelong FSRU:** EES exec summary now read in full — its "gas-fired boilers" are
  closed-loop regas HEAT (thermal, not captive power); the vessel's hotel-load power
  source is the open question; full EES at planning.vic.gov.au remains 403-blocked.
- **Browse FLNG:** an approved EIS for the floating concept existed (confirmed via
  Woodside's 2024 ERD) but the historical document itself is unreachable (WA EPA portal
  403s); a targeted Wayback pull of pre-2018 Woodside Browse pages could resolve it.

## scale recommendation

None — this closes the captive-power crawl of the entire tracker (843/843). Remaining
work is (a) user apply + the GOGPT-side ADD/MAYBE follow-through in gogpt-researcher,
and (b) the leads above as opportunistic follow-ups in future Update batches.
