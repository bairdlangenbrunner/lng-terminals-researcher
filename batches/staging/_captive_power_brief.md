# Agent brief — Captive-power terminal-first researcher

You research **ONE question per LNG terminal**: does this terminal have a **captive gas power
plant**? You do NOT edit anything. You return a structured verdict. The orchestrator QC-gates
every citation you return and does all staging.

Read this whole brief before your first search. Governing docs: `docs/sops/captive_power.md` §2
(the definition) and **§2b (the tests that do the screening now that neither size nor duty does)**,
`docs/workflows.md` §9 (the recipe), and the repo `CLAUDE.md` hard rules.

## 1. The definition (SOP §2 — this is the crux)

A **captive gas power plant** is an **on-site / fenceline gas-fired plant, at ANY size**, whose
primary function is powering the terminal / liquefaction.

- **THERE IS NO MW THRESHOLD (changed 2026-07-27). A 3 MW on-site gas turbine is a YES.** Earlier
  versions of this brief set a `>50 MW` floor. It was wrong: GEM's `CaptiveGasPower` is a plain
  Boolean with no size qualifier, and GOGPT — the supposed source of the threshold — itself tracks
  1,900 sub-50 MW units of which 861 are captive, down to 1.5 MW. **Record size in `electric_mw`;
  never use it to disqualify.** If you find yourself writing "genuine on-site gas generation, but
  only NN MW, so NO" — that is a **YES**.
- **Never defeat a documented positive with an assumed size.** The floor cost us the Mukran FSRU
  miss: a regulator's permit said the terminal runs "permanently with onboard gas generators" and the
  pass still returned NO by *assuming* "~20–30 MW, standard FSRU-class equipment." Reasoning from
  class precedent to a negative is not a finding. **Absence of a published spec is INSUFFICIENT,
  never a documented NO.** A `True` asserts the *existence* of on-site gas generation, so a missing
  MW figure does not block it — leave `electric_mw` empty and still say YES.
- **Partially-captive counts.** A plant that powers the terminal *and* exports surplus to the grid
  is still captive.
- **Mechanical-drive counts — but is flagged.** On-site gas turbines that *mechanically drive the
  refrigeration compressors* (shaft power, no electricity generated) are captive power. Report
  `mechanical: "True"` for any terminal whose captive verdict includes mechanical-drive turbines,
  `"False"` for a pure-electricity-generator site. A **mixed** site (a real generator *plus*
  mechanical drives) is `"True"`.
- **As-designed captive power on an unbuilt facility still counts.** GEM records proposed projects
  by their design, so a proposed/under-construction terminal whose design includes captive power is
  a YES. A *cancelled* project that got far enough to publish a design is also a YES on design.
- **Out of scope:** off-site plants and non-gas fuels. Diesel-only / MDO-only / fuel-oil-only
  gensets are NOT captive gas power no matter how many there are — but **dual-fuel engines
  (DFDE, Wärtsilä `W*DF`, "gas/diesel") DO count** when a source establishes they burn gas or BOG
  in service; say which mode the source documents. **Non-combustion self-generation is not *gas*
  power:** turboexpanders / pressure-letdown recovery (Barcelona), ORC/ORMAT waste-heat units
  (Huelva), wind (Dragon), solar — all settled NOs on this ground.
- **Power, not heat — thermal ≠ electric.** A gas-burning installation producing *process heat* is
  not captive power however large: submerged-combustion vaporizers (SCV), open-rack vaporizers
  (ORV), process boilers, gas-fired water heaters. Świnoujście's >50 MW**t** SCV permit and
  Zeebrugge's SCV/ORV are settled NOs. Watch the unit — **MWt/MWth is thermal**, MW/MWe electric.
  Waste heat flowing **INTO** the terminal is not captive power either (Gate←Uniper,
  Grain←Uniper 340 MWth, Brunsbüttel←Covestro, Stade←Dow).
- **Loads are not generators.** Do not mistake consumption for generation: Falconara's "4× 1.1 MW
  electric motors" are compressor drives; Tenerife's "3.9 MW" is site demand; Fos Tonkin's "45 MW"
  is incremental *grid draw* from RTE; Barcelona's "38,499 MWh" is metered grid **import** (and MWh
  is energy, not capacity). None is on-site generation.
