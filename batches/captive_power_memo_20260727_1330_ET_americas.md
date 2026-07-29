# Captive-power cross-tracker — remainder of the United States + all of the Americas

**Date:** 2026-07-27
**Workflow:** Captive-power cross-tracker (§9), terminal-first.
**Area:** Fourth and final Americas increment — every US LNG terminal outside the Gulf (East Coast,
West Coast, Alaska, inland) plus every non-US country in the hemisphere: Canada, Mexico, Puerto Rico,
Dominican Republic, Jamaica, Panama, Colombia, Brazil, Chile, Peru, Argentina, Trinidad and Tobago,
El Salvador, Venezuela.
**Workbook:** `batches/lng_terminals_batch_20260727_1330_ET_americas-captive_update.xlsx` (recalc clean)
**Prior increments:** Louisiana (2026-07-09), Texas (2026-07-10), US Gulf remainder (2026-07-27).
**With this batch the Americas are complete.**

---

## Headline

**45 terminals crawled terminal-first; 12 confirmed captive; 32 `CaptiveGasPower` records staged.**

The hemisphere splits cleanly along one axis, and it is not geography — it is **grid access**.

- **Every terminal that can reach a large hydro or utility grid chose electric drive**, and said so in
  a regulatory filing: Tilbury, Cedar, Woodfibre and Summit Lake in British Columbia; Placentia Bay in
  Newfoundland. These are *documented* negatives, not unresearched ones.
