# Captive-power cross-tracker — Europe pass

**Stamp:** 2026-07-27 15:39 ET
**Workbook:** `batches/lng_terminals_batch_20260727_1539_ET_europe-captive_update.xlsx`
**Staging:** `batches/staging/captive_power/europe/`
**Scope:** 144 LNG terminals / 210 unit-rows across **28 countries** — the whole Europe region as
defined in `batches/staging/europe/meta.json`, filtered on `Country/Area` (deliberately NOT
`--subnational`, so blank-`State/Province` terminals cannot be silently dropped).

## Headline

**5 terminals have captive gas power. All 5 are in Norway (1) and Russia (4). Zero in the EU or the
UK.** 14 unit-rows staged (`CaptiveGasPower = True` + paired ref), 11 green / 3 yellow.

| Verdict | n |
|---|---|
| YES | 5 |
| NO (documented negative) | 58 |
| INSUFFICIENT | 45 |
| SCREENED (non-candidate) | 36 |

This is a much thinner harvest than the Americas (29 terminals), and the reason is structural, not a
research gap: **Europe's LNG fleet is overwhelmingly import/regas on a dense grid.** Regas demand is
mostly *heat* for vaporization, met by seawater or submerged-combustion burners, with a modest
electric load bought from the grid. Captive power at scale is a *liquefaction* phenomenon, and
Europe's only liquefaction of consequence sits in the Arctic and the Russian Far East.

## The five YES terminals

| Terminal | Country | Detail | mech | Conf |
|---|---|---|---|---|
| Hammerfest LNG / Melkøya | Norway | 229 MW, 5× GE LM6000PD generators | False | green |
| Yamal LNG | Russia | 376 MW CHP, Siemens SGT-800 | False | green |
| Arctic LNG 2 | Russia | ~1500 MW planned (3×500 MW Wison/CGT30 stages) **+** 4× Baker Hughes LM9000 mechanical drive on Train 1 | True | green |
| Sakhalin II / Prigorodnoye | Russia | 5× GE Frame 5 generators + 4× Frame 7EA mechanical | True | green |
| Ust-Luga | Russia | 4× dual-shaft 120 MW MHI H-100, ~480 MW shaft | True | yellow |

**`electric_mw` is deliberately blank on Sakhalin II and Ust-Luga.** Ust-Luga's H-100s are the
dual-shaft *mechanical-drive* variant turning refrigeration compressors — that shaft power must never
populate an electric figure. Sakhalin II's widely-repeated ~129 MW generator figure traces back to
**gem.wiki** and was refused rather than cited circularly; a reviewer wanting that number should pull
GE Frame 5001/5002 spec sheets or a Sakhalin Energy technical paper.

## Citation gate — what I changed after re-verifying every staged URL myself

I re-ran `url_verifier.py` on all 14 staged citations independently of the researchers' logs.

- **Dropped `nsenergybusiness.com/projects/hammerfest-lng/`** — HTTP 403 (bot-blocked, so live, not
  dead) but **no Wayback snapshot exists**, so the asserted value cannot be verified against it. A
  page nobody can read cannot carry a citation. Hammerfest still stands on `snl.no` (which carries
  `229` + `LM6000` + `gasskraftverk` together) plus Equinor's own releases → 2 independent sources,
  one of them the operator. Green holds.
- **Ust-Luga downgraded green → yellow.** It rests on ONE document (Mitsubishi Power 2021-11-25); the
  `mhi.com` copy is the same release, not a second source. A lone source earns green only when it is
  primary/regulatory — an equipment-vendor press release is not.
- **Arctic LNG 2's `electric_mw` normalized** from a prose blob to the bare number `1500`, detail
  moved to `mechanical_drive_note`. Its ref list is **2 independent publishers, not 4** — 3 of the 4
  URLs are High North News across its `www.` and `en.` hosts. Two is still enough for green, but the
  count was overstated.
- **Two FAILs were token artifacts, not bad citations** (the documented no-folding pitfall): the High
  North News turbine article FAILs the literal `CGT30` but PASSes `Harbin` + `150MW`; `150 MW` with a
  space FAILs where `150MW` passes.
- **`niiosp.ru` retained on Yamal with a scoped note.** It does *not* contain the 376 MW figure, but
  it verifiably concerns this exact facility (`Ямал СПГ` + `Сабетта` + `электростанции`), so it
  corroborates the plant's **existence** — which is what a `True` cell asserts — not the MW. 376 MW
  is independently carried by power-technology.com and energoseti.ru.
- **7 inline `gem.wiki` URLs scrubbed from prose fields.** Agents had pasted them into
  `gogpt_prior_assessment` narrative text labelled "identity only". gem.wiki URLs are permitted only
  in the dedicated review-only nav columns; in prose they read as citations. Replaced with a
  non-clickable identity marker. The 70 remaining gem.wiki URLs are all in sanctioned nav columns.

## GOGPT-side findings (for the gas-plant tracker, not this batch's edit lane)

- **Hammerfest's GOGPT record (plant_id 100000407847) carries `captive=false`. That is wrong** — it
  is the terminal's own 229 MW captive plant, 0.0 km away. A GOGPT-side data fix.
- **Yamal LNG (376 MW) and Sakhalin II (5× Frame 5) have no GOGPT record at all.** Yamal is a clean
  `ADD`; Sakhalin II is `MAYBE` pending a citable nameplate.
