# Captive-power cross-tracker — Europe pass (final)

**Stamp:** 2026-07-27 18:32 ET
**Workbook:** `batches/lng_terminals_batch_20260727_1832_ET_europe-captive_update.xlsx`
**Staging:** `batches/staging/captive_power/europe/`
**Scope:** 144 LNG terminals / 210 unit-rows across **28 countries** — the whole Europe region as
defined in `batches/staging/europe/meta.json`, filtered on `Country/Area` (deliberately NOT
`--subnational`, so blank-`State/Province` terminals cannot be silently dropped).

**This memo supersedes `captive_power_memo_20260727_1539_ET_europe.md`, whose headline finding was
wrong.** That memo reported 5 YES terminals and concluded there were *zero* in the EU or the UK. The
true count is **30**, and 22 of them are in the EU. What follows is the corrected result and, because
the failure is reusable, an account of how the first answer went wrong.

## Headline

**30 of 144 European terminals have captive gas power** → **57 unit-rows staged**
(`CaptiveGasPower = True` + paired ref), **50 green / 7 yellow**, 13 rows flagged `mechanical = True`.

| Verdict | n | meaning |
|---|---|---|
| YES | 30 | staged |
| NO | 46 | documented negative — an enumeration or an explicit statement of how the site is powered |
| INSUFFICIENT | 57 | no source found either way; **never** a NO |
| SCREENED | 7 | non-candidate, now *evidenced* (never built) rather than assumed |
| STANDBY_ONLY | 4 | gas genset confirmed, but emergency-only → not staged |

By country: Italy 8, Russia 8, Germany 3, Greece 2, and one each in Belgium, Croatia, Cyprus, France,
Lithuania, Norway, Poland, Romania, Türkiye.

## The first pass was wrong, and the reason is reusable

The 15:39 memo's explanation was structural and confident: *"captive power is a liquefaction
phenomenon, and Europe's fleet is overwhelmingly grid-connected import/regas."* That sounds like a
finding about Europe. It is actually **the abolished >50 MW floor wearing a geographic disguise** —
liquefaction is where the *big* captive plants are, so a rule that only sees big plants sees only
liquefaction, and then reports its own blind spot as a fact about the continent.

Two classes were invisible to it, and together they are 25 of the 30:

1. **FSRUs — the single largest miss class (13 terminals).** An FSRU's dual-fuel diesel-electric
   engine plant *is* on-site gas-fired generation serving the terminal. It never registers as a
   "power plant," has no GOGPT record, and is usually undisclosed in MW. This is an **import-side**
   phenomenon, which the liquefaction theory ruled out a priori. Krk, Cyprus, Le Havre, Brunsbüttel,
   Mukran, Wilhelmshaven, Alexandroupolis, Piombino, Toscana, Klaipėda, Marshal Vasilevskiy, Polish
   Baltic Sea Coast, Etki.
2. **Small and mid-size coastal regas terminals running BOG-fired engines or cogeneration.** Mostly
   Italian, and mostly documented only in a national permit portal, not in English trade press:
   Ravenna, HIGAS, Gioia Tauro, Zaule, Trieste Monfalcone, plus Revithoussa's CHP and Zeebrugge's WKK.