- **Every terminal that cannot reach a grid generates its own power at scale**: Kenai and Alaska LNG
  (Alaska), the moored FLNGs (Argentina LNG's Hilli Episeyo), and the remote-coast Canadian projects
  that predate the grid-electrification turn (Goldboro, Ksi Lisims' contingency case).
- **Island and Caribbean terminals are almost all the opposite relationship** — they exist to *feed* a
  power station, which is `PowerPlantsSupplied`, never captive. Peñuelas, San Juan, Costa Norte and
  Andrés all fail the direction test cleanly.

That pattern is the useful output of this batch as much as the individual verdicts are: for a
grid-connected North American project after roughly 2015, the prior should be **NO**.

| Verdict | Count | Terminals |
|---|---|---|
| **Confirmed captive — staged** | 12 | Kenai, LNG Canada, NF Altamira, Alaska LNG, Peru LNG, Costa Azul, Firebird, Atlantic LNG, Goldboro, Cove Point, Ksi Lisims, Argentina LNG |
| **Confirmed NO** | 11 | incl. Tilbury, Cedar, Woodfibre, Summit Lake, Peñuelas, San Juan, Costa Norte, Andrés |
| **Insufficient evidence** | 8 | incl. AMIGO FLNG, Placentia Bay, Bahía Blanca, TGS Puerto Galván, Kitsault |
| **Screened, not researched** | 14 | cancelled-and-never-built or no design detail in existence |

**Staged: 32 `CaptiveGasPower` unit-rows across 12 terminals** — 25 green, 5 blue (already `True` in
GEM, re-verified unchanged), 2 yellow. **Zero `PowerPlantsSupplied`** (never in this workflow).
**17 `qa_review` items**, two of them high-severity, route off-lane findings to Update batches.

---

## 1. The strongest find: Goldboro LNG (T100000130354) — YES, green, 180 MW

Nova Scotia's environmental-assessment record states verbatim that the facility includes a
**"180 MW Power Plant"**, with *"On-site (gas turbine) power generation to support the LNG facility and
support services."* That is a purpose-built captive plant named as such in a primary regulatory
document — the cleanest single piece of evidence in the batch.

It also produced the batch's only **independent cross-tracker confirmation**: GOGPT already carries a
"Goldboro LNG power station" record at **180 MW**, cancelled, flagged captive — the same number,
arrived at separately. Two trackers agreeing to the megawatt on a cancelled project is a strong signal
that both records are right.

`mechanical = False`, deliberately. The design *also* carries roughly **640 MW of Frame 7 mechanical
drive** for the refrigeration compressors (documented in the record's `mechanical_drive_note`), but the
YES does not need it: the 180 MW electric plant stands on its own. Flagging `mechanical = True` here
would misdescribe what the verdict rests on.

## 2. Alaska LNG (T100000130206) — YES, green, and a citation the QC gate had to remove

Verdict unchanged (GEM already carries `True`; staged **blue**, re-verified). But the citation set
changed materially, and the reason is worth recording.

The record originally cited **FERC's FEIS Volume 1**. Full-text verification of that document — 17.2 MB,
1,927,950 characters — found **zero** occurrences of "turbine generator", zero of "N+1", and "124" only
as page numbers. The claim is simply not in the volume that was cited. It was dropped.

**AGDC Resource Report 1 carries the entire claim verbatim**, so the finding survives as a single
primary/regulatory green — which is the one shape in which a lone source is legitimately green.

A second, subtler defect surfaced on the same record: a token check on `['800,000', 'ISO horsepower']`
**passed on co-occurrence** — the two tokens are both present in the document but describe different
things (800,000 is *cubic yards of dredge spoil*). The real figure is **298,000 ISO hp** across six gas
treatment plant units. Corrected. This false-PASS mechanism is generic to substring verification and is
now written up in §6.

## 3. Argentina LNG (T100000130832) — YES, green, after blanking an unsupported number

The most serious defect the QC gate caught anywhere in this batch. The record staged **66 MW** of
electric generation (2 × 33 MW) aboard Hilli Episeyo. Verification found:

- **No cited URL contains "33 MW" or "66 MW"** — the number had no source at all.
- `rivieramm.com` is **live-dead** (110 bytes), and its Wayback copy is about **Gimi**, a different
  Golar FLNG serving BP's Greater Tortue Ahmeyim off Mauritania/Senegal — and quotes **26 MW**, not
  2 × 33 MW.
- A second citation (`petroleumafrica`) is a 1,164-byte stub.

`electric_mw` was blanked and both URLs dropped. **The YES survives green on the mechanical side**,
which is well-sourced: four GE PGT25+G4 aeroderivative turbines driving GE 2BCL compressors, roughly
136 MW of shaft power, on a **moored FLNG with no grid connection** — off-grid by physical necessity.
`mechanical = True`.

The Gimi/Hilli conflation that produced the bad number is itself logged as a `qa_review` item, because
the same confusion may exist in GEM's vessel fields.

## 4. Two verdicts overridden for consistency

Both preserve the researcher's original text verbatim, with the override recorded in `_orch`.

- **Placentia Bay FLNG: YES → not staged.** The Newfoundland EA registration gives a gas-turbine base
  case (~120–140 MW shaft + ~40 MW utility demand) — but the *same document* states the
  gas-turbine-vs-electric-motor driver study was **deferred to later engineering**, and the project was
  shelved before it happened. That is the identical evidentiary state as **AMIGO FLNG**, which scored
  INSUFFICIENT in this batch. Staging one and not the other would be indefensible, and CLAUDE.md's
  never-stage-with-doubt rule governs. The 120–140 MW primary-source finding is preserved in
  `qa_review` so it survives if the project revives.
- **TGS Puerto Galván: NO/green → INSUFFICIENT.** Its stated basis was *"undisclosed in any public
  source found"* — that is **absence of evidence, not a positive NO**, and a green NO asserts more than
  the research supports.

## 5. Ksi Lisims (T100000130914) — staged yellow as an explicit reviewer call

Not a research gap; a definitional one. The **committed** design is grid electric drive. The **603 MW**
figure is an *approved contingency* case in the environmental assessment — real, permitted, and not
what the project intends to build. Staged **yellow** rather than omitted so a reviewer sees the
ambiguity and rules on it, which is the right disposition for a question the sources cannot settle.

Firebird was downgraded **green → yellow** on a narrower ground: `lawinsider.com` genuinely contains
both "SCC6-800" and "430", but it is the **only** source carrying the number.

## 6. QC gate — what ran, and two verifier lessons

38 token checks over every YES-record citation plus four retry casualties, run concurrently:
**35 PASS / 3 FAIL**, and all four previously-lost citations recovered.

The 3 FAILs are **token-choice artifacts, not citation defects** — no citation changed:

- **Altamira's turbine model is printed "SGT 400"** (space), and the token was `SGT-400`. The verifier
  does **no hyphen/space folding**. The value is independently corroborated by two sources.
- **The LNG Canada air permit** legitimately supports only the generic gas-turbine fact; LMS100 and
  93.4 MW are carried by the GE release and the EAO TDR respectively.

Two verifier behaviours worth carrying into the SOP:

1. **No hyphen/space folding and no accent folding.** `SGT-400` fails against printed "SGT 400";
   ASCII `Gatun` fails against accented "Gatún". Choose tokens as they appear on the page.
2. **Multi-token checks validate each token independently, so unrelated co-occurring tokens can
   manufacture a PASS** (the Alaska 800,000 case above). **Bare numbers make weak tokens** — prefer
   distinctive multi-word phrases.

## 7. The 17 `qa_review` items — two high-severity

Both are records where the *world* has moved and GEM has not:

- **Argentina LNG is carried as `proposed`, but phase 1 reached FID.** Southern Energy SA holds a RIGI
  authorization certificate and a 30-year export permit, signed a 20-year ~US$13.7bn charter for Hilli
  Episeyo, and Seatrium's mooring/life-extension contract starts Q3 2026 for a 2027 operations start.
  FID on the second FLNG (MK II, on the **Fuji LNG** hull — *not* Gimi — 3.5 mtpa, 2028) followed
  around August 2025. Routed to a follow-on Update batch rather than staged here: this batch's edit
  lane is `CaptiveGasPower` only, and a status change deserves the systematic timeline pull and
  source re-verification an Update pass gives it. Flagged **with its sources** so nothing is lost.
- **Bahía Blanca is carried as `mothballed` with owner YPF, but the asset is gone.** The Tango FLNG
  barge left after the Oct 2020 Exmar–YPF settlement, was **sold to Eni in Aug 2022**, redeployed to
  Marine XII offshore Republic of Congo, and achieved first gas Dec 2023. The hull cannot return. This
  is a textbook vessel-reassignment case — the follow-on batch should run `fsru_sync_check.py` and
  verify GEM's Congo-side record carries the vessel.

Also notable among the medium items: **Repsol has been 100% owner of Saint John LNG since 2021**
(GEM still shows Repsol 75% / Irving Oil 25%); **`PowerPlantsSupplied` is blank on both Peñuelas and
San Juan** despite well-documented purpose-built relationships (off-lane here — never staged from a
captive batch, but exactly the follow-up this workflow is good at surfacing); and **Summit Lake PG is
an inland site** that rails ISO containers to Prince Rupert, which raises a marine-scope question of
the Dar es Salaam class (the captive verdict is NO either way, so nothing in this batch turns on it).

---

## Scope note and one open decision for the reviewer

**12 confirmed captive terminals is well past the SOP's ">~5 confirmed new captive pairs in one area"
escalation trigger — but that trigger is *area*-scoped**, and this batch deliberately spans a
hemisphere at the user's instruction ("do the rest of the US now, and all of the americas generally").
Per-area the counts are ordinary. Surfaced here rather than treated as a blocker.

**Open decision: should documented NO verdicts be staged as `CaptiveGasPower = "False"`?** Four
negatives in this batch are green-quality — Tilbury, Cedar, Woodfibre and Summit Lake all have
documented grid-fed electric drive. Staging them would turn real research into real data. **Precedent
across three applied batches is to stage positives only**, so this pass follows it; all 45 verdicts are
on the review-only `terminal_first_priors` tab either way. If the answer is yes, those four are a
one-line addition, and the same question applies retroactively to the negatives in Louisiana, Texas and
the US Gulf.

---

## Workbook tabs

| Tab | Rows | What it is |
|---|---|---|
| `updates_summary` | 32 | The staged `CaptiveGasPower` records, with the review-only `mechanical` and GOGPT columns |
| `updates_in_database_format` | 32 | The paste view |
| `qa_review` | 17 | Off-lane findings routed to Update / cross-tracker follow-ups |
| `terminal_first_priors` | 45 | **Every terminal crawled**, YES-first — the audit trail for the negatives |
| `neighboring_plants` | 33 | Nearby plants considered and why they were or weren't captive |
| `gogpt_candidates` | 45 | 4 ADD, 41 do-not-add |