- **Not one European GOGPT plant carries the id-56 "LNG production/liquefaction" captive tag.** The
  tag is effectively unused on this continent, so it cannot be relied on as a discovery filter.
- Final candidate tally after my overrides: **1 ADD** (Yamal), **2 MAYBE** (Sakhalin II, Mukran
  FSRU), **1 REVIEWER CALL** (Jade Energy), 140 DO NOT ADD. Hammerfest was reclassified ADD → **DO
  NOT ADD** because its record already exists — that column asks whether a *new* record is warranted.

## Four priors I was wrong about, corrected by the research

Recording these because they were my dispatch-prompt expectations, not the researchers':

1. **South Hook (UK) — the CHP was never built.** Verdict NO. Worth stating the rule this settles:
   the SOP's "cancelled-but-designed = YES" clause exists because GEM records a *proposed terminal*
   by its design. South Hook the terminal is **operating**, so its record describes an as-built
   facility with no captive power; staging True would misdescribe it. I've added this distinction to
   the SOP.
2. **Adriatic LNG's on-site turbine is 30 MW** — below the 50 MW threshold. NO on threshold.
3. **Eemshaven has no dedicated pipe to the Magnum CCGT** — the assumed direction relationship isn't
   there.
4. **Arctic LNG 2's 1500 MW is genuinely electric generation**, not the mechanical/electric
   conflation I predicted. The mechanical drives are a *separate* 260–290 MW shaft on Train 1.

## Patterns worth carrying into the next region

- **FSRUs sit below the threshold, so they are NO-on-threshold, not YES.** Onboard generation runs
  20–31 MW: Höegh-class ~31 MW, **Krk 16.5 MW** (green, Croatian academic source). Only a genuinely
  off-grid moored unit at scale would clear 50 MW.
- **Thermal ≠ electric.** Świnoujście and Eemshaven both turned on this: a >50 MW**t** combustion
  installation (submerged-combustion vaporizers, process-heat boilers) is not captive *power*.
- **The industrial-host trap fired exactly as briefed at Huelva** — its two GOGPT priors (GEMASA,
  Refinería La Rábida) are real tier-A captive cogeneration, but captive to CEPSA's separate Palos de
  la Frontera refinery/chemicals site, not the LNG terminal.
- **Spain is the model for a documented negative:** 4 Enagás/Saggas terminals proved grid-fed from
  their own EMAS filings, with metered numbers (Barcelona 38,499 MWh grid + 6,325 MWh
  *non-combustion* turboexpander self-gen; Huelva 47,778 MWh grid + 287 MWh ORMAT; Sagunto 25,500 MWh
  grid-billed). That is a far better research product than "not found".
- **38 direction-test cases** across the region — terminals feeding gas OUT to an external station
  (Bilbao→BBE 800 MW, Mugardos→As Pontes, Tenerife→Granadilla, Cyprus/Höegh→Vasilikos). All recorded
  in `qa_review` as `PowerPlantsSupplied` leads for a *different* batch; none staged here.

## Data-quality findings flagged, not corrected (94 `qa_review` incidentals)

- **Black Sea LNG Terminal (T100000131101)** is tagged `Country=Romania` but its coordinates
  (42.2756, 41.6328) land at **Kulevi, Georgia — 765 m from the separate Kulevi LNG Terminal record
  (T100000130910)**. I computed this rather than take the agent's "~300 m" on trust. Its GOGPT priors
  came back as Romanian plants >1,000 km away purely as an artifact of the country tag. Likely the
  AGRI project's Georgia-sited liquefaction leg mislabelled. **Needs a human call on whether these
  are one record or two.**
- **Taranto LNG (T100001084182)** is internally contradictory: `Status=operating` / `Substatus=actual`
  but `ProposalYear=2025` and `ActualStartYear=2027`.
- **Vlora FSRU** — `PowerPlantsSupplied` is blank where comparable direction cases are populated.
- **Argo FSRU (Italy)** — environmental study rejected **24 June 2026**.
- **Dörtyol FSRU (Türkiye)** — a second unit was announced **February 2026**.
- **Tenerife's Granadilla GOGPT prior** carries a matcher `status_flag: "mismatch"`.

All route to a follow-on **Update** batch — this batch's edit lane is `CaptiveGasPower` only.

## Known limitation: 45 INSUFFICIENT, and why

The subagent **WebSearch budget (~200 calls) is exhaustible**, and it was exhausted in 10 of the 18
shards, degrading their back halves. The INSUFFICIENTs are not evenly spread — they concentrate in
**Russia (14)** and **Italy (9)**, which is where the unbuilt-project tail lives. For most of them
"undisclosed in any public source found" is the honest answer regardless of budget (early-stage
Arctic proposals with no published design), but these 14 were cut short and deserve a top-up pass:

Fos Cavaou, Montoir, Inkoo, Teesside GasPort, Teesside WaveCrest, Grangemouth, Port Meridian,
Yakutia LNG, Portovaya, Marshal Vasilevskiy, Paldiski FSRU, Gdansk FSRU, Jade Energy, Mukran.

Portovaya and Yakutia are the two most likely to convert to YES — both are liquefaction, and
Portovaya is off-grid by design.

## Apply notes

Paste from **`updates_in_database_format`**. `updates_summary` carries two review-only columns that
are **not** GEM fields and must not be pasted: `mechanical`, and the `gogpt_*` lead columns.
Nothing in this batch touches `PowerPlantsSupplied` (asserted by the assembler, verified 0 rows in
the QC scan).
