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

And it emits a DORMANT-REVIVAL WATCH (compute_dormant_revival_watch): the OTHER
discovery blind spot. A GEM terminal that is wholly cancelled/shelved is a dead
SITE, and a brand-new project at that site (different sponsor, different design)
is a NEW terminal per the dead-and-revived rule (lifecycle_rules.md) — but nothing
in the routine workflow revisits dead records to ask "did something new rise here?"
(stale_sweep's dev_pipeline covers shelved for the Update worklist but never
cancelled, and it re-verifies the EXISTING record, not a new project at the site).
This block lists every wholly cancelled/shelved in-scope terminal as a Discovery
revival-check worklist, prioritizing long-dead sites (5+ y → a new project at the
same site is plausible, Discovery SOP §12). This is exactly the class of miss that
let "POIC Lahad Datu" (a 2026 FSU project on the site of the 2016-cancelled "Lahad
Datu Sabah LNG Terminal") slip past a discovery sweep.

NEVER flags read-only/computed columns (you can't write them — the backend
recomputes) or out-of-scope "no longer updated as of 2026" columns (LH2/NH3/PCI…).
Boolean fields are never "missing" — blank encodes False per the schema.

Usage:
    python completeness_sweep.py
    # Reads ./gem_export.csv + .colmap.json, writes work/completeness_sweep.json
    python completeness_sweep.py --country "United States"   # field audit only
    python completeness_sweep.py --no-coverage              # skip coverage gap

    python completeness_sweep.py --no-dormant-watch        # skip dormant-revival watch

Library:
    from completeness_sweep import (compute_gaps, compute_coverage_gap,
                                    compute_dormant_revival_watch)
    gaps = compute_gaps("./gem_export.csv")
    coverage = compute_coverage_gap("./gem_export.csv")
    dormant = compute_dormant_revival_watch("./gem_export.csv")

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
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from normalize import normalize_country  # noqa: E402
from colmap import load_colmap as _load_colmap  # noqa: E402

try:
    from country_universe import COASTAL_COUNTRIES
except ImportError:  # coverage-gap check degrades gracefully if the list is absent
    COASTAL_COUNTRIES = set()

# ---------------------------------------------------------------------------
# Column policy — all sourced from docs/reference/gem_db_schema.md.
# Exact header strings (note "Country/Area", "CapacityinBcm/y", "… [ref]").
# ---------------------------------------------------------------------------

# Computed/rollup + DB-assigned, and "no longer updated as of 2026" columns —
# the build script must never write these, so a blank here is not actionable.
# Canonical sets live in schema_constants.py (shared with build_review_package.py
# / pull_gem_db.py). (gem_db_schema.md "Read-only column list".)
from schema_constants import COMPUTED_COLUMNS, OUT_OF_SCOPE_COLUMNS

EXCLUDED = COMPUTED_COLUMNS | OUT_OF_SCOPE_COLUMNS  # never flagged by any check

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

# [ref] columns whose data column is owned by a dedicated workflow with its own
# inclusion rules — a standard Update batch must not half-apply those rules from
# a blank-ref flag. CaptiveGasPower: the captive-power SOP (§9) owns the pair
# (>50 MW threshold, mechanical-drive flagging). Orphan-ref (Rule F) still applies.
WORKFLOW_OWNED_REFS = {"CaptiveGasPower [ref]"}

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
                    if ref_col in WORKFLOW_OWNED_REFS:
                        continue  # owned by a dedicated workflow, not an Update fill target
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


def _parse_year(v):
    """Pull a 4-digit year out of a cell like '2016', '2016.0', 'cancelled 2016'."""
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    # tolerate floats and trailing text
    for tok in s.replace(",", " ").split():
        tok = tok.split(".")[0]
        if tok.isdigit() and len(tok) == 4:
            y = int(tok)
            if 1900 <= y <= 2100:
                return y
    head = s.split(".")[0]
    if head.isdigit() and len(head) == 4:
        return int(head)
    return None


DORMANT_STATUSES = {"cancelled", "shelved"}


def compute_dormant_revival_watch(csv_path, country_filter=None, today=None):
    """List wholly cancelled/shelved in-scope terminals as a Discovery revival worklist.

    A terminal counts as DORMANT only if EVERY one of its unit-rows is cancelled or
    shelved — a terminal with any living (proposed/construction/operating/idle/…)
    unit is an active project, not a dead site. For each dormant terminal we report
    the death status (cancelled outranks shelved), the death year (max across units),
    years-since-death, and a revival_priority:

      - "high"        → dead 5+ years: a fresh proposal here is likely a NEW distinct
                        project at the same site, not a revival of this record
                        (Discovery SOP §12). These are the ones a sweep most often misses.
      - "normal"      → dead < 5 years.
      - "unknown_age" → no parseable death year.

    The Discovery sweep should web-search each of these sites for new activity (new
    sponsor, new FSU/FSRU charter, new permit) and, per the dead-and-revived rule
    (lifecycle_rules.md), stage a genuinely different new project as a NEW terminal
    (AssociatedTerminals → the dead record) rather than overwriting the dead record.

    Read via the snake_case colmap keys (like compute_coverage_gap); global by
    design unless country_filter is given.
    """
    if today is None:
        today = date.today()

    colmap = _load_colmap(csv_path)
    ci_tid = colmap.get("terminal_id")
    ci_fuel = colmap.get("fuel")
    ci_country = colmap.get("country")
    ci_status = colmap.get("status")
    if ci_tid is None or ci_status is None:
        return {"error": "terminal_id/status missing from colmap"}

    ci_name = colmap.get("terminal_name")
    ci_loc = colmap.get("location")
    ci_state = colmap.get("state_province")
    ci_district = colmap.get("prefecture_district")
    ci_owner = colmap.get("owner")
    ci_cancelled_yr = colmap.get("cancelled_year")
    ci_shelved_yr = colmap.get("shelved_year")

    def g(row, i):
        return row[i].strip() if i is not None and i < len(row) and row[i] else ""

    terminals = defaultdict(lambda: {"statuses": set(), "cancelled_yrs": [],
                                     "shelved_yrs": [], "rep": None})
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)  # header
        for row in reader:
            if len(row) < colmap["_total_columns"]:
                continue
            if ci_fuel is not None and row[ci_fuel] != "LNG":
                continue
            if country_filter and ci_country is not None and row[ci_country] != country_filter:
                continue
            tid = g(row, ci_tid)
            if not tid:
                continue
            rec = terminals[tid]
            rec["statuses"].add(g(row, ci_status).lower())
            cy = _parse_year(g(row, ci_cancelled_yr))
            sy = _parse_year(g(row, ci_shelved_yr))
            if cy:
                rec["cancelled_yrs"].append(cy)
            if sy:
                rec["shelved_yrs"].append(sy)
            if rec["rep"] is None:
                rec["rep"] = row

    watch = []
    for tid, rec in terminals.items():
        statuses = {s for s in rec["statuses"] if s}
        if not statuses or not statuses.issubset(DORMANT_STATUSES):
            continue  # has a living unit, or unknown status — not a dead site
        row = rec["rep"]
        death_status = "cancelled" if "cancelled" in statuses else "shelved"
        death_yrs = rec["cancelled_yrs"] if death_status == "cancelled" else rec["shelved_yrs"]
        # fall back to whichever year list is populated
        if not death_yrs:
            death_yrs = rec["cancelled_yrs"] or rec["shelved_yrs"]
        death_year = max(death_yrs) if death_yrs else None
        if death_year is None:
            years_dead, priority = None, "unknown_age"
        else:
            years_dead = today.year - death_year
            priority = "high" if years_dead >= 5 else "normal"
        loc_bits = [g(row, ci_district), g(row, ci_state), g(row, ci_loc)]
        watch.append({
            "terminal_id": tid,
            "terminal_name": g(row, ci_name),
            "country": g(row, ci_country),
            "location": " — ".join(b for b in loc_bits if b),
            "prior_owner": g(row, ci_owner),
            "death_status": death_status,
            "death_year": death_year,
            "years_dead": years_dead,
            "revival_priority": priority,
        })

    order = {"high": 0, "normal": 1, "unknown_age": 2}
    watch.sort(key=lambda w: (order[w["revival_priority"]],
                              -(w["years_dead"] or 0), w["country"], w["terminal_name"]))
    by_priority = Counter(w["revival_priority"] for w in watch)
    return {
        "dormant_count": len(watch),
        "by_priority": dict(by_priority),
        "watch": watch,
        "_note": (
            "Wholly cancelled/shelved in-scope terminals = dead SITES to revival-check "
            "during Discovery (Discovery SOP §4.0a / §6). A genuinely different new "
            "project at one of these sites is a NEW terminal per the dead-and-revived "
            "rule (lifecycle_rules.md), not an edit to the dead record. 'high' priority "
            "= dead 5+ years (Discovery SOP §12). This is the blind spot that let POIC "
            "Lahad Datu slip past a sweep."
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
    p.add_argument("--output", "--out", dest="out", default="work/completeness_sweep.json")
    p.add_argument("--country",
                   help="Filter the field audit + dormant watch to one country "
                        "(coverage gap stays global)")
    p.add_argument("--no-coverage", action="store_true",
                   help="Skip the country coverage-gap check")
    p.add_argument("--no-dormant-watch", action="store_true",
                   help="Skip the dormant-revival watch (cancelled/shelved sites to recheck)")
    p.add_argument("--today", help="Override today's date (YYYY-MM-DD) for dormant-age calc")
    args = p.parse_args()

    if not Path(args.csv).exists():
        sys.exit(f"ERROR: {args.csv} not found. Run pull_gem_db.py first.")

    today = date.today()
    if args.today:
        today = datetime.strptime(args.today, "%Y-%m-%d").date()

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

    dormant = None
    if not args.no_dormant_watch:
        dormant = compute_dormant_revival_watch(args.csv, country_filter=args.country, today=today)
        n = dormant.get("dormant_count", 0)
        bp = dormant.get("by_priority", {})
        print(f"\n  Dormant-revival watch: {n} wholly cancelled/shelved site(s) to revival-check"
              f"{f' ({args.country})' if args.country else ''}"
              f" — {bp.get('high', 0)} high-priority (dead 5+ y)")
        for w in dormant.get("watch", [])[:10]:
            yd = f"{w['years_dead']}y" if w["years_dead"] is not None else "age?"
            print(f"    [{w['revival_priority']:>11}] {w['death_status']:>9} {yd:>4}  "
                  f"{w['country']}: {w['terminal_name']}")
        if n > 10:
            print(f"    … and {n - 10} more (see {args.out})")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(
        {"summary": summary, "gaps": gaps, "coverage_gap": coverage,
         "dormant_revival_watch": dormant},
        indent=2, default=str))
    print(f"\n  Saved to {args.out}")


if __name__ == "__main__":
    main()
