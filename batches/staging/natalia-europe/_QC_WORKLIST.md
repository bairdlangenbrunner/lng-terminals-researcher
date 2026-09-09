# QC handoff → exhaustive Update worklist (`natalia-europe`)

Source: `batches/qc_20260729_1345_ET.md` (full memo) and
`batches/staging/qc-natalia-europe/staged_qc_spotchecks.json` (30 resolved cells).

**These are QC *detections*, not pre-approved edits.** You still research and cite each one to the
exhaustive-tier standard before staging it. QC did the finding; you do the sourcing. Where QC
already names a verified URL, re-verify it yourself with `url_verifier.py` — do not inherit a pass.

---

## A. Value fixes — resolved by the QC spot-check

Each has a resolution and evidence in `staged_qc_spotchecks.json` (match on `unit_id` + `field`).

| Unit | Terminal | Fix |
|---|---|---|
| `G100001095559` | Italy · Taranto | **`Status` → `proposed`; move `ActualStartYear` 2027 → `LatestPlannedStartYear`** (currently blank). Live row is `operating` with a future actual-start year — internally incoherent. Mid-VIA, consultation ran through Jul 2026. **Highest priority in the batch.** |
| `G100002105800` | Italy · Portovesme | `ShelvedYear` + `StopYear` → **2023**. GEM's own cited ref passes on "2023", fails on "2025" (verified). |
| `G100002047800` | Italy · Porto Empedocle | `Status` → **proposed**; clear `ShelvedYear`/`StopYear`. Snam Dec-2025 Ten-Year Plan lists it active, deadline to Apr 2028 — matches GEM's own `LatestPlannedStartYear` 2028. Cited `ieefa.org` ref is dead AND not independent (aggregator) — replace, don't merge. |
| `G100002106100` | Italy · Porto Torres | Clear `ShelvedYear`, `StopYear` (both uncited residue) and `FloatingVesselName` (*Golar Tundra* has been at Piombino since Mar 2023; no FSRU tender opened for Porto Torres). |
| `G100002047400` + `G100002047401` | Italy · Toscana | `Parent` + `Parent GEM Entity ID` → Snam **97.31%** (entity `E100001014534` unchanged). **Check first** whether the Golar Offshore Toscana 2.69% purchase closed — may now be 100%. Project-level: apply to BOTH unit-rows. |
| `G100002101000` | Greece · Thessaloniki | `Capacity` → **7.30 bcm/y**. 7.74 was derived from the *maximum* rating (9,567 MWh/h); methodology wants nominal (6,378 MWh/h → sponsor + LNG Prime both say 20 Mm³/day = 7.30). **Flag in `qa`**: `ResearcherNotesUnit` shows the peak basis was deliberate — this is a methodology disagreement to surface, not a silent revert. |
| `G100002046600` + `G100001055461` | Italy · Adriatic | `Parent` → `IFM Global Infrastructure Fund [31.5%]; Vitol Holding II SA [31.5%]; Snam SpA [30.0%]; Abu Dhabi National Oil Co [7.0%]`. Keep the live IGIF rename; **restore Vitol's dropped 31.5%**. Project-level: both unit-rows. |
| `G100002109900` | Netherlands · Zeeland | `Operator` → **`VTTI; Höegh Evi`**. The cited `zeelandenergyterminal.com/about` page says "equal ownership **and operatorship**" — it contradicts the live sole-operator value. |
| `G100002092400` | Albania · Port of Vlora | `CancelledYear` → **2026** (clears the orphan_ref). Also: `ShelvedYear` 2024 has **no ref at all** — source it. |
| `G100002068100` | Greece · Alexandroupolis | Fill `VesselOwner` → **Gastrade AE**. Moderate confidence (no single post-closing primary says "Gastrade owns it"); if you can't corroborate to ≥2 independent, leave blank + `qa`. |
| `G100002100800` | France · Le Havre | Fill `VesselOwner` → `Höegh Evi [50%]; Mitsui O.S.K. Lines (MOL) [48.5%]; Tokyo LNG Tanker [1.5%]`. Status already correctly `retired`. |

### DO NOT stage — QC resolved these in the live DB's favour
- **Fos Cavaou `G100002044800` `Capacity` 10.00 bcm/y is CORRECT** (Elengy Open Season, effective 1 Jan 2025). 8.00 is pre-expansion.
- **El Musel `G100002052800` 7.00 bcm/y is CORRECT** — 5.10 mtpa is the same capacity in another basis, not a conflict.
- **Mugardos `G100002053400` `Grupo Gadisa` is CORRECT** — "Tojeiro Group" is not the shareholder of record.
- **Jade Energy `G100002100100` `OtherNames`: do NOT add "Jade Energy"** — that IS the primary name since the 30 Apr 2026 rename; adding it would be a self-duplicate alias.
- Naming-only, no action: Thessaloniki `Enerwave SA`, Alexandroupolis vessel `Alexandroupolis`, Zeeland `VTTI BV`/`Hoegh Evi`.

