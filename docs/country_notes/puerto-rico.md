# Puerto Rico

US territory, so the US federal source tier applies *plus* a territorial regulator. Three GEM
terminals: Peñuelas (operating, EcoEléctrica JV), San Juan (operating, New Fortress Energy),
Aguirre GasPort FSRU (cancelled 2019, Excelerate).

## Resources

- **FERC** — eLibrary dockets. The San Juan jurisdictional case is **CP20-466** (FERC asserted
  jurisdiction over the NFE San Juan facility); the Aguirre Offshore GasPort proceeding was
  terminated in 2019. FERC filings are the best primary source for what these facilities
  *physically are* (berths, storage, regas trains) — better than trade press.
- **DOE / FECM** — LNG import/export authorizations naming Puerto Rico.
- **Puerto Rico Energy Bureau (PREB)** — `energia.pr.gov`. Dockets on gas supply, generation RFPs,
  and the Integrated Resource Plan. The IRP + PREB procurement dockets are the strongest *forward*
  signal for a new import terminal; check these before trade press on any discovery run.
- **PREPA / Genera PR / LUMA Energy** — generation-conversion and gas-supply procurements.
  Genera PR (the private generation operator) is a New Fortress Energy subsidiary, which is also
  the San Juan terminal's owner — note the vertical relationship when reading gas-supply awards.
- **EIA** — Puerto Rico territory profile / LNG import series.
- Local press (Spanish): El Nuevo Día, Noticel, Metro PR, Primera Hora, Sin Comillas, El Vocero,
  Caribbean Business. Useful Spanish query terms: `terminal de gas natural licuado`,
  `regasificación`, `barcaza de gas`, `muelle de GNL`.

## Research Tips

- **Scope trap — domestic vs cross-border.** Puerto Rico is a US territory, so LNG shipped from the
  US mainland is *domestic* Jones Act traffic, not a border crossing. Both PR terminals are in scope
  because they receive marine LNG cargoes, but the island is also heavily served by **LNG-by-truck /
  ISO-container virtual pipeline** distribution — GIIGNL flags "Truck loading" at both terminals.
  A trucked-supply-only or peak-shaving facility is OUT OF SCOPE (Discovery SOP §3).
- **Power-plant ≠ terminal.** Gas-conversion projects at the PREPA plants (Palo Seco, Aguirre,
  Costa Sur, Mayagüez, Cambalache, Yabucoa) are GOGPT power stations fed by existing terminals, not
  new LNG terminals — even when the announcement bundles "LNG receiving" language.
- **San Juan's GIIGNL type cell reads "Onshore + FSU", not "Onshore"** — the "+ FSU" wraps onto a
  second `pdftotext -layout` line, so a naive grep of the terminal row misses it and makes GEM's
  `Offshore`/`Floating` = True look wrong. It isn't: FERC's show-cause order (174 FERC ¶61,207,
  Docket CP20-466) describes an FSU **semi-permanently moored at San Juan Harbor**, and PR has no
  entry in GIIGNL's FSRU *fleet* table simply because an FSU is not an FSRU (no onboard regas).
  Corroborating convention: across the whole export the two flags are only ever set together
  (352 True/True, 12 True/blank, 909 blank/blank, **zero False/True**) — so `Floating` True with
  `Offshore` False would itself be the anomaly. **The FSU's vessel name is still unidentified**;
  FERC never names it, and "Coral Encanto" is *not* it (AIS shows that vessel trading in the West
  Mediterranean as of Nov 2025). `FloatingVesselName` stays blank until a primary source names it.
- **Peñuelas capacity history in GIIGNL:** 1.5 mtpa (2020 ed.) → 2.0 (2024 ed.) → 1.5 base + a
  separate "Peñuelas expansion" 0.5 mtpa row with start year 2020 (2025 ed.) → 2.0 single line
  (2026 ed.). The 2.0 total is stable; the open question is whether GEM should split the project
  into a 1.5 base unit + 0.5 expansion unit, not whether the total is right.
- **Peñuelas 2.5% owner:** GIIGNL 2024/2025/2026 name **OCO Partners**; the 2021 edition's narrative
  records that **GE Capital sold its 2.5% Peñuelas share**. GEM long carried "EcoElectrica LP [2.5%]"
  — the JV itself standing in for the unknown minority holder. OCO Partners is **not** in the GEM
  entity system (checked against Postgres `entity_history` 2026-07-28) — it needs creating.
- **Peñuelas `Parent` cell is duplicated (197.5%)** in the live DB: the Naturgy/ENGIE/Mitsui block
  appears twice, with *two different* Mitsui entities — `Mitsui Group` (E100000134078) and
  `Mitsui & Co Ltd` (E100000000651). When fixing, keep `unknown [2.5%]` rather than OCO Partners so
  `Parent` stays in lockstep with `Parent GEM Entity ID` = E100000132388, which is GEM's literal
  "unknown" placeholder; the two Mitsui entities may warrant a tracker-wide merge.
- **The gas-supply contract, not the plant announcement, is the `PowerPlantsSupplied` source.**
  NFEnergia's 15 Mar 2024 NGSPA with PREPA names the delivery points — San Juan and Palo Seco are
  firm; Cambalache (NEPR docket MI-2024-0004) and Mayagüez (Feb-2025 conditional approval) are
  pending PREB action and should not be staged until approved.

## Update notes

- *AI-draft, 2026-07-28* — exhaustive-tier Update + Discovery pass; see
  `batches/run_records/2026-07-28_puerto-rico_exhaustive-update-and-discovery.md`.
