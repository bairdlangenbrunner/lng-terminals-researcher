# Georeference SOP — deriving terminal coordinates

Rev 1 (2026-07-29, from the Aguirre GasPort FSRU case — cancelled FERC project whose only
location evidence is an EIS figure).

Governs how a batch derives or corrects a `Latitude`/`Longitude` pair when GEM's coordinate
is missing, `approximate`, or demonstrably wrong. The output is a normal staged update
(Update SOP conventions apply: url_verifier gate, ≥2-independent-or-primary confidence,
`Location [ref]` as the ref column). The methodology doc's Location section is authoritative
on `Accuracy` semantics and recommended satellite products.

## §1 Scope and when to invoke

- A completeness sweep or QC pass flags a blank/`approximate` coordinate, or research shows
  the stored point is wrong (e.g. it marks a nearby landmark, not the facility).
- A discovery candidate needs its first coordinate.
- Never invoked to second-guess an `exact` coordinate that already matches satellite imagery —
  spot-checking those is QC, not this SOP.

## §2 Decision ladder — try each rung in order, stop at the first that resolves

**§2.0 Built facilities: mapping services + OSM first.** If the terminal physically exists
(operating / idled / mothballed / retired / under construction with visible works), find it in
satellite/mapping products before touching any document:
- Google Maps, Bing, Yandex, Apple Maps satellite layers; Esri World Imagery
  [Wayback](https://livingatlas.arcgis.com/wayback/) for a facility that existed but was removed.
- OpenStreetMap (search + Overpass; industrial/harbour tagging often outlines LNG berths).
- FSRUs/FLNGs: VesselFinder / MarineTraffic current or historical position of the named vessel.
- Read the coordinate off the regas/liquefaction works or the berth itself (unit convention:
  the facility, not the site office). This yields `Accuracy = exact` per the methodology
  ("you find the terminal location in Google Maps or other GIS software and are sure it's the
  proper location"). `Location [ref]` cites the mapping-service view per the methodology's
  Location Datasource guidance.

**§2.1 Published coordinates.** For unbuilt/cancelled projects (and built ones §2.0 couldn't
pin): search the paper trail for explicit lat/lon — FERC dockets/eLibrary, EIS/EA text layers
(grep the PDF text for `°`, `latitude`, `N latitude`, DMS patterns), USACE public notices,
Federal Register notices, Coast Guard deepwater-port dockets, NOAA chart notes, pilot books,
sponsor FEED/tender documents. A regulator-published coordinate is Tier 1 and cites directly.

**§2.2 Graticule interpolation.** If the best available map figure carries a lat/lon graticule
(ticks or grid lines), interpolate the target between graticule lines by pixel measurement —
no imagery matching needed. Cross-check against the scale bar.

**§2.3 Figure georeferencing** (`scripts/georeference_figure.py`) — the last rung, for a
figure with no graticule and no published coordinate (the Aguirre case: DEIS Figure 3.3-1).
Recipe in `docs/workflows.md` §10; method notes in the script docstring. Summary: fetch an
Esri World Imagery mosaic over the figure's area, seed a similarity fit with ≥2 rough
correspondences, let coastline patch-matching refine it, then read the marker's pixel through
the fit.

## §3 Error budget and confidence

- The tool prints GCP residual RMSE (ground meters) and leave-one-out spread at the target
  point. Under ~15 m RMSE with <10 m LOO is normal for a z15 mosaic and a good-quality figure;
  treat >30 m RMSE or LOO > RMSE as a failed fit — re-seed or add GCPs, don't stage.
- **Cross-check both**: (a) fitted m/px vs the figure's scale bar (agree within ~5%);
  (b) the derived point vs any documented distance ("~3 miles offshore of X"). A disagreement
  is a fit error until proven otherwise.
- Confidence for a coordinate derived from ONE regulatory figure is **green** (primary/
  regulatory source) — but only after the §4 visual verification passes. A same-document
  second figure is corroboration of your reading, not a second source.

## §4 Visual verification is mandatory

`point` writes THREE overlays: `verify_point.png` (satellite crop centered on the derived
point, GCPs in green), `verify_full.png` (whole mosaic), and `verify_fig.png` (the derived
point + lat/lon marked **on the source figure itself** — this closes the round trip: the
crosshair must land on the figure's own marker). **View all three** and confirm the point sits
where the figure says it should relative to coastline/landmarks. Copy the overlays plus
`fit.json` into the batch's staging dir (`batches/staging/<region>/georef_<slug>/`) as the
audit trail — the user reviews the coordinate against these images, and (per user directive
2026-07-29) all three are part of the deliverable whenever a coordinate is derived this way;
the figure-side overlay is not optional (the point must be shown on the actual georeferenced
image, not just on satellite imagery).

## §5 Staging conventions

- Stage `Latitude` and `Longitude` as two update records, both with `ref_field =
  "Location [ref]"` and the figure's document URL in `ref_urls`. The URL must pass
  `url_verifier.py` with tokens proving the figure is in the document (e.g. the figure number
  + the marker's legend label), not just the project name.
- `source_notes` must record: the document + figure number + PDF page, the tool + fit quality
  (RMSE, LOO), and the cross-checks. A future reader must be able to re-derive the point.
- **`Accuracy`:** methodology-defined. Never-built (proposed/shelved/cancelled) projects stay
  `approximate` regardless of fit quality — "the terminal is not yet built and it's an
  approximated location". A built facility located via §2.0 or a regulator-published
  coordinate (§2.1) is `exact`.
- The existing `Location [ref]` cell merges (never replaces) per the Update SOP ref rules.

## §6 Pitfalls (each cost real time — don't rediscover them)

- **Match satellite-to-satellite.** The reference mosaic is Esri World Imagery, never an OSM/
  cartographic render: cross-modal NCC has a flat correlation surface — fits crawl and
  misconverge (the original Aguirre attempt).
- **Never brute-force the 4-D transform.** Two rough seed pairs pin scale/rotation/translation
  in closed form; local ±N px NCC per GCP does the rest in seconds.
- **The marker is a symbol, not a footprint.** A colored square/triangle marks a point; don't
  read its pixel extent as facility dimensions unless the figure says the shape is to scale.
- **Line-drawn figures** (engineering drawings, no imagery base) defeat NCC — use ≥4 careful
  `--seed` pairs + `--seed-only`, and widen the error bars accordingly.
- **Extent limit:** a similarity fit ignores projection curvature; beyond ~40 km of figure
  extent, split the figure or accept degraded RMSE (the tool warns).
- **Mask annotations.** Legends, labels, and margins poison auto-GCPs; pass `--map-bottom` (and
  trust the tool's saturation/label mask) so GCPs land on imagery only.
- **Figure page ≠ report page.** Cite the PDF page AND the printed report page; verify the
  figure exists in the exact PDF you cite (mirrors differ — the DEIS on energy.gov ≠ a
  same-named file elsewhere; render the cited copy's page before staging).
