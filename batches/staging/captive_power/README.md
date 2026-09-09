# Captive-power staging — FROZEN (2026-09-09)

The captive-power cross-tracker workflow is **complete**: the tracker was 100%
crawled as of 2026-08-02 (africa + oceania closed that evening), and the four
full-region deliverable workbooks in `batches/deliverables/` supersede every
earlier increment. See `docs/sops/captive_power.md` §9 and the run records.

**Everything under this directory is a frozen run artifact, not maintained tooling.**

That includes the 23 one-off Python files here — the per-region
`_assemble_<region>.py`, `_build_dispatch.py`, `_compute_neighbors.py`,
`_enrich_neighbor_ids.py`, `_merge_full_regions.py`, `_merge_drive_deliverables.py`
and the regional-export pair. They were written per region, diverge from each
other in small ways, and are kept only so a past batch can be traced.

**Do not:**

- Import, extend, or copy them as a starting point for new work.
- Treat any of them as the canonical assembler. The canonical one is
  `batches/staging/_assemble.py`.
- Spend effort parameterizing or deduplicating them — this was considered on
  2026-09-09 and deliberately declined, because the workflow that produced them
  is finished (`docs/improvement_plan.md`, Phase 4).

If captive-power research ever reopens, write a fresh parameterized assembler
against the canonical staging contract rather than reviving one of these.