---

## B. Mechanical fixes

- **4 × `CapacityUnits = 'MMcf/d'`** (not in catalog `['bcm/y','mtpa']`) — convert value + unit:
  Stade FSRU `G100002108600` (750.00), Wilhelmshaven FSRU `G100002045800`,
  Wilhelmshaven TES FSRU `G100002109700`, Eemshaven FSRU `G100001096022`.
  Use `capacity_normalize.py`; cite the underlying source for the converted figure.
- **5 German `project_field_inconsistent`** — project-level field populated on one unit-row, blank on siblings:
  Mukran FSRU `G100002114101` (`Operator`, `Operator [ref]`, `TempFacility` across 3 rows);
  Jade Energy `G100002100100` (`PlannedStopYear`, `TempFacility` across 2 rows).
  **Mukran's `Operator [ref]` is `https://www.giignl.org/annual-report`** — dead AND not a specific-page
  citation. Re-cite the correct edition at its official mirror before propagating.
- **`orphan_ref`**: Port of Vlora `CancelledYear` (→ A above); Toscana `G100002047401` `Capacity [ref]`
  with blank `Capacity`; Trieste Monfalcone `G100002048200` `FloatingVesselName [ref]` with blank vessel
  name — resolve each (fill the value, or drop the ref if it supports nothing).
- **Operating units missing `Capacity`/`CapacityUnits`**: Dunkirk `G100002044601`,
  Fos Cavaou `G100002044801`, Toscana `G100002047401`.
- **Zaule `G100002048400`** (cancelled) missing `Owner`.
- **35 `blank_ref` fills**, concentrated in `ShelvedYear [ref]` (10), `StopYear [ref]` (10),
  `Status [ref]` (8), `CancelledYear [ref]` (7) — uncited dormancy anchors on cancelled/shelved units.
  Cite the **dormancy evidence** (the stalled planning doc or newest article), NOT a source that says
  "shelved". Per-country lists in `batches/staging/qc-natalia-europe/comp_<Country>.json`.

---

## C. Citation repair

- **66 legacy `giignl.org` URLs are dead** — the single biggest win, and it needs no research:
  re-cite the **SAME edition** at its official mirror using the edition→URL table in `data/README.md`.
  Grep your country's rows for `giignl.org` and repair mechanically.
- **Albania, priority** — this country is the only genuinely rotted one (21.1%, zero giignl.org):
  - Port of Vlora FSRU 2 `G100001096073`: **malformed URL with no host**,
    `https:///energy-news/aktor-group-seals-6b-us-lng-supply-deal-with-albania-p8458.html`,
    cited in `capacity_ref`, `proposal_date_ref` AND `status_ref`. Identify the intended host, verify, repair.
  - Eagle FSRU `G100002042400`: 5 dead `eagle-lng.com` refs (domain gone, HTTP 000) + 5 image-only
    EU PCI PDF refs → **the record has no machine-verifiable citation left.** Re-source or blank+qa.
- **11 `lngworldnews.com`** (defunct outlet) — Wayback the same article, or replace with a live source.
- **17 `unverifiable`** image-only PDFs (Albania 5, Croatia 5, Italy 6, France 1) — NOT rot, but where one
  is a value's sole support, read it and add a machine-verifiable corroboration.
- **Normalize GIIGNL-2026 citations to the canonical mirror** `…/ee1bebf9…/GIIGNL-2026-Annual-Report-0521.pdf`
  (per `data/README.md`). The `-final.pdf` and `-0526b.pdf` variants are the SAME document — one source,
  never two, and never both listed to manufacture corroboration.
- **Check for replace-not-merge**: Krk `G100002043000` `Capacity [ref]` had its GIIGNL citation replaced
  outright by a euractiv link. Run `audit_ref_drops.py` over your country and merge back anything still valid.

---

## Per-country dead-citation counts (from the QC sweep)

Belgium 12 · Albania 8 · Italy 48 · Malta 3 · Spain 15 · Germany 21 · Gibraltar 1 · France 7 ·
Netherlands 2 · Croatia 0 · Greece 0 · Montenegro 0 · Portugal 0.

Full per-URL verdicts: `batches/staging/qc-natalia-europe/citqc_<Country>.json`
(fields: `unit_id`, `ref_column`, `url`, `verdict`, `reason`).