- **Captive to WHOM — the industrial-host trap.** A colocated captive plant may belong to a
  *different* port tenant. Settled: Huelva's GEMASA + La Rábida are CEPSA's refinery's; Stade's
  163 MW plant is **Dow's own**, built 2015, years before the FSRU; Sines' 43/41 MW are Repsol's and
  Indorama's; Tjeldbergodden's 150 MW was Statnett's regional grid reserve. Ask it every time.
- **Standby-only is a YES (user directive 2026-07-28).** "If there is any turbine whatsoever that
  runs when grid supply fails, that counts as a yes." A gas genset that runs *only* on grid failure
  is captive gas power — do not flag it, do not escalate it, stage it. Eemshaven is the type case:
  the Groningen permit has both FSRUs on **shore power** ("walstroom") with onboard engines started
  only on grid interruption — that is a green YES, `captive_category: standby_backup`. The
  **fuel gate is what still screens here**: gas-fired standby → YES; diesel-only standby → NO;
  fuel unstated anywhere → INSUFFICIENT (never NO). Duty now sets `captive_category`, not the
  verdict — a genset that is standby-*capable* but also carries load in service is
  `power_generation` (Klaipeda), not `standby_backup`.

### The direction test — the single most common error

Captive power flows **INTO** the terminal: the plant powers the liquefaction/regas.
The **opposite** relationship — the terminal piping regasified gas **OUT** to an external power
station — is a different GEM field (`PowerPlantsSupplied`) and is **NOT** a captive finding.

Island and small-market regas terminals usually exist *to feed* a power station. If the terminal's
whole purpose is supplying fuel to an adjacent power plant, the answer to *your* question is **NO**
(and you say so, flagging the `PowerPlantsSupplied` relationship in `notes` for a different batch).
Never report such a case as captive.

### The grid-access prior (from the Americas sweep — expectation-setting, NOT a substitute for research)

- **Grid-connected → electric drive, and the project says so in a filing.** For a grid-connected
  project after roughly 2015 the prior is **NO**, and the negative is usually *documented* in an
  environmental assessment or air permit. Find that document and quote it — a *documented* NO is a
  far better return than "not researched".
- **No grid → self-generation at scale.** Remote/off-grid sites and **moored FLNG/FSRU vessels**
  (off-grid almost by construction) generate their own power by necessity.
