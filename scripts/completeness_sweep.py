"""
completeness_sweep.py — whole-export field-completeness + blank-[ref] audit.

The companion to stale_sweep.py. Where stale_sweep is purely status/date-driven
(it only reads Status, LastUpdated and a couple of anchor years), this walks
EVERY in-scope LNG unit-row across ALL 115 columns and flags content gaps:

  1. blank_ref     — a data value is present but its paired [ref] cell is empty
                     (a [ref]-fill target; carrier-project Rule F, the "no orphan
                     citations" rule, read in reverse). High-yield columns per the
                     blank-rate table in docs/reference/gem_db_schema.md.
  2. orphan_ref    — a [ref] cell is filled but its paired data value is blank
                     (a Rule F *violation* — a citation with nothing to cite).
  3. missing_field — a field required for the unit's lifecycle status is blank
                     (e.g. an operating unit with no Capacity or no ActualStartYear).

Plus two structural checks the diff/update scripts don't cover:

  4. project_field_inconsistent — a project-level field differs across the
     unit-rows of a single terminal. Violates the CLAUDE.md hard rule
     "project-level field changes apply to ALL unit-rows" and will surface as
     an inconsistency in the next export.
  5. suspect_enum_value — an enum cell holds a value outside the catalog in
     gem_db_schema.md. The schema says flag these, don't auto-accept.

It ALSO emits a country COVERAGE GAP (compute_coverage_gap): the rest of the
workflow only ever looks at countries already in the export, so a country with
ZERO GEM LNG terminals is a blind spot no field audit can see. The check diffs a
reference coastal-country universe (country_universe.py) against the GEM-covered
set and returns the uncovered coastal countries as a discovery worklist — the
"are we missing a whole country?" question. See the Discovery SOP: iterate
covered ∪ uncovered, not just covered.

NEVER flags read-only/computed columns (you can't write them — the backend
recomputes) or out-of-scope "no longer updated as of 2026" columns (LH2/NH3/PCI…).
Boolean fields are never "missing" — blank encodes False per the schema.

Usage:
    python completeness_sweep.py
    # Reads ./gem_export.csv + .colmap.json, writes work/completeness_sweep.json
    python completeness_sweep.py --country "United States"   # field audit only
    python completeness_sweep.py --no-coverage              # skip coverage gap

Library:
    from completeness_sweep import compute_gaps, compute_coverage_gap
    gaps = compute_gaps("./gem_export.csv")
    coverage = compute_coverage_gap("./gem_export.csv")

NOTE: the required-field POLICY (ALWAYS_REQUIRED / REQUIRED_BY_STATUS /
FLOATING_REQUIRED below) is the part that encodes methodology judgment, not just
schema mechanics — review it against the GEM LNG Terminals Manual before trusting
the missing_field counts. The blank_ref / orphan_ref / enum checks are mechanical
and follow directly from the schema.
"""
import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from normalize import normalize_country  # noqa: E402

try:
    from country_universe import COASTAL_COUNTRIES
except ImportError:  # coverage-gap check degrades gracefully if the list is absent
    COASTAL_COUNTRIES = set()

# ---------------------------------------------------------------------------
# Column policy — all sourced from docs/reference/gem_db_schema.md.
# Exact header strings (note "Country/Area", "CapacityinBcm/y", "… [ref]").
# ---------------------------------------------------------------------------

# Computed/rollup + DB-assigned — the build script must never write these, so a
# blank here is not actionable. (gem_db_schema.md "Read-only column list".)
READONLY = {
    "CapacityinMtpa", "CapacityinBcm/y",
    "TotImportLNGTerminalCapacityinMtpa", "TotImportLNGTerminalCapacityinBcm/y",
    "TotExportLNGTerminalCapacityinMtpa", "TotExportLNGTerminalCapacityinBcm/y",
    "CostUSD", "CostEuro",
    "TotKnownTerminalCostsUSD", "TotTerminalCost [ref]",
    "TerminalID", "UnitID", "Wiki",
}