**Four sweeps were needed, and the last two mattered most.** Sweeps 1–2 chased INSUFFICIENT verdicts.
Sweep 3 turned on the SCREENED class itself, which no verdict sweep can see: *a screen is a verdict
with no research behind it.* Of 36 screened records, 23 were never built (screen stands) and 13 were
built — and for those, scale was never a legitimate screen. Re-researching them yielded two YES:
**Ravenna** (three BOG-fired internal-combustion generators supplying the depot's own electricity,
per the MASE filing) and **HIGAS Sardinia** (Riviera's as-built description: *"a natural gas captive
power generation system"*, verbatim).

The SOP text that produced the error has been fixed at source: `docs/sops/captive_power.md`'s Phase-2
dispatch instruction used to tell the dispatcher to quick-screen "small import/FSRU regas terminals."
That sentence is gone, so the next area increment cannot repeat it.

## Evidence rules this pass settled

- **A NO must point at a source** — either (a) an enumeration of the installation's equipment or
  permitted emission sources with no gas generator in it, or (b) an explicit statement of how the
  site's electricity is supplied. Anything else is INSUFFICIENT.
- **An enumeration only counts if it is meant to be complete *for the question asked*.** A conference
  process-flow slide or an adversarial lifecycle opinion mentions equipment incidentally; it does not
  enumerate auxiliary power, so its silence is bare absence in disguise. This downgraded
  **Brunsbüttel onshore** NO → INSUFFICIENT.
- **A documented enumeration beats an inferred YES** — the mirror of the Mukran rule. **Kollsnes**
  flipped YES → NO on Gasnor's own permit, whose entire energy plant is 2.05 MWt of hot-oil burners.
- **SCREENED should be evidenced, not assumed.** A never-built project filed as INSUFFICIENT re-enters
  the research queue every batch forever; reclassing it to SCREENED *with its evidence* closes it.
  Gran Canaria and Bar were closed this way.
- **Rev 00 and rev 01 of one document at two portal IDs are ONE source.** Caught in the Panigaglia
  shard, whose two refs were the same annex (`REL-AMB-E-09111`) filed twice.

## Two verdicts the orchestrator resolved after the shards gave up

Both had been punted with "scanned images / OCR not attempted," and both turned on documents no
search snippet would ever surface.

- **Montoir-de-Bretagne → STANDBY_ONLY.** The 33-page 1997 base authorization is an image-only scan.
  OCR'd through the new `pdftoppm` + `tesseract` fallback in `url_verifier.py`; Article I-2 enumerates
  *"1 groupe électrogène gaz de secours d'une puissance de 1 250 kVA."* Gas-fired — and **no MW floor
  would ever have found it** — but *de secours*, so it is not staged. This is exactly the find the
  removed floor was blocking, and exactly why STANDBY_ONLY needs to be its own verdict rather than
  collapsing into NO.
- **Panigaglia → NO.** The 263-page Studio Preliminare Ambientale states the site takes 132 kV from
  the national grid and that the 32 MW cogeneration authorised by DM 569/2010 was never built.

## Citation gate

Every staged URL was re-verified independently of the researchers' logs. Corrections applied:

- **Antifer's proposed NO upgrade rejected**, verdict kept INSUFFICIENT — the CNDP dossier's *"turbine
  à gaz entraînant l'alternateur"* is a glossary footnote defining *cycle combiné*, not site equipment.
- **Etki green → yellow** (round 4). Its lone citation is the operator's own spec table, which never
  states self-generation; it states *"Engine: Wärtsilä-Hyundai DFDE"*, and the finding is one
  inferential step from that designation. Sound inference, but not the primary-source-states-the-value
  standard green requires. Five other single-ref greens **pass** that test and stand: Zeebrugge (Flemish
  ministerial decree), Gioia Tauro / Trieste Monfalcone / Zaule (MASE VIA filings), Revithoussa (DESFA's
  own fact sheet: *"supplying the necessary power to LNG terminal"*).
- **Ust-Luga green → yellow**: one document only; an equipment-vendor press release is not primary.
- **Dropped `nsenergybusiness.com/projects/hammerfest-lng/`** — 403 *and* no Wayback snapshot, so the
  value cannot be verified against it. Hammerfest still stands green on `snl.no` + Equinor.
- **Arctic LNG 2's ref list is 2 publishers, not 4** (three URLs are High North News host variants);
  `electric_mw` normalised to `1500`.
- **7 inline gem.wiki URLs scrubbed** from prose fields by a new assembler scrubber. gem.wiki survives
  only in the review-only navigation columns.

## Reviewer decision point

**8 of the 30 are staged on as-designed evidence for facilities not currently operating**: 4 wholly
cancelled (Constanta, Shtokman, Trieste Monfalcone, Zaule), 1 shelved (Cyprus FSRU), 2 proposed (Gioia
Tauro, Obsky), 1 retired (Le Havre FSRU); Marshal Vasilevskiy is idled. Staging them is consistent with
how GEM retains every other as-designed attribute — `Capacity`, `Owner`, `FacilityType` — on a dead
record, and the evidence in each case is the project's own regulatory filing. **If you read
`CaptiveGasPower` as strictly as-built/current-state, these are the rows to drop.** Flagging rather
than deciding, because it is a data-model question, not a research one.

## GOGPT side

`gogpt_candidates` is review-only — nothing here is a GEM edit. Worth noting:

- **Hammerfest** GOGPT plant `100000407847` carries `captive = false`, which is **wrong**.
- **Yamal** and **Sakhalin II** have no GOGPT record at all.
- No European GOGPT plant carries the id-56 liquefaction captive tag.

## Residual debt

57 INSUFFICIENT remain. Five failed **only** on document retrieval and are worth one more attempt:
**Pori** and **Klaipėda small-scale** each *found* a qualifying enumeration that then failed
`url_verifier` on a 403 with no Wayback; **Mosjøen** is blocked by an invalid TLS cert on `gasnor.no`;
**Fredrikstad** by a docplayer-only mirror; **Brunnsviksholme**'s miljötillstånd was never obtained.
**Brunsbüttel onshore** has a live lead — the Schleswig-Holstein portal (G10/2023/055) advertised a
March-2026 participation window, now four months past, so the Antragsunterlagen are probably
downloadable.

## Out of the captive lane

**147 qa_review items (3 high / 101 medium / 43 low)** for a follow-on Update batch. Highlights:
Risavika's owner is Risavika Production AS (North Sea Midstream Partners, since 16 Nov 2021), operated
by px Norge — not Skangass/Gasum; Kollsnes' PRTR operator is now MOLGAS NORWAY AS; HIGAS is wholly
owned by Avenir LNG with Reganosa as O&M; Klaipėda's operator has rebranded to KN Energies and `kn.lt`
refs need re-pointing; Brunnsviksholme is Gasum Clean Gas Solutions AB, not AGA; Mowi's ~0.22 mtpa is
implausible against two 1,000 m³ tanks.

**Escalated:** Black Sea LNG (`T100000131101`) is tagged Romania but its coordinates land at Kulevi,
**Georgia**, 765 m from `T100000130910`.

---

## Companion workbook — Americas no-MW-floor mop-up

`batches/lng_terminals_batch_20260727_1827_ET_americas-captive-mopup_update.xlsx`
(`batches/staging/captive_power/americas-floor-mopup/`)

A sibling to the already-built `captive_power/americas-all`, not a mutation of it — americas-all's
Louisiana rows are already applied, so editing it in place would desync the built workbook from its
inputs. Nine Americas terminals whose verdicts rested on the withdrawn floor were re-researched:
**2 YES, 7 INSUFFICIENT, 1 new row staged.**

- **Peñuelas** (`T100000130578`) `CaptiveGasPower = True`, yellow — the canonical **partially-captive**
  case: the adjacent EcoElectrica combined-cycle plant sells to the PREPA grid *and* supplies the
  integrated LNG terminal on the same site. Power flowing outward does not defeat captive status.
- **Coastal Bend** is a YES but deliberately **not re-staged** (americas-all already stages it;
  re-staging would duplicate the `(unit_id, field_name)` pair). Its basis strengthened — the developer
  now *names* cogeneration — but confidence drops green → yellow: both URLs are `coastalbendlng.com`,
  one self-published origin.
- The 7 INSUFFICIENTs are an **evidence upgrade, not a regression**: several previously read NO on
  floor reasoning (Hialeah: *"two orders of magnitude below the scale at which a >50 MW turbine set is
  ever installed"*).
- **High-severity incidental:** American LNG **Titusville** (`T100000130209`) is recorded `cancelled`
  in GEM but filed a DOE 15-19-LNG semi-annual report on 19 Mar 2026 and had its FTA authorisation
  transferred to LNG Holdings LLC / New Fortress Energy in Nov 2024. A cancelled project does not keep
  filing DOE semi-annual reports.

I also audited whether the Americas needs a *further* pass: all 21 scale-fingerprinted americas-all
records were checked, 17 unstaged, of which only 5 were ever built; 2 are validly-screened crude-oil
terminals, 2 were already in this mop-up, and Tilbury Island already carried a research-grounded NO
(IAAC, verbatim: *"electric drive is the preferred alternative"*). **The Americas increment is
complete.**