- **Regas is not liquefaction.** A regas terminal's energy demand is mostly *heat* for
  vaporization, often met by seawater or submerged-combustion burners, with modest electric load.
  Most import terminals are grid-fed → NO. The exceptions are terminals with a purpose-built on-site
  CHP (Revithoussa's 13 MW gas-engine cogen is a YES) and offshore/moored units (Adriatic's 30 MW
  GE10s, Krk's 16.5 MW BOG-fuelled DFDE module). A modest electric load is a reason the CHP is
  *small*, never a reason it doesn't count.

## 2. Hard citation rules (these are absolute — a violation invalidates your verdict)

- **Every URL you return must be value-checked** with
  `python scripts/url_verifier.py "<url>" "<token>" ["<token2>" ...]` from the repo root. The
  specific value your claim asserts (the MW figure, the turbine model, the "on-site generation"
  wording) MUST appear on that page. A page that merely loads is a **failed citation**.
- **≥2 independent publishers** for any staged value (3 when findable). Independent = different
  publishers/origins. **Two URLs that are copies/mirrors/host-variants of the SAME document are ONE
  source, never two.** A primary + its own press echo is one source. One
  primary/regulatory source (regulator filing, environmental assessment, air permit, operator
  technical paper) alone = green.
- **NEVER cite gem.wiki or globalenergymonitor.org**, or anything that derives from/republishes GEM
  (some IEEFA, Wikipedia, news footnoting GEM). Chase the primary source it points to and cite THAT.
  If the only place a value appears is gem.wiki, the value is **unsourced**.
- **Banned source: abarrelfull** (`abarrelfull.wikidot.com`, `abarrelfull.co.uk`) — never, even
  alongside corroboration.
- **A bare domain/homepage is never a citation.** Cite the specific page/PDF containing the value.

### url_verifier token-choice pitfalls (these caused real false PASS/FAIL last run)

- **No hyphen/space folding, no accent folding.** `SGT-400` FAILS against printed "SGT 400";
  ASCII `Gatun` FAILS against "Gatún". Try both spellings before concluding a citation is bad.
- **Multi-token checks validate each token independently**, so unrelated co-occurring tokens can
  manufacture a PASS. **Bare numbers are weak tokens** — prefer a distinctive multi-word phrase.
- Put `$` inside dollar tokens; a bare number substring-matches all over a page.
- **401 / 403 / 429 / a Cloudflare interstitial = the page is LIVE (bot-blocked), not dead.** The
  verifier auto-checks the Wayback snapshot; keep the live URL.

## 3. Where to look (best-yield sources, roughly in order)

1. **The project's own environmental/permit filing** — this is where captive power is always
   described, and it is primary/regulatory (green on its own). By jurisdiction:
   EU: the project's EIA / *Umweltverträglichkeitsprüfung* / *studio di impatto ambientale* /
   *estudio de impacto ambiental*, and the **EU Industrial Emissions Portal / E-PRTR** entry;
   UK: the DCO / Development Consent Order application on the Planning Inspectorate site, the
   Environment Agency **environmental permit**, and the **UK Emissions Trading Scheme** installation
   list; Norway: **Miljødirektoratet** discharge permits and the *Plan for utbygging og drift* (PUD)
   / **Sokkeldirektoratet** (ex-NPD) field pages; Türkiye: **EPDK/EMRA** licence registers and the
   *ÇED raporu*; Russia: the operator's own technical/IR material, **Glavgosekspertiza** design
   approvals, and equipment-vendor releases.
2. **Turbine/equipment vendor press releases** (Baker Hughes/NUOVO PIGNONE, Siemens Energy, GE
   Vernova, MAN, Wärtsilä, Mitsubishi Power) — these name the model, count and rating, and
   distinguish *mechanical drive* from *generator* explicitly. Highest-yield source for the
   `mechanical` flag.
3. **EPC contractor releases** (Technip Energies, Saipem, Chiyoda, Fluor, JGC, KBR, Wison).
4. **Trade-technical press** — LNG Industry, Gas Processing & LNG, Oil & Gas Journal, Offshore
   Energy, Riviera, Modern Power Systems, Turbomachinery International, Diesel & Gas Turbine
   Worldwide. Good corroboration, not primary.
5. **The operator's own technical papers / conference proceedings** (LNG-x, GASTECH, IGU) — often
   the only place an aggregate shaft-power figure is published.

## 4. What you must return

Return **JSON only** (no prose outside it): a top-level array with one object per terminal you were
assigned. Every terminal in your assignment gets an object — including the ones you screen out.

```json
[{
  "terminal": "<name exactly as given>",
  "terminal_id": "<as given>",
  "country": "<as given>",
  "verdict": "YES" | "NO" | "INSUFFICIENT" | "SCREENED",
  "mechanical": "True" | "False" | "",
  "captive_category": "mechanical_drive" | "power_generation" | "mechanical_drive+power_generation" | "standby_backup" | "contingency_design",
  "hardware_summary": "<ONE line naming the actual hardware: count, type, rating where a source states one — e.g. '2× 12 MW gas turbine generators (essential-power backup)'. Grounded in what your sources say; never a rating you inferred.>",
  "fuel_basis": "<how you established the fuel is gas — name the engine/turbine model if known>",
  "confidence": "green" | "yellow" | "red",
  "captive_summary": "<1-3 sentences: what the captive power IS (or why there is none), with the numbers>",
  "electric_mw": "<generating MW only, or \"\" if none/undisclosed — NEVER put shaft power here>",
  "mechanical_drive_note": "<shaft-power turbines: model, count, rating, aggregate hp/MW shaft — kept SEPARATE from electric_mw>",
  "confirmed_how": "<the evidence chain in full: who says what, in which document, quoting the operative wording>",
  "refs": ["<verified url>", "..."],
  "verification_log": [{"url": "...", "tokens": ["..."], "result": "PASS|FAIL", "note": "..."}],
  "gogpt_prior_assessment": "<for the GOGPT plant(s) you were given: IS it this terminal's captive power? If not, WHY not (usually: unrelated merchant plant, or a different industrial host's captive plant) + one independent non-gem.wiki info_url about that plant>",
  "gogpt_candidate": "ADD" | "MAYBE" | "REVIEWER CALL" | "DO NOT ADD",
  "gogpt_candidate_basis": "<why — see §5>",
  "status_or_other_findings": "<any status/FID/capacity/owner/vessel finding you tripped over, with sources — do NOT act on it>",
  "notes": "<anything else, incl. a PowerPlantsSupplied direction-test case>"
}]
```

Verdict meanings:
- **YES** — captive power confirmed against §2, with verified citations.
- **NO** — a *documented* negative: you found the filing/source saying the site is grid-fed, or that
  the gas-burning kit is heat-only, or that the plant belongs to another host, or that the fuel is
  diesel-only. This is a real research product; say where it's documented. **Size is never a ground
  for NO.**
- **INSUFFICIENT** — you looked and the answer is genuinely not in any public source, OR the design
  study was explicitly deferred/never done. "Undisclosed in any public source found" is
  **INSUFFICIENT**, not NO — absence of evidence is not a documented negative. Note that an
  undisclosed **MW figure** does not force INSUFFICIENT: if the *existence* of on-site gas
  generation is documented, that is a YES with `electric_mw` left empty.
- **SCREENED** — an obvious non-candidate you did not deep-research: cancelled-and-never-designed,
  or a crude-oil loading berth. **Say in one line why**, with the screen criterion. **Small scale is
  no longer a screen** — a bunkering/satellite/truck-loading depot can hold a 3 MW gas genset and
  that is a YES, so these now get real research (HIGAS was wrongly screened on scale and is a YES).

`captive_category` (every YES; SOP §2d) — what the hardware IS. Review-only, never a GEM column:
- **`mechanical_drive`** — gas turbines shaft-driving the refrigeration compressors. No generator,
  zero MWe. Always pairs with `mechanical: "True"`.
- **`power_generation`** — a dedicated on-site generating plant carrying site load in normal
  service (cogen, BOG-fired engines, FSRU dual-fuel gensets that supply the vessel).
- **`mechanical_drive+power_generation`** — both, at one site.
- **`standby_backup`** — gas-fired generation that runs only when grid supply fails.
- **`contingency_design`** — approved/designed generation that gets built only if a stated
  condition occurs (Ksi Lisims' power barges if the BC Hydro interconnection slips).

Pick on *present-tense duty*, not on what the hardware could do: a standby-capable genset that also
carries load in service is `power_generation`.

Confidence: **green** = ≥2 independent corroborations or one primary/regulatory source;
**yellow** = single non-primary or implied source; **red** = single weak source (prefer leaving the
figure blank and saying so).

## 5. `gogpt_candidate` — should this terminal become a NEW GOGPT power-station record?

GOGPT tracks **electricity generation** with a nameplate MW. **"Confirmed captive" ≠ "GOGPT power
station."**

- **ADD** — a genuine, sourced, gas-fired *generating* plant with a citable nameplate, **at any
  size**. GOGPT tracks 1,900 sub-50 MW units (861 of them captive, down to 1.5 MW), so a small
  rating is no bar.
- **MAYBE** — cogeneration exists but MW undisclosed or pre-filing.
- **REVIEWER CALL** — generation exists but no citable nameplate, or it is vessel-mounted (FSRU
  onboard gensets) and it's unclear whether GOGPT's ontology captures it.
- **DO NOT ADD** — reserve this for: a GOGPT record already exists, or it isn't a gas power station
  at all (grid-fed, heat-only, mechanical-drive only, another host's plant). **Size is NEVER a
  reason for DO NOT ADD.** This is a green *negative* determination, not a failure.

**Never let mechanical-drive shaft power populate `electric_mw`.** The biggest gas MW at a
liquefaction site is usually the compressor drives (hundreds of MW aggregate shaft). That figure
goes in `mechanical_drive_note`. Putting it in `electric_mw` fabricates power supply that does not
exist.

## 6. Working rules

- Resolve scope doubt **before** you answer. If you catch yourself writing "a reviewer may
  prefer…", that is the signal to go resolve it, not to hedge.
- Do not stage, do not edit files in the repo, do not touch the live database.
- Report what you actually found. A `SCREENED` with a crisp reason and a documented `NO` are both
  good outcomes; an over-claimed `YES` costs the whole batch its credibility.
- Log every verifier call in `verification_log`, **including the FAILs** — the orchestrator needs
  the failures to know what was dropped and why.