# "No longer updated as of 2026" per methodology — never flag.
OUT_OF_SCOPE = {
    "PCINotes", "PCI3", "PCI4", "PCI5", "PCI6",
    "LH2", "NH3", "SyntheticLNG", "RetrofitProposed",
    "AltFuelPrelimAgreement", "AltFuelCallMarketInterest",
}

EXCLUDED = READONLY | OUT_OF_SCOPE  # never flagged by any check

# Klass=P columns from the gem_db_schema.md 115-col table. A blank/defect in one
# of these is reported ONCE per terminal (on the representative row), and these
# are the columns the cross-unit consistency check applies to.
PROJECT_LEVEL = {
    "TerminalID", "Wiki", "TerminalName", "Fuel", "Country/Area",
    "ResearcherNotesProject", "OtherNames", "LocalNames", "Language",
    "Operator", "Operator [ref]",
    "TotImportLNGTerminalCapacityinMtpa", "TotImportLNGTerminalCapacityinBcm/y",
    "TotExportLNGTerminalCapacityinMtpa", "TotExportLNGTerminalCapacityinBcm/y",
    "PlannedStopYear", "TempFacility", "ImportExportOnly",
    "Location", "Region", "SubRegion", "Prefecture/District", "State/Province",
    "Latitude", "Longitude", "Accuracy", "Location [ref]",
    "AssociatedTerminals", "AssociatedTerminals [ref]",
    "Source", "Source [ref]",
    "PowerPlantsSupplied", "PowerPlantsSupplied [ref]",
    "CaptiveGasPower", "CaptiveGasPower [ref]",
    "Pipelines", "Pipelines [ref]",
    "TotKnownTerminalCostsUSD", "TotTerminalCost [ref]",
    "Offshore", "Floating", "FloatingVesselName", "FloatingVesselName [ref]",
    "VesselOwner", "VesselOwner [ref]", "VesselParent",
    "VesselOperator", "VesselOperator [ref]",
    "Opposition", "ESJNotes", "Defeated", "CCS", "CCSNotes",
    "PCINotes", "PCI3", "PCI4", "PCI5", "PCI6",
    "LH2", "NH3", "SyntheticLNG", "RetrofitProposed",
    "AltFuelPrelimAgreement", "AltFuelCallMarketInterest",
}

# Blank encodes False — never "missing", and they don't need a [ref] unless True.
BOOLEAN_FIELDS = {
    "Offshore", "Floating", "ImportExportOnly", "CaptiveGasPower",
    "Opposition", "Defeated", "CCS",
}

# ---------------------------------------------------------------------------
# [ref] pairing. Most "X [ref]" cells pair with the data column "X", but four
# date/rollup refs do NOT have an identically-named data column — alias them.
# ---------------------------------------------------------------------------
REF_DATA_ALIASES = {
    "ProposalDate [ref]": ["ProposalYear", "ProposalMonth"],
    "ConstructionDate [ref]": ["ConstructionYear", "ConstructionMonth"],
    "StartDate [ref]": [
        "ActualStartYear", "ActualStartMonth", "ActualStartYear2", "ActualStartYear3",
    ],
    # TotTerminalCost [ref] pairs with a computed rollup — skip entirely.
}
SKIP_REFS = {"TotTerminalCost [ref]"}

# [ref] columns whose paired data is densely populated → a blank ref here is a
# high-yield fill target (gem_db_schema.md "[ref]-fill targets in order of yield").
HIGH_YIELD_REFS = {
    "Capacity [ref]", "ConstructionDate [ref]", "ProposalDate [ref]",
    "Operator [ref]", "Cost [ref]", "StartDate [ref]", "Status [ref]",
}

