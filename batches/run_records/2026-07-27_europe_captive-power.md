# Run record — Captive-power cross-tracker: Europe

**Date:** 2026-07-27
**Workflow:** Captive-power cross-tracker (`docs/workflows.md` §9, `docs/sops/captive_power.md`), terminal-first.
**Trigger:** user — "can you do a europe pass now for the lng captive power work?"
**Staging:** `batches/staging/captive_power/europe/` (+ sibling `captive_power/americas-floor-mopup/`)
**Workbook:** `batches/lng_terminals_batch_20260727_1832_ET_europe-captive_update.xlsx` (recalc clean)
**Companion workbook:** `batches/lng_terminals_batch_20260727_1827_ET_americas-captive-mopup_update.xlsx`
**Memo:** `batches/captive_power_memo_20260727_1832_ET_europe.md`
**Status:** built — awaiting user apply.

> Earlier artifacts from this same run (`…1539_ET…` workbook and memo) are **superseded**. Their
> headline — 5 YES, "zero in the EU or the UK" — was wrong. Kept on disk for the audit trail only.

---

## Plan

First region after the Americas were completed and consolidated (`captive_power/americas-all`,
88 rows / 29 terminals):

1. Scope from a fresh export: every LNG terminal in the 28-country Europe region, reusing the country
   list from `batches/staging/europe/meta.json` verbatim rather than inventing a new definition.
2. Compute GOGPT colocation priors as a **prior, not a filter**; crawl terminal-first.
3. Fan out 18 shards of terminal-first researchers, each returning a structured verdict per terminal.
4. Orchestrator QC gate over every cited URL on every YES record before staging anything.
5. Author the staging JSONs, build, recalc, memo, run record, `meta.json`.

Steps 3–4 ran **four times**, not once. That was the difference between the wrong answer and the
right one.

## Scope

**144 terminals / 210 unit-rows across 28 countries.** All 144 have coordinates; `CaptiveGasPower` was
blank on all 144 going in. Filtered on `Country/Area` with GOGPT `by_country=True` and **deliberately
not `--subnational`**, so the documented blank-area blind spot (blank `State/Province` on the LNG side,
blank `subnational` on the GOGPT side) could not silently drop rows — that blind spot caused the ST LNG
FLNG miss in the Texas run. Priors: 66 colocation matches / 429 neighbours / 336 unmatched GOGPT
captive plants. Sharded 18 ways.

## Outcome

**30 confirmed captive; 57 `CaptiveGasPower` unit-rows staged** (50 green, 7 yellow, 13
`mechanical=True`). **46 documented NO, 57 INSUFFICIENT, 7 SCREENED, 4 STANDBY_ONLY.** Zero
`PowerPlantsSupplied` (asserted in the assembler, verified 0 rows in the QC scan). 147 `qa_review`
items (3 high / 101 medium / 43 low).

By country: Italy 8, Russia 8, Germany 3, Greece 2, and one each in Belgium, Croatia, Cyprus, France,
Lithuania, Norway, Poland, Romania, Türkiye.

## The first pass was wrong — this is the transferable part

The first sweep found 5 YES (Norway 1, Russia 4) and I wrote up a confident structural explanation:
*"captive power is a liquefaction phenomenon, and Europe barely liquefies… zero in the EU or the UK."*

That was **the abolished >50 MW floor wearing a geographic disguise.** Liquefaction is where the big
captive plants are, so a method that only sees big plants sees only liquefaction — and then reports
its own blind spot as a fact about the continent. A structural explanation that exactly matches the
shape of your own filter should be treated as a symptom, not a finding.

Two classes were invisible, 25 of the 30 between them:

1. **FSRUs (13).** The onboard dual-fuel diesel-electric engine plant *is* on-site gas-fired
   generation serving the terminal. No GOGPT record, no "power plant" framing, MW usually undisclosed.
   An **import-side** class the liquefaction theory excluded a priori.
