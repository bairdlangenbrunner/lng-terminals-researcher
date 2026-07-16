"""
Shared GEM column-name sets — canonical source for the out-of-scope /
read-only column lists duplicated (in header-string form) across
completeness_sweep.py, pull_gem_db.py, and build_review_package.py.

These mirror the methodology's "no longer updated as of 2026" list plus the
GEM-computed/rollup columns, and are enforced by build_review_package.py (the
build script must never write to them). Column names are the exact
gem_export.csv header strings (e.g. "Country/Area", "CapacityinBcm/y",
"… [ref]") per docs/reference/gem_db_schema.md.

Verified identical in membership across all three duplicated copies as of this
consolidation (2026-07) — pull_gem_db.py's copy used its own short/canonical
column-name keys (e.g. "capacity_mtpa" instead of "CapacityinMtpa") rather than
header strings, but maps 1:1 onto the same 13 + 11 columns via its
EXPECTED_COLUMNS table; see pull_gem_db.py for the derived translation.
"""

# GEM-computed / DB-assigned columns. The build script must never write these
# (a blank here is not actionable research-wise — the backend recomputes it).
COMPUTED_COLUMNS = {
    "TerminalID", "UnitID", "Wiki",
    "CapacityinMtpa", "CapacityinBcm/y",
    "TotImportLNGTerminalCapacityinMtpa", "TotImportLNGTerminalCapacityinBcm/y",
    "TotExportLNGTerminalCapacityinMtpa", "TotExportLNGTerminalCapacityinBcm/y",
    "CostUSD", "CostEuro",
    "TotKnownTerminalCostsUSD", "TotTerminalCost [ref]",
}

# "No longer updated as of 2026" per the methodology — never write or flag.
OUT_OF_SCOPE_COLUMNS = {
    "PCINotes", "PCI3", "PCI4", "PCI5", "PCI6",
    "LH2", "NH3", "SyntheticLNG", "RetrofitProposed",
    "AltFuelPrelimAgreement", "AltFuelCallMarketInterest",
}

READ_ONLY_COLUMNS = COMPUTED_COLUMNS | OUT_OF_SCOPE_COLUMNS