# ---------------------------------------------------------------------------
# Required-field POLICY (methodology judgment — review before trusting).
# ---------------------------------------------------------------------------
ALWAYS_REQUIRED = [
    "TerminalName", "Country/Area", "Status", "FacilityType",
    "Owner", "Latitude", "Longitude",
]
REQUIRED_BY_STATUS = {
    "operating":    ["Capacity", "CapacityUnits", "ActualStartYear"],
    "construction": ["Capacity", "CapacityUnits", "LatestPlannedStartYear"],
    "proposed":     [],  # capacity/timing often genuinely unknown this early
    "shelved":      ["ShelvedYear"],
    "cancelled":    ["CancelledYear"],
    "idled":        ["StopYear"],
    "mothballed":   ["StopYear"],
    "retired":      ["StopYear"],
}
# Required only when Floating == "True" (also an FSRU sync touchpoint).
FLOATING_REQUIRED = ["FloatingVesselName"]

# ---------------------------------------------------------------------------
# Enum catalogs (gem_db_schema.md). Non-blank values outside these are suspect.
# Blanks are handled by the required-field logic, not here.
# ---------------------------------------------------------------------------
ENUM_CATALOGS = {
    "Status": {"proposed", "construction", "operating", "idled", "mothballed",
               "retired", "shelved", "cancelled"},
    "Substatus": {"actual", "confirmed", "inferred 2 y", "inferred 4 y"},
    "FacilityType": {"import", "export"},
    "Accuracy": {"exact", "approximate"},
    "FIDStatus": {"Pre-FID", "FID"},
    "ShelvedCancelledStatusType": {"inferred", "confirmed"},
    # For LNG terminals the schema says use mtpa or bcm/y only.
    "CapacityUnits": {"mtpa", "bcm/y"},
}


def _load_colmap(csv_path):
    map_path = Path(csv_path).with_suffix(".colmap.json")
    if not map_path.exists():
        raise RuntimeError(
            f"colmap.json not found at {map_path}. Run pull_gem_db.py first."
        )
    colmap = json.loads(map_path.read_text())
    if "_header_columns" not in colmap:
        # pull_gem_db.py strips _header_columns before serializing the colmap
        # to disk, so re-derive the header list from the CSV itself (BOM-safe).
        with open(csv_path, encoding="utf-8-sig") as f:
            colmap["_header_columns"] = next(csv.reader(f))
    return colmap


def _blank(v):
    return v is None or str(v).strip() == ""


def _build_ref_pairs(headers):
    """{ '<X> [ref]': ['<data col>', ...] } for every actionable [ref] column."""
    hset = set(headers)
    pairs = {}
    for h in headers:
        if not h.endswith(" [ref]") or h in SKIP_REFS or h in EXCLUDED:
            continue
        if h in REF_DATA_ALIASES:
            data_cols = [c for c in REF_DATA_ALIASES[h] if c in hset]
        else:
            base = h[: -len(" [ref]")]
            data_cols = [base] if base in hset else []
        data_cols = [c for c in data_cols if c not in EXCLUDED]
        if data_cols:
            pairs[h] = data_cols
    return pairs