2. **Small/mid coastal regas with BOG-fired engines or cogeneration (12).** Mostly Italian, documented
   only in national permit portals, invisible to English-language trade press.

**The SCREENED class was the deepest hole.** A screen is *a verdict with no research behind it*, so it
is invisible to every sweep that iterates over verdicts. Sweep 3 partitioned the 36 screened records
by whether the plant was ever **built**: 23 never-built (screen stands), 13 built (scale was never a
legitimate screen). Re-researching the 13 produced Ravenna (green YES, three BOG-fired MCI per the
MASE filing) and HIGAS Sardinia (Riviera's as-built list: *"a natural gas captive power generation
system"*, verbatim).

**Fixed at source:** `docs/sops/captive_power.md`'s Phase-2 dispatch text used to tell the dispatcher
to quick-screen "small import/FSRU regas terminals." That sentence is gone, so the next area increment
cannot regenerate the error.

## Evidence rules this run settled (all now in the SOP)

- **A NO must point at a source:** either an enumeration of equipment/permitted emission sources with
  no gas generator in it, or an explicit statement of how the site's power is supplied. Else
  INSUFFICIENT.
- **An enumeration only counts if it is meant to be complete for the question asked.** A conference
  process-flow slide or an adversarial lifecycle Gutachten mentions equipment incidentally and does not
  enumerate *auxiliary power*; its silence is bare absence in disguise. → **Brunsbüttel onshore**
  NO → INSUFFICIENT.
- **A documented enumeration beats an inferred YES** (mirror of the Mukran rule). → **Kollsnes**
  YES → NO on Gasnor's own permit: the entire energy plant is 2.05 MWt of hot-oil burners. Caught
  before staging.
- **SCREENED should be evidenced, not assumed** — a never-built project filed as INSUFFICIENT re-enters
  the queue every batch forever. Gran Canaria and Bar reclassed with their evidence, closing them.
- **`STANDBY_ONLY` earns its own verdict** rather than collapsing into NO — it records a real
  gas-fired genset that simply fails the not-standby-only test.
- **Rev 00 / rev 01 of one document at two portal IDs = ONE source** (the Panigaglia shard had
  double-counted `REL-AMB-E-09111`).

## Two verdicts resolved by the orchestrator after shards gave up

Both punted as "scanned images / OCR not attempted":

- **Montoir → STANDBY_ONLY.** The 33-page 1997 base authorization is an image-only scan; OCR'd via a
  new `pdftoppm` + `tesseract` fallback added to `url_verifier.py`. Article I-2 enumerates *"1 groupe
  électrogène gaz de secours d'une puissance de 1 250 kVA"* — gas-fired, and **no MW floor would ever
  have found it**, but emergency-only, so not staged.
- **Panigaglia → NO.** The 263-page Studio Preliminare Ambientale: the site takes 132 kV from the
  national grid, and the 32 MW cogeneration authorised by DM 569/2010 was never built. (The VIA portal
  documentation page is a JS shell with zero document links — found by probing nearby document IDs in
  parallel.)

## Gotchas hit

- **A QC override keyed to a nonexistent terminal_id silently does nothing.** The Ust-Luga downgrade
  was keyed to `T100000130846` (correct: `T100000130504`); only the assembler's "override not present
  — SKIPPED" warning stopped it shipping as green. Keep that warning.
- **The subagent WebSearch budget (~200 calls) is exhaustible** and was exhausted in 10 of 18 shards.
  It doesn't kill an agent — it quietly degrades the back half of a large shard into INSUFFICIENT.
  Size shards for it.
- **Dispatch priors must lose to evidence, including mine.** Several of my own were wrong: South Hook's
  CHP was never built; Eemshaven has no dedicated pipe to the Magnum CCGT. And one was wrong *twice* —
  I recorded Adriatic LNG's 30 MW on-site turbine as "below threshold," which is exactly the void
  reasoning; Adriatic is now a staged green YES.
- **WebFetch cannot parse a raw PDF body** — `curl` + `pdftotext -layout` locally is the fallback, and
  is what unlocked both Montoir and Panigaglia.
- **My own audit over-flagged once:** a regex scan tagged Tilbury Island as a possible floor victim;
  reading the record showed a properly grounded NO quoting IAAC verbatim (*"electric drive is the
  preferred alternative"*). Verify a flag by reading the record before acting on it.

## Reviewer decision point (flagged, not decided)

**8 of the 30 are staged on as-designed evidence for facilities that aren't operating** — 4 cancelled
(Constanta, Shtokman, Trieste Monfalcone, Zaule), 1 shelved (Cyprus FSRU), 2 proposed (Gioia Tauro,
Obsky), 1 retired (Le Havre FSRU); Marshal Vasilevskiy is idled. Consistent with how GEM retains other
as-designed attributes on dead records, and each rests on the project's own filing — but if
`CaptiveGasPower` is read as strictly as-built, those are the rows to drop. Data-model question, so
it's the user's call.

## Companion increment — Americas no-MW-floor mop-up

A **sibling** dir, not a mutation of `americas-all` (whose Louisiana rows are already applied — editing
in place would desync the built workbook from its inputs). Nine floor-dependent Americas verdicts
re-researched: **2 YES, 7 INSUFFICIENT, 1 new row staged** (Peñuelas, yellow — the canonical
partially-captive case). Coastal Bend is YES but deliberately not re-staged (already in americas-all;
would duplicate the `(unit_id, field_name)` pair), with confidence green → yellow since both URLs share
one self-published origin. High-severity incidental: **Titusville** is `cancelled` in GEM yet filed a
DOE semi-annual report on 19 Mar 2026.

I also confirmed no *further* Americas pass is needed: of 21 scale-fingerprinted americas-all records,
17 unstaged, only 5 ever built, 2 validly-screened crude-oil terminals, 2 already in this mop-up, and
Tilbury Island already research-grounded. **Americas complete.**

## Doc + script changes

- `docs/sops/captive_power.md` — Phase-2 dispatch no longer instructs screening of small import/FSRU
  terminals (root-cause fix for this run's error); added the `STANDBY_ONLY` disposition, the "a NO must
  point at a source" rule and its enumeration-completeness qualifier, the sweep-until-enumeration-backed
  loop, and the SCREENED-class re-audit; §2 clarified that "cancelled-but-designed = YES" applies to the
  terminal's *own* design, not an abandoned captive bolt-on at an operating terminal (South Hook).
- `scripts/url_verifier.py` — ZIP reader, OCR fallback (`pdftoppm` + `tesseract`) for image-only PDFs,
  and a user-agent-drop retry.
- `scripts/captive_power_colocation.py` — docstring states the no-MW-floor rule.

## Escalations for the user

- **Black Sea LNG (`T100000131101`)** is tagged `Country=Romania` but its coordinates land at **Kulevi,
  Georgia — 765 m from Kulevi LNG Terminal (`T100000130910`)**. One record or two? Not corrected.
- **Hammerfest's GOGPT record (`100000407847`) has `captive=false`, which is wrong.** GOGPT-side fix.
- **Yamal and Sakhalin II have no GOGPT record**, and **no European GOGPT plant carries the id-56
  liquefaction captive tag** — useless as a filter here.
- Taranto LNG's status fields are internally contradictory; Argo FSRU's environmental study was
  rejected 24 Jun 2026; Dörtyol FSRU has a second unit announced Feb 2026. → follow-on Update batch.

## Next

Europe complete. Five INSUFFICIENTs are worth one retry on document access alone (Pori, Klaipėda
small-scale, Mosjøen, Fredrikstad, Brunnsviksholme), plus Brunsbüttel onshore, whose Schleswig-Holstein
Antragsunterlagen (G10/2023/055) should now be public. Remaining regions: Asia (the big one), the
Middle East/Gulf, Africa, Oceania.
