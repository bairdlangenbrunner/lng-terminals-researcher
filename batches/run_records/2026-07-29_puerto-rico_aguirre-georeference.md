# 2026-07-29 — Aguirre coordinate georeference + workflow commit

Follow-on to `2026-07-28_puerto-rico_exhaustive-update-and-discovery.md` (same staging
dir, same batch scope). Two jobs: (1) derive the true coordinate of the cancelled
Aguirre Offshore GasPort "Proposed Terminal Site" and stage the fix; (2) commit the
method as a reusable workflow (user: "commit this to a workflow so that it can be
reused… for terminals that are operating… look for the terminal in mapping programs
(google maps, bing, yandex, etc.) and on OSM… first").

## Plan

- The prior session's brute-force 4-D NCC grid search (figure vs OSM render) crawled
  and misconverged. Replacement: seed similarity + local patch NCC against an **Esri
  World Imagery** mosaic (satellite-to-satellite), closed-form fit, error propagation.
- No published coordinate exists for the platform (DEIS/FEIS text layers, Federal
  Register notices, web all searched — route exhausted), so figure georeferencing is
  genuinely required, which validated the ladder design.

## Status / method

- Source figure: DOE/FERC **DEIS EIS-0511 (2014), Figure 3.3-1** "LNG Terminal
  Alternatives", PDF p.74 (report p.3-8); the energy.gov copy was downloaded and its
  p.74 visually confirmed before citing. FEIS has no equivalent figure; DEIS Figure
  3.4-2 (p.80) shows the same site (same-document corroboration only). The raster
  actually georeferenced is a variant render of the same figure whose caption box
  reads "Figure 3.4-1" — the numbering discrepancy was investigated: the energy.gov
  DEIS's list of figures pairs "LNG Terminal Alternatives" with 3.3-1, and its p.74
  caption confirms; the citation stands and the staged source_notes acknowledge the
  variant numbering.
- Tool: `scripts/georeference_figure.py` (written this run) — `fetch` (z15 Esri
  mosaic, 4.54 m/ref px) → `fit` (2 rough seeds, 10 auto-GCPs kept, 12.51 m/figpx,
  rot 0.97°, **RMSE 9.2 m**) → `point --detect cyan` (**LOO rms 2.4 m, max 3.6 m**).
- Validation: tool run with deliberately perturbed seeds reproduced the first
  (hand-scripted) derivation within 1 m; fitted scale matches the figure's 1:53,000
  scale bar; derived point is 3.17 mi from the Aguirre plant vs the documented
  "~3 miles offshore". All THREE verify overlays viewed (mandatory) and kept at
  `batches/staging/puerto-rico/georef_aguirre/` (verify_point.png, verify_full.png,
  verify_fig.png — the point + lat/lon marked on the source figure itself, crosshair
  landing on the cyan "Proposed Terminal Site" square — plus fit.json). The
  figure-side overlay was added mid-run per user directive and is now a standing
  requirement (SOP §4).

## Outcome

- **Result: lat 17.904111, lon -66.230618** (offshore berthing platform site, south of
  the Boca del Infierno cays, Jobos Bay). GEM had **17.9741670, -66.1100000** — ~14 km
  away, near the onshore Aguirre power complex.
- Staged in `batches/staging/puerto-rico/puerto-rico.updates.json` (26 → 28 records):
  `Latitude` + `Longitude` (green, 1b_regulator, ref = `Location [ref]`, DEIS URL —
  url_verifier PASS with tokens "Figure 3.3-1" / "Proposed Terminal Site" / "Aguirre",
  log in the staging dir); existing `Location [ref]` record amended to FEIS + DEIS
  (merge rule). `Accuracy` stays `approximate` per methodology — never-built projects
  are `approximate` by definition regardless of fit quality (checked against the
  methodology doc's Location section this run).
- Rebuilt workbook (supersedes 20260728_2304 and the intermediate 20260729_0955/1129
  rebuilds):
  **`batches/lng_terminals_batch_20260729_1130_ET_puerto-rico_exhaustive_update.xlsx`**
  — 28 updates, no GUARD/REF-DROP warnings (the Lat/Lon value records now declare the
  dead-microsite drop in `dropped_urls_dead`, matching the Location [ref] record);
  meta.json `built` bumped.
- **Workflow committed:** `docs/sops/georeference.md` (rev 1 — §2 decision ladder:
  built → mapping services/OSM first (`exact`), then published coordinates, then
  graticule interpolation, then figure georeferencing; §3 error budget; §4 mandatory
  visual verification, overlays ship with the batch; §5 staging + Accuracy semantics;
  §6 pitfalls), `docs/workflows.md` §10 recipe, CLAUDE.md router row,
  `scripts/README.md` entries, sop_pointers.md (GRF) entries.