def compute_gaps(csv_path, country_filter=None):
    colmap = _load_colmap(csv_path)
    headers = colmap["_header_columns"]
    idx = {name: i for i, name in enumerate(headers)}

    def col(row, name):
        i = idx.get(name)
        return row[i] if i is not None and i < len(row) else None

    ref_pairs = _build_ref_pairs(headers)
    # Project-level columns we actually consistency-check (skip excluded ones).
    consistency_cols = [c for c in PROJECT_LEVEL if c in idx and c not in EXCLUDED]
    enum_cols = {c: cat for c, cat in ENUM_CATALOGS.items() if c in idx}

    ci_tid = idx.get("TerminalID")
    ci_fuel = idx.get("Fuel")
    ci_country = idx.get("Country/Area")

    # Group unit-rows by terminal so project-level checks fire once per project.
    terminals = defaultdict(list)
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # header
        for row in reader:
            if len(row) < colmap["_total_columns"]:
                continue
            if ci_fuel is not None and row[ci_fuel] != "LNG":
                continue  # out of scope per methodology
            if country_filter and ci_country is not None and row[ci_country] != country_filter:
                continue
            terminals[row[ci_tid]].append(row)

    gaps = []

    def add(row, gap_type, column, severity, detail):
        gaps.append({
            "terminal_id": col(row, "TerminalID"),
            "unit_id": col(row, "UnitID"),
            "terminal_name": col(row, "TerminalName"),
            "unit_name": col(row, "UnitName"),
            "country": col(row, "Country/Area"),
            "status": col(row, "Status"),
            "gap_type": gap_type,
            "column": column,
            "severity": severity,
            "detail": detail,
        })

    def is_proj(name):
        return name in PROJECT_LEVEL

    for tid, rows in terminals.items():
        rep = rows[0]

        # --- (4) cross-unit consistency on project-level fields ---
        if len(rows) > 1:
            for name in consistency_cols:
                vals = {(col(r, name) or "").strip() for r in rows}
                if len(vals) > 1:
                    add(rep, "project_field_inconsistent", name, "medium",
                        f"{len(vals)} distinct values across {len(rows)} unit-rows: "
                        f"{sorted(vals)!r} — project-level field must be uniform")

        for ri, row in enumerate(rows):
            is_rep = (ri == 0)
            status = (col(row, "Status") or "").strip()

            # --- (3) required fields ---
            required = list(ALWAYS_REQUIRED) + REQUIRED_BY_STATUS.get(status, [])
            if (col(row, "Floating") or "").strip() == "True":
                required += FLOATING_REQUIRED
            for name in required:
                if name not in idx or name in EXCLUDED or name in BOOLEAN_FIELDS:
                    continue
                if is_proj(name) and not is_rep:
                    continue  # report project-level gap once
                if _blank(col(row, name)):
                    sev = "high" if name in ALWAYS_REQUIRED else "medium"
                    add(row, "missing_field", name, sev,
                        f"{status or 'unknown-status'} unit missing required field {name!r}")

            # --- (1)+(2) ref pairing ---
            for ref_col, data_cols in ref_pairs.items():
                proj = is_proj(ref_col) or any(is_proj(d) for d in data_cols)
                if proj and not is_rep:
                    continue
                data_present = any(not _blank(col(row, d)) for d in data_cols)
                ref_present = not _blank(col(row, ref_col))
                if data_present and not ref_present:
                    sev = "medium" if ref_col in HIGH_YIELD_REFS else "low"
                    add(row, "blank_ref", ref_col, sev,
                        f"{'/'.join(data_cols)} populated but {ref_col} blank — [ref]-fill target")
                elif ref_present and not data_present:
                    add(row, "orphan_ref", ref_col, "medium",
                        f"{ref_col} filled but {'/'.join(data_cols)} blank — Rule F violation")

            # --- (5) suspect enum values ---
            for name, catalog in enum_cols.items():
                if name in EXCLUDED:
                    continue
                if is_proj(name) and not is_rep:
                    continue
                v = (col(row, name) or "").strip()
                if v and v not in catalog:
                    add(row, "suspect_enum_value", name, "medium",
                        f"{name}={v!r} not in catalog {sorted(catalog)!r}")

    return gaps


