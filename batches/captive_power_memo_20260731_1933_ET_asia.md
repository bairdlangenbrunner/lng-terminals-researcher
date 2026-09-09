# Captive-power memo — Asia (19 countries)

**Stamp:** 2026-07-31 19:33 ET
**Workbook:** `batches/lng_terminals_batch_20260801_1136_ET_asia-captive_update.xlsx`
(rebuilt 2026-08-01: the `…20260731_1932_ET…` build shipped 35 staged rows with `gogpt_plant`
named but `gogpt_plant_id` blank — ids now filled from the GOGPT Postgres for every named plant,
regardless of GOGPT's captive flag; verdicts and staged values unchanged. Prune the 07-31 file.)
**Staging:** `batches/staging/captive_power/asia/`
**Fourth regional increment** after us-gulf → americas-complete and europe. Remaining: Middle
East/Gulf, Africa, Oceania.

---

## What this is

The largest captive-power increment yet: **316 terminals / 458 unit-rows across 19 countries**
(Europe was 144/210). Terminal-first crawl sharded 45 ways (max 8 terminals/shard), dispatched
2026-07-31 on a fresh pull, plus an 8-shard **recovery pass** that re-researched the 51 terminals
whose first pass ran out of search budget (37 of them China). Recovery results supersede primary
shard entries by `terminal_id`; both layers are committed under `shard_results/`, and
`_assemble_asia.py` (committed alongside) reproduces the five canonical staging JSONs from them.

| | count |
|---|---|
| staged unit-rows | **56** (54 `CaptiveGasPower=True` + **2 `True→False` overturns**) |
| terminals with a staged edit | **32** (30 YES + Palu + Chana) |
| `terminal_first_priors` | 316 (every terminal, verdict + evidence) |
| `gogpt_candidates` | 316 |
| `neighboring_plants` | 440 (nearest-2 GOGPT per terminal, 30 km cap, whole-country pulls) |
| `qa_review` | 243 (88 INSUFFICIENT + 155 update-batch flags) |
| `PowerPlantsSupplied` | **0** (never staged by this workflow) |

Verdicts over all 316: **30 YES / 117 NO / 88 INSUFFICIENT / 81 SCREENED**. Staged-row confidence:
49 green / 7 yellow. Build emitted no `GUARD:`/`REF-DROP:` warnings; `recalc.py` clean; test suite
green (81 passed). `hybrid_basis` is blank on all 32 staged terminals — a checked, positive
finding: no Asia YES rests on a mixed grid arrangement (all are onboard-vessel, off-grid
liquefaction-complex, or dedicated on-site plants).

## Where the YES verdicts are

India 9, Malaysia 7, Indonesia 5, Japan 4, Bangladesh 2, plus Brunei, China (Tianjin PipeChina
FSRU), and Hong Kong — and **eleven countries returned zero YES**, including all 32 Vietnamese
terminals. That is not under-research: Vietnam, Thailand, Sri Lanka, Taiwan, South Korea, and the
Philippines are dominated by the **direction test** — terminals built to feed external power
plants (`PowerPlantsSupplied` territory), the exact opposite relationship to captive power.

Two structural families produced most YES verdicts:

- **Liquefaction complexes with own power/mechanical-drive islands** (mechanical=True on 10
  terminals): the Petronas MLNG complex (Satu/Dua/Tiga/T9 + the three PFLNGs), Bontang, Tangguh,
  Brunei LNG, West Papua FLNG. Category `mechanical_drive+power_generation` (25 unit-rows).
- **FSRU/FSU onboard generation with a documented spec** (`power_generation`, 28 unit-rows):
  Tianjin (66.3 MW dual-fuel), Hong Kong (4× MAN dual-fuel gensets, Bureau Veritas class record),
  Jafrabad/Vasant 1 (35.1 MW), Jaigarh, Summit FSRU (2×10 MW GTs per its EIA), Karaikal FSRU
  (3×22 MW GTs per its MoEFCC clearance), Moheshkhali, Lampung, Tanjung Benoa.

India's strength is a sourcing artifact worth naming: **MoEFCC/state EIA and clearance filings on
parivesh/environmentclearance.nic.in enumerate power systems** ("GTGs for captive power" verbatim
at Gopalpur), so single-source green (primary/regulatory) is repeatedly reachable there. China is
the mirror image — 40 of the 88 INSUFFICIENT are Chinese terminals whose 环评 (EIA) documents
exist behind provincial portals/eiacloud paywalls that defeated both passes.

## The two overturns (paste-sheet `False` rows)

Both pre-existing `CaptiveGasPower=True` values fail re-verification, and both survived an
adversarial second-agent QC (`qc_overturn_verification.json`, both upheld green):

- **Palu (Indonesia)**: the sole original ref uses "captive" for the *power plant's* relationship
  to nickel smelters — the terminal supplies gas OUT to that 1.2 GW plant. Classic direction-test
  misreading; correction cites the same PR Newswire source, so no ref is dropped.
- **Chana (Thailand)**: the original True had a **blank ref**; the terminal feeds the Songkhla
  Chana 1.7 GW EGAT-contracted plant (already correctly in `PowerPlantsSupplied`). Two independent
  sources staged.

The other two pre-existing Trues (**Hatsukaichi**, **MLNG Tiga**) re-verified cleanly; their rows
merge the existing ref URLs forward per the ref-MERGE rule.

## GOGPT side — for Natalia (SOP §4a)

`gogpt_candidates` tab: **9 ADD / 12 MAYBE / 24 REVIEWER CALL / 271 DO NOT ADD**. ADDs with citable
nameplates: Chhara 18 MW, Dhamra 29 MW (3× Bergen B35:40), Ennore ~26 MW CHP, Kochi 13 MW,
Hatsukaichi 11 MW gas-engine cogen, Yokkaichi Works 16.5 MW (3×5.5 MW gas engines, distinct from
the GOGPT-matched Kasumi station), Yoshinoura 35 MW multi-GT (distinct from the 502 MW main
station), Tiga FLNG 70 MW (MAN 20V35/44G), and **Ishikari 93.6 MW — flagged: it reads as a
merchant gas-engine plant, worth a manual screen before adding**. Per-unit tech
(aeroderivative/frame/genset), per-unit MW, plant totals, and status are in the tab per her screen
(no cancelled; sub-20 MW units only when plant ≥20 MW EU / ≥50 MW Russia — Asia rows carry the
data either way; the screen is hers to apply).

The dominant REVIEWER CALL class is **vessel-mounted FSRU/FSU generation** (Tianjin, Hong Kong,
Jafrabad, Jaigarh, Summit, Karaikal, Moheshkhali…): generation is real and often has a citable
nameplate, but whether GOGPT's ontology takes floating plant is a tracker-side decision this
workflow doesn't make. Also note the standing MW-conflation caveat: several liquefaction "power
station" figures bundle mechanical-drive shaft MW with electric MW — the `mechanical_drive_note`
column separates them; never let shaft MW into a generating-MW field.

Colocation context: China alone has **175 captive-flagged GOGPT plants in-country, 165 unmatched
to any LNG terminal** — the industrial-host trap (nearby captive plant belongs to an unrelated
factory) recurred constantly (Qidong/Huafeng textile, Wuhu/Xinxing steel, Map Ta Phut/Bangkok
Cogeneration, Hainan/Yangpu, Teluk Lamong/Pelindo). The neighboring_plants tab documents nearest-2
so these non-relationships are visible instead of re-litigated next pass.

## INSUFFICIENT landscape (88 — all in qa_review)

- **China (40)**: EIA-portal access, not absence of evidence. A targeted 环评-retrieval pass
  (eiacloud accounts or provincial-portal scraping) would likely resolve most.
- **FSRU house-power fuel undocumented (the BW Batangas class)**: BW Batangas, Engro Elengy
  (Exquisite), GasPort (BW Integrity), SLNG 2 (generator confirmed via ABB, fuel unstated),
  Nusantara Regas Satu, MCV (Myanmar, re-graded NO→INSUFFICIENT for exactly this reason). Class
  registers were checked; per the fuel gate these stay open rather than presumed.
- Proposed terminals with no published design yet (Matarbari pair, Crown Kakinada, Energas, etc.).

## Update-batch flags (155 in qa_review — the majors)

- **POSCO Dangjin (South Korea)**: GEM `shelved` vs sourced construction toward 2027 completion.
- **Haiphong FSRU (Vietnam)**: April 2026 Vingroup proposal to replace the 4,800 MW LNG plant
  with renewables+BESS (possible cancellation lead) + a 4,800 vs 6,400 MW conflict.
- **Map Ta Phut 2 / LMPT2 (Thailand)**: assets moved PTTLNG→PE LNG Co, EGAT 50% since Apr 2024 —
  Owner field reconciliation.
- **Long Son (Vietnam)**: `PowerPlantsSupplied` blank despite documented plant link; **Wuhu
  (China)**: Huaihe Energy 2×450 MW peaking plant same-parent/same-port lead; **Guangdong Dapeng**
  and **Pinghu**: further `PowerPlantsSupplied` checks.
- **Northern Vietnam LNG**: shelved-but-active (Aug 2024 term sheet); **Nam Dinh**: identity
  ambiguity (PV GAS); **Chan May**: 4,000 vs 1,500 MW figures; **Rizhao Lanshan**: owner
  discrepancy.
- **Kiyanly (Turkmenistan)**: marine-export scope question (polymer-plant adjunct; may not meet
  the ship-crossing gate) — scope call for the user, not resolved here.
- **Vessel identities**: Karaikal FSU named "Ghasha" in GEM vs "Al Khaznah" (IMO 9038440) in
  independent reporting; Vasant 1 (Jafrabad) IMO 9837066 confirmed via IRClass. `fsru_sync_check`
  ran gem-only (no carrier backend) — these route to the FSRU sync lane of a future Update batch.

## Orchestrator QC applied (audit trail, all inline-noted in shard files)

Fukuoka SCREENED→NO (equipment-enumeration NO; SCREEN criteria don't cover a retired facility);
MCV NO→INSUFFICIENT (fuel gate); Tiga FLNG terminal_id typo fixed against the export; four
citation repairs (Dabhol and Kerawalapitiya bare homepages → specific pages; Map Ta Phut 1
green→yellow on a replacement source; Dahej corroborated with an ADB EIA, stays green); one
bare-homepage residue scrubbed from a prior-assessment text. Full-file banned-domain/bare-URL sweep
clean. West Papua FLNG's YES was accepted at yellow after review: it rests on the confirmed EPC's
own published platform equipment package (Gastech 2024 paper) tied to the project by Genting's own
release — design-document evidence, not the banned class-precedent inference.

## Recommendation

Scale to the remaining increments — **Middle East/Gulf next** (FSRU-heavy, regulatory-filing-rich;
should behave like India), then Africa, then Oceania. Two follow-ons worth queuing independently:
(1) a China EIA-retrieval mini-pass to burn down the 40 INSUFFICIENTs; (2) the update-batch flags
above, several of which (Dangjin, Haiphong) are status-material.