def compute_coverage_gap(csv_path):
    """Diff the reference coastal-country universe against GEM-covered countries.

    dedup_index.py, the discovery dedup, and the regional sweep are all keyed off
    countries that ALREADY appear in the export, so a country with zero GEM LNG
    terminals is invisible to them. Returns the uncovered coastal countries as a
    discovery worklist, plus a self-check list of GEM-covered countries missing
    from the reference set (extend country_universe.py, or fix a name there, so a
    real country never reads as a false gap).

    Both sides are normalized via normalize_country() so alias/canonical
    differences (USA↔United States, Türkiye↔Turkey) fold out. Global by design —
    ignores any per-country field-audit filter.
    """
    if not COASTAL_COUNTRIES:
        return {"error": "country_universe.COASTAL_COUNTRIES unavailable"}

    colmap = _load_colmap(csv_path)
    ci_country = colmap.get("country")
    ci_fuel = colmap.get("fuel")
    if ci_country is None:
        return {"error": "no country column in colmap"}

    covered_raw = set()
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # header
        for row in reader:
            if len(row) < colmap["_total_columns"]:
                continue
            if ci_fuel is not None and row[ci_fuel] != "LNG":
                continue
            c = (row[ci_country] or "").strip()
            if c:
                covered_raw.add(c)

    covered = {normalize_country(c) for c in covered_raw if normalize_country(c)}
    universe = {normalize_country(c) for c in COASTAL_COUNTRIES if normalize_country(c)}

    uncovered = sorted(u for u in universe if u not in covered)
    outside_ref = sorted(c for c in covered if c not in universe)

    return {
        "covered_count": len(covered),
        "reference_count": len(universe),
        "uncovered_coastal": uncovered,
        "gem_countries_outside_reference": outside_ref,
        "_note": (
            "uncovered_coastal = reference coastal countries with ZERO GEM LNG "
            "terminals → discovery worklist (Discovery SOP §4.0: iterate covered "
            "∪ uncovered). gem_countries_outside_reference = GEM-covered countries "
            "absent from country_universe.py → add them there (or fix a name) so "
            "they don't read as a false gap."
        ),
    }


def summarize(gaps):
    by_type = Counter(g["gap_type"] for g in gaps)
    by_sev = Counter(g["severity"] for g in gaps)
    by_country = Counter(g["country"] for g in gaps)
    fill_targets = Counter(g["column"] for g in gaps if g["gap_type"] == "blank_ref")

    print(f"\n  Total gaps: {len(gaps)}")
    print(f"\n  By type:")
    for k, n in by_type.most_common():
        print(f"    {k:28} {n}")
    print(f"\n  By severity:")
    for k in ("high", "medium", "low"):
        if by_sev.get(k):
            print(f"    {k:28} {by_sev[k]}")
    print(f"\n  Top [ref]-fill targets (blank_ref by column):")
    for k, n in fill_targets.most_common(10):
        print(f"    {k:28} {n}")
    print(f"\n  Top 10 countries by gap count:")
    for c, n in by_country.most_common(10):
        print(f"    {str(c):30} {n}")

    return {
        "by_type": dict(by_type),
        "by_severity": dict(by_sev),
        "fill_targets": dict(fill_targets),
        "by_country": dict(by_country),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", default="./gem_export.csv")
    p.add_argument("--out", default="work/completeness_sweep.json")
    p.add_argument("--country",
                   help="Filter the field audit to one country (coverage gap stays global)")
    p.add_argument("--no-coverage", action="store_true",
                   help="Skip the country coverage-gap check")
    args = p.parse_args()

    if not Path(args.csv).exists():
        sys.exit(f"ERROR: {args.csv} not found. Run pull_gem_db.py first.")

    gaps = compute_gaps(args.csv, country_filter=args.country)
    summary = summarize(gaps)

    coverage = None
    if not args.no_coverage:
        coverage = compute_coverage_gap(args.csv)
        unc = coverage.get("uncovered_coastal", [])
        print(f"\n  Coverage gap: {len(unc)} coastal countries with NO GEM LNG terminal")
        if unc:
            preview = ", ".join(unc[:20])
            print(f"    {preview}{' …' if len(unc) > 20 else ''}")
        outside = coverage.get("gem_countries_outside_reference", [])
        if outside:
            print(f"  NOTE: {len(outside)} GEM countries absent from the reference list "
                  f"(extend country_universe.py): {', '.join(outside)}")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(
        {"summary": summary, "gaps": gaps, "coverage_gap": coverage},
        indent=2, default=str))
    print(f"\n  Saved to {args.out}")


if __name__ == "__main__":
    main()
