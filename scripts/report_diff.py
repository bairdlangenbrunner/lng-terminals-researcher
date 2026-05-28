"""
Report-vs-GEM reconciliation diff.

Parameterized on report type so the same logic handles GIIGNL today and IGU
(or any future industry report) tomorrow.

Produces a four-way classification per Reconciliation SOP:
  - Match: report row and GEM row exist for the same project (capacity/owner
           may agree or disagree — flagged separately)
  - GIIGNL-only: report shows a project GEM doesn't have (discovery candidate)
  - GEM-only: GEM shows a project the report doesn't list (usually expected —
              GEM tracks more than the report does; see Reconciliation SOP §4)
  - Ambiguous: name/country triggers multiple GEM matches; needs disambiguation

Matching is PROJECT-LEVEL not unit-level — multi-unit GEM projects collapse
to one row for the diff. Per Reconciliation SOP §3.5, this means unit-level
capacity disagreements get reported at the project total level. The decision
to match project-level not unit-level is documented in the SOP; this script
implements that.

Two-pass matching:
  Pass 1: exact (normalized country, normalized site name)
  Pass 2: fuzzy within same country (for surviving GIIGNL-only rows) —
          a candidate is "fuzzy match" if normalized site name is a substring
          match in either direction, OR shares a common token of length ≥4
          AND owner overlap.

Usage:
    python report_diff.py --report giignl \\
        --extracted ./giignl_extracted.csv \\
        --output ./giignl_diff.json
"""
import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from normalize import (
    normalize_country, normalize_entity, normalize_terminal_name,
    parse_entity_list, transliterate_to_english,
)


DEFAULT_GEM_CSV = "./gem_export.csv"

# Matches a trailing " Expansion" / " Extension" qualifier on a report site name.
# GIIGNL splits a phased terminal across "<Site>" and "<Site> Expansion" rows;
# this captures the "<Site>" base so the rows can be folded together (see
# _classify). Requires a non-empty base before the qualifier, so a bare
# "expansion" extraction artifact does NOT match.
_EXPANSION_RE = re.compile(r"^(.*\S)\s+(?:expansion|extension)\s*$", re.IGNORECASE)


def _strip_expansion_suffix(raw):
    """Return the base site name if `raw` ends in 'Expansion'/'Extension', else None."""
    if not raw:
        return None
    m = _EXPANSION_RE.match(str(raw).strip())
    return m.group(1).strip() if m else None


# Matches a trailing unit/complex code on a report site name, e.g. the Algerian
# Sonatrach complexes "Arzew GL1Z" / "Arzew GL2Z" / "Skikda GL1K". The code must
# contain BOTH letters and digits (regex: 1-4 letters, digits, optional trailing
# letter) so plain named stages WITHOUT a digit are never stripped — protects
# "Senboku II", "Bontang Train E", "Corpus Christi Stage III". Used to fold the
# per-complex rows to a shared base site so they (a) match one GEM project and
# (b) align 1:1 to GEM unit names (the code "GL1Z" == GEM unit "GL1Z").
_UNIT_CODE_RE = re.compile(r"^(.*\S)\s+([A-Za-z]{1,4}\d+[A-Za-z]?)$")


def _strip_unit_code_suffix(raw):
    """Return the base site name if `raw` ends in a unit/complex code, else None.

    "Arzew GL1Z" -> "Arzew"   "Skikda GL1K" -> "Skikda"   "Senboku II" -> None
    """
    if not raw:
        return None
    m = _UNIT_CODE_RE.match(str(raw).strip())
    if not m:
        return None
    code = m.group(2)
    # Regex guarantees a digit; require a letter too (a code, not a bare number).
    if not any(c.isalpha() for c in code):
        return None
    return m.group(1).strip()


# Per-status anchor-year column to surface on the non-operating sheet. Pre-operating
# and dormancy statuses each have their own anchor; post-operating statuses fall back
# to the stop year then the actual start.
_STATUS_ANCHOR_COL = {
    "proposed": ["proposal_year"],
    "construction": ["construction_year", "proposal_year"],
    "shelved": ["shelved_year"],
    "cancelled": ["cancelled_year", "shelved_year"],
    "idled": ["stop_year", "actual_start_year"],
    "mothballed": ["stop_year", "actual_start_year"],
    "retired": ["stop_year", "actual_start_year"],
}


def _unit_anchor_year(row, ci, status):
    """Return a representative year string for a unit given its current status."""
    for col in _STATUS_ANCHOR_COL.get(status, []):
        idx = ci.get(col)
        if idx is not None and idx < len(row):
            val = (row[idx] or "").strip()
            if val:
                return val
    return ""


import string as _string

# GEM-side statuses that are NOT currently operating. GIIGNL's liq/regas tables
# are operating-only, so these never appear there — they populate the
# non-operating sheet (defaulting to "GEM has, GIIGNL doesn't").
_NONOP_STATUSES = {
    "proposed", "construction", "shelved", "cancelled",
    "idled", "mothballed", "retired",
}


def _simple_tokens(s):
    """Lowercased tokens split on whitespace / hyphen / slash, punctuation-stripped.

    Splitting on '-' and '/' lets 'arzew-bethioua' yield {'arzew','bethioua'} so a
    GIIGNL 'Arzew ...' row shares the 'arzew' token with GEM's hyphenated name.
    """
    out = set()
    for raw in re.split(r"[\s\-/]+", s or ""):
        clean = raw.strip(_string.punctuation + "()[]{}")
        if clean:
            out.add(clean)
    return out


def _tokens_4plus(s):
    """Distinctive (4+ char) tokens, for fuzzy name overlap."""
    return {t for t in _simple_tokens(s) if len(t) >= 4}


def _align_units(rp, gp):
    """Align report member rows to GEM units within an already-matched project.

    The bridge is that a GEM unit name often appears as a token inside the GIIGNL
    site name (GIIGNL 'Arzew GL1Z' ⊃ GEM unit 'GL1Z'). A GEM unit is accepted for a
    report row when its normalized name is a token-subset of the report site name
    AND (the unit name is code-like [contains a digit] OR capacities are within 25%).

    Returns (unit_matches, matched_gem_unit_names).
    """
    unit_matches = []
    used = set()
    for r in rp["rows"]:
        site_tokens = _simple_tokens(normalize_terminal_name(r.get("site_name", "")))
        try:
            rcap = float(r.get("capacity_mtpa", "")) if r.get("capacity_mtpa") else 0.0
        except ValueError:
            rcap = 0.0
        chosen = None
        for u in gp.get("units", []):
            un = u["unit_name_norm"]
            if not un or u["unit_name"] in used:
                continue
            un_tokens = _simple_tokens(un)
            if not un_tokens or not un_tokens <= site_tokens:
                continue
            has_digit = any(c.isdigit() for c in un)
            gcap = u["capacity_mtpa"]
            cap_close = bool(gcap and rcap and abs(rcap - gcap) / gcap <= 0.25)
            if has_digit or cap_close:
                chosen = u
                break
        if chosen:
            used.add(chosen["unit_name"])
            gcap = chosen["capacity_mtpa"]
            dpct = (abs(rcap - gcap) / gcap * 100) if gcap else None
            unit_matches.append({
                "report_site": r.get("site_name", ""),
                "report_capacity_mtpa": round(rcap, 2),
                "gem_unit_name": chosen["unit_name"],
                "gem_unit_status": chosen["status"],
                "gem_unit_capacity_mtpa": round(gcap, 2),
                "capacity_delta_pct": round(dpct, 1) if dpct is not None else None,
                # Agree only when capacities are identical at 2-decimal precision;
                # any non-zero difference is a conflict (red).
                "agree": bool(round(rcap - gcap, 2) == 0),
            })
    return unit_matches, {um["gem_unit_name"] for um in unit_matches}


def _load_colmap(csv_path):
    map_path = Path(csv_path).with_suffix(".colmap.json")
    if not map_path.exists():
        raise RuntimeError(f"colmap.json not found at {map_path}. Run pull_gem_db.py first.")
    return json.loads(map_path.read_text())


def _build_gem_project_table(gem_csv):
    """Collapse the unit-level GEM CSV into project-level entries.

    Returns (projects, alias_map):
      projects = {(country_norm, terminal_name_norm, section_type): project_dict}
      alias_map = {(country_norm, alias_norm, section_type): canonical_key}

    Key includes section_type so a single GEM terminal with BOTH liquefaction
    and regasification facilities (e.g. Sabine Pass, which has 6 export trains
    and 1 import terminal under the same TerminalName) becomes TWO project
    entries — one per section_type. Otherwise their capacities would sum
    incorrectly when matched against GIIGNL's section-specific tables.

    alias_map lets the matcher find a GEM project when GIIGNL uses a name
    that lives in GEM's OtherNames column rather than TerminalName. Example:
    Kribi FLNG is in GEM under TerminalName "Cameroon FLNG Terminal" with
    "Kribi FLNG Terminal" listed under OtherNames; the alias map makes the
    GIIGNL "Kribi" row match.

    project_dict fields:
      - terminal_id, terminal_name, country, section_type
      - aliases_norm: set of normalized OtherNames (used by fuzzy match too)
      - status_set, total_capacity_mtpa, operating_units, total_units
      - owners_set, fsru
    """
    colmap = _load_colmap(gem_csv)
    ci = {k: colmap.get(k) for k in [
        "terminal_id", "terminal_name", "unit_name", "country", "facility_type",
        "status", "fuel", "owner", "capacity_mtpa", "floating",
        "import_export_only", "other_names", "local_names", "language",
        "proposal_year", "construction_year", "shelved_year", "cancelled_year",
        "stop_year", "actual_start_year",
    ]}
    if None in (ci["terminal_id"], ci["terminal_name"], ci["country"]):
        sys.exit("ERROR: GEM CSV missing required columns")

    projects = {}
    alias_map: dict[tuple, tuple] = {}
    with open(gem_csv, encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) < colmap["_total_columns"]:
                continue
            fuel = row[ci["fuel"]] if ci["fuel"] is not None else "LNG"
            if fuel != "LNG":
                continue
            country = row[ci["country"]]
            tname = row[ci["terminal_name"]]
            uname = row[ci["unit_name"]] if ci["unit_name"] is not None else ""
            ftype = row[ci["facility_type"]] if ci["facility_type"] is not None else ""
            country_norm = normalize_country(country)
            tname_norm = normalize_terminal_name(tname)
            if not country_norm or not tname_norm:
                continue

            ie_only = row[ci["import_export_only"]] if ci["import_export_only"] is not None else ""
            combined = (ftype + " " + ie_only).lower()
            if "export" in combined or "liquefaction" in ftype.lower():
                section_type = "liquefaction"
            elif "import" in combined or "regasification" in ftype.lower():
                section_type = "regasification"
            else:
                section_type = "unknown"
            if section_type == "unknown":
                continue

            key = (country_norm, tname_norm, section_type)

            status = row[ci["status"]] if ci["status"] is not None else ""
            owner = row[ci["owner"]] if ci["owner"] is not None else ""
            cap_mtpa = row[ci["capacity_mtpa"]] if ci["capacity_mtpa"] is not None else ""
            floating = row[ci["floating"]] if ci["floating"] is not None else ""
            other_names_raw = row[ci["other_names"]] if ci["other_names"] is not None else ""

            try:
                cap = float(cap_mtpa) if cap_mtpa else 0.0
            except ValueError:
                cap = 0.0

            owner_tags = set()
            for part in owner.split(","):
                part = part.strip()
                if "%" in part:
                    part = part.rsplit("(", 1)[0].rsplit(" ", 1)[0].strip()
                if part:
                    owner_tags.add(normalize_entity(part))

            if key not in projects:
                projects[key] = {
                    "terminal_id": row[ci["terminal_id"]],
                    "terminal_name": tname,
                    "country": country,
                    "country_norm": country_norm,
                    "name_norm": tname_norm,
                    "section_type": section_type,
                    "unit_names": [],
                    "operating_unit_names": [],
                    "units": [],
                    "aliases_norm": set(),
                    "aliases_raw": set(),
                    "status_set": set(),
                    "total_capacity_mtpa": 0.0,
                    "operating_units": 0,
                    "total_units": 0,
                    "owners_set": set(),
                    "fsru": False,
                }
            p = projects[key]
            p["status_set"].add(status)
            if uname and uname != "--" and uname not in p["unit_names"]:
                p["unit_names"].append(uname)
            if status == "operating" and uname and uname != "--" \
                    and uname not in p["operating_unit_names"]:
                p["operating_unit_names"].append(uname)
            p["total_units"] += 1
            if status == "operating":
                p["operating_units"] += 1
                p["total_capacity_mtpa"] += cap
            p["owners_set"].update(owner_tags)
            if floating and floating.lower() in ("true", "yes", "1"):
                p["fsru"] = True

            # Per-unit detail (used by the unit-level alignment pass in _classify
            # and by the non-operating sheet). unit_name_norm is a plain lowercased
            # token form — NOT normalize_terminal_name (which strips suffixes that
            # are meaningful in unit names like "GL1Z").
            uname_norm = (uname or "").lower().strip()
            if uname_norm == "--":
                uname_norm = ""
            p["units"].append({
                "unit_name": uname if (uname and uname != "--") else "",
                "unit_name_norm": uname_norm,
                "status": status,
                "capacity_mtpa": cap,
                "start_year": _unit_anchor_year(row, ci, status),
                "owners_set": owner_tags,
            })

            local_names_raw = row[ci["local_names"]] if ci["local_names"] is not None else ""
            languages_raw = row[ci["language"]] if ci["language"] is not None else ""

            def _register_alias(alias_raw_input: str) -> None:
                """Normalize + register an alias on this project."""
                if not alias_raw_input or not alias_raw_input.strip():
                    return
                alias_norm = normalize_terminal_name(alias_raw_input)
                if not alias_norm or alias_norm == tname_norm:
                    return
                if alias_norm in p["aliases_norm"]:
                    return
                p["aliases_norm"].add(alias_norm)
                p["aliases_raw"].add(alias_raw_input.strip())
                alias_key = (country_norm, alias_norm, section_type)
                # Don't let an alias overwrite a canonical entry: if alias_key
                # is already a canonical key, leave alias_map alone (canonical wins).
                if alias_key not in projects and alias_key not in alias_map:
                    alias_map[alias_key] = key

            # OtherNames: simple comma-split, register each as alias.
            for alias_raw in (other_names_raw or "").split(","):
                _register_alias(alias_raw)

            # LocalNames: comma-split paired with Language column (1:1). Each
            # local name gets registered raw AND with English transliterations
            # (e.g. "中石油唐山曹妃甸LNG接收站" → also adds the pinyin form so
            # GIIGNL's "Caofeidian (Tangshan)" can match via shared tokens).
            # See normalize.transliterate_to_english for supported scripts.
            local_list = [n.strip() for n in (local_names_raw or "").split(",") if n.strip()]
            lang_list = [l.strip() for l in (languages_raw or "").split(",") if l.strip()]
            for i, local_name in enumerate(local_list):
                language = lang_list[i] if i < len(lang_list) else ""
                for variant in transliterate_to_english(local_name, language):
                    _register_alias(variant)

    return projects, alias_map


def _classify(report_rows, gem_projects, alias_map=None):
    """Apply matching with canonical + alias + fuzzy passes, then classify.

    Returns dict with: matches, fuzzy_matches, report_only, gem_only_operating,
                       ambiguous, stats
    """
    alias_map = alias_map or {}

    def _row_keyparts(r):
        """(country_norm, full_name_norm, section_type) for a report row, or None
        if the row is a subtotal or missing a required field."""
        if (r.get("notes") or "").lower().startswith("country subtotal"):
            return None
        country_norm = normalize_country(r.get("country", ""))
        name_norm = normalize_terminal_name(r.get("site_name", ""))
        section_type = r.get("section_type", "")
        if not country_norm or not name_norm or not section_type:
            return None
        return country_norm, name_norm, section_type

    # First scan: the set of (country, full-name, section) keys present in the
    # report. Used below to decide whether an "<X> Expansion" row has a base
    # "<X>" partner to fold into.
    rep_name_keys = set()
    for r in report_rows:
        kp = _row_keyparts(r)
        if kp:
            rep_name_keys.add(kp)

    # Second scan: count how many report rows share each unit-code-stripped base
    # (country, base_norm, section). ≥2 distinct rows sharing a base (e.g. Algeria
    # 'Arzew GL1Z'/'GL2Z'/'GL3Z' → 'arzew') is itself evidence the base is a real
    # multi-complex site, so the unit-code fold can fire even when GEM names the
    # project differently ('Arzew-Bethioua LNG Terminal').
    unit_code_base_counts = defaultdict(int)
    for r in report_rows:
        kp = _row_keyparts(r)
        if not kp:
            continue
        country_norm, _full, section_type = kp
        base_raw = _strip_unit_code_suffix(r.get("site_name", ""))
        if not base_raw:
            continue
        base_norm = normalize_terminal_name(base_raw)
        if base_norm:
            unit_code_base_counts[(country_norm, base_norm, section_type)] += 1

    def _grouping_name(country_norm, raw_site, section_type, full_norm):
        """Resolve the grouping name for a report row, returning
        (group_name_norm, folded, base_display_raw).

        Two conservative folds, each firing only when the stripped base resolves:

        1. Expansion/extension fold. GIIGNL splits a phased terminal across
           '<Site>' + '<Site> Expansion' rows (e.g. Taiwan 'Taichung' 6.1 +
           'Taichung Expansion' 1.9 = one 8.0 MTPA CPC terminal). Fold when the
           base resolves to another report row, a GEM canonical key, or alias.

        2. Unit-code fold. GIIGNL splits a multi-complex site across per-complex
           rows carrying a code suffix ('Arzew GL1Z'/'GL2Z'/'GL3Z'). Fold when the
           base resolves to a GEM key/alias OR ≥2 report rows share the base.

        Both avoid merging extraction artifacts and genuinely distinct named
        stages that lack a suffix/code ('Senboku II', 'Bontang Train E')."""
        base_raw = _strip_expansion_suffix(raw_site)
        if base_raw:
            base_norm = normalize_terminal_name(base_raw)
            if base_norm:
                base_key = (country_norm, base_norm, section_type)
                if base_key in rep_name_keys or base_key in gem_projects or base_key in alias_map:
                    return base_norm, True, base_raw

        code_base_raw = _strip_unit_code_suffix(raw_site)
        if code_base_raw:
            cb_norm = normalize_terminal_name(code_base_raw)
            if cb_norm and cb_norm != full_norm:
                cb_key = (country_norm, cb_norm, section_type)
                if (cb_key in gem_projects or cb_key in alias_map
                        or cb_key in rep_name_keys
                        or unit_code_base_counts.get(cb_key, 0) >= 2):
                    return cb_norm, True, code_base_raw

        return full_norm, False, None

    # Group report rows by (country, name, section_type) — collapse subtotal rows.
    # section_type is part of the key so a site with both liquefaction and
    # regasification rows in GIIGNL maps to two separate report-side projects,
    # mirroring the GEM-side keying.
    report_projects = {}
    for r in report_rows:
        kp = _row_keyparts(r)
        if kp is None:
            continue
        country_norm, full_norm, section_type = kp
        name_norm, folded, base_display = _grouping_name(
            country_norm, r.get("site_name", ""), section_type, full_norm)
        key = (country_norm, name_norm, section_type)

        try:
            cap = float(r.get("capacity_mtpa", "")) if r.get("capacity_mtpa") else 0.0
        except ValueError:
            cap = 0.0

        owner_tags = set()
        for ent in parse_entity_list(r.get("owner", "")):
            if ent["entity"]:
                owner_tags.add(ent["entity"])

        if key not in report_projects:
            report_projects[key] = {
                "country": r.get("country", ""),
                "country_norm": country_norm,
                "site_name": r.get("site_name", ""),
                "name_norm": name_norm,
                "section_type": section_type,
                "total_capacity_mtpa": 0.0,
                "owners_set": set(),
                "trains_count": 0,
                "rows": [],
                "site_names": set(),
            }
        rp = report_projects[key]
        # Prefer the base name as the display name (so a folded group shows
        # "Taichung" / "Arzew", not "Taichung Expansion" / "Arzew GL1Z").
        if folded and base_display:
            rp["site_name"] = base_display
        elif full_norm == name_norm and not rp.get("_display_locked"):
            rp["site_name"] = r.get("site_name", "")
        if folded and base_display:
            rp["_display_locked"] = True
        rp["site_names"].add(r.get("site_name", ""))
        rp["total_capacity_mtpa"] += cap
        rp["owners_set"].update(owner_tags)
        rp["trains_count"] += 1
        rp["rows"].append(r)

    # Pass 1: exact match — first try canonical TerminalName, then OtherNames alias.
    matches = []
    matched_gp_keys: list[tuple] = []  # every GEM project key that got matched
    aligned_unit_names_by_gp: dict[tuple, set] = defaultdict(set)
    matched_report_keys: set[tuple] = set()
    matched_gem_keys: set[tuple] = set()
    # Map each report key to the GEM canonical key it matched (if any) and
    # which side of the GEM record matched it.
    canonical_via_alias: dict[tuple, tuple] = {}  # report_key -> (canonical_key, alias_norm)

    for rp_key in list(report_projects.keys()):
        if rp_key in gem_projects:
            matched_report_keys.add(rp_key)
            matched_gem_keys.add(rp_key)
        elif rp_key in alias_map:
            canonical_key = alias_map[rp_key]
            matched_report_keys.add(rp_key)
            matched_gem_keys.add(canonical_key)
            canonical_via_alias[rp_key] = (canonical_key, rp_key[1])

    giignl_only_keys = set(report_projects.keys()) - matched_report_keys
    gem_only_keys = set(gem_projects.keys()) - matched_gem_keys

    for rp_key in sorted(matched_report_keys):
        rp = report_projects[rp_key]
        if rp_key in canonical_via_alias:
            gp_key, matched_alias_norm = canonical_via_alias[rp_key]
            gp = gem_projects[gp_key]
            via_alias = True
        else:
            gp_key = rp_key
            gp = gem_projects[gp_key]
            matched_alias_norm = ""
            via_alias = False
        key = rp_key  # variable name kept for code below that uses `key`

        # Compare capacity
        cap_delta = rp["total_capacity_mtpa"] - gp["total_capacity_mtpa"]
        cap_pct = abs(cap_delta) / gp["total_capacity_mtpa"] * 100 if gp["total_capacity_mtpa"] else None

        # Compare owners
        owner_overlap = rp["owners_set"] & gp["owners_set"]
        owner_only_report = rp["owners_set"] - gp["owners_set"]
        owner_only_gem = gp["owners_set"] - rp["owners_set"]

        # Confidence on the match — "high" for canonical name hit, "high"
        # also for alias hit (still deterministic, just via OtherNames).
        confidence = "high"
        disagreements = []
        # Any non-zero capacity difference is a conflict (compared at the
        # 2-decimal precision the diff reports). GIIGNL is one source in a
        # conflict, not authoritative — every disagreement routes to Update.
        if round(cap_delta, 2) != 0:
            pct_str = f"{cap_pct:.1f}%" if cap_pct is not None else "n/a"
            disagreements.append(f"capacity differs by {pct_str} (report={rp['total_capacity_mtpa']:.2f}, gem={gp['total_capacity_mtpa']:.2f})")
        if owner_only_report:
            disagreements.append(f"owners in report not in GEM: {sorted(owner_only_report)}")
        if owner_only_gem:
            disagreements.append(f"owners in GEM not in report: {sorted(owner_only_gem)}")

        unit_matches, aligned_names = _align_units(rp, gp)
        matched_gp_keys.append(gp_key)
        aligned_unit_names_by_gp[gp_key] |= aligned_names

        matches.append({
            "match_type": "exact_via_alias" if via_alias else "exact",
            "confidence": confidence,
            "match_granularity": "unit" if unit_matches else "project",
            "country": rp["country"],
            "site_name": rp["site_name"],
            "gem_terminal_id": gp["terminal_id"],
            "gem_terminal_name": gp["terminal_name"],
            "gem_unit_name": gp["operating_unit_names"],
            "matched_alias": matched_alias_norm if via_alias else "",
            "section_type_report": rp["section_type"],
            "section_type_gem": gp["section_type"],
            "report_capacity_mtpa": round(rp["total_capacity_mtpa"], 2),
            "gem_capacity_mtpa": round(gp["total_capacity_mtpa"], 2),
            "capacity_delta_mtpa": round(cap_delta, 2),
            "capacity_delta_pct": round(cap_pct, 1) if cap_pct is not None else None,
            "owners_overlap": sorted(owner_overlap),
            "owners_report_only": sorted(owner_only_report),
            "owners_gem_only": sorted(owner_only_gem),
            "report_train_count": rp["trains_count"],
            "report_sites_merged": sorted(rp["site_names"]) if len(rp["site_names"]) > 1 else [],
            "gem_operating_units": gp["operating_units"],
            "gem_total_units": gp["total_units"],
            "unit_matches": unit_matches,
            "disagreements": disagreements,
        })

    # Pass 2: fuzzy on remaining report-only rows
    ambiguous = []
    fuzzy_matches = []
    still_only = []
    # Sort for determinism: this loop discards from gem_only_keys as it assigns
    # fuzzy matches, so when several report rows contend for the same GEM
    # candidate (e.g. Qatar's QatarEnergy LNG train rows vs the (N)/(S) GEM
    # records) the outcome depends on iteration order. Iterating a set is not
    # stable run-to-run, which made the diff non-reproducible.
    for key in sorted(giignl_only_keys):
        rp = report_projects[key]
        country_norm = key[0]
        name_norm = key[1]
        section_type = key[2]
        # Candidates in same country AND same section_type (a GIIGNL
        # liquefaction row shouldn't fuzzy-match a GEM regasification entry).
        candidates = [
            (gk, gp) for gk, gp in gem_projects.items()
            if gk[0] == country_norm and gk[2] == section_type and gk in gem_only_keys
        ]
        # Fuzzy criteria (any of):
        #   (a) substring match — name is contained in the other (strong signal)
        #   (b) any 4+ char token shared AND owner overlap — distinct word + confirmation
        #   (c) 2+ distinctive 4+ char tokens shared — owner-free strong signal
        # Compare across BOTH canonical TerminalName AND all OtherNames + LocalNames
        # aliases (the latter includes transliterations of CJK names per normalize.py).
        # (c) catches cases where the GIIGNL owner cell is truncated or mis-parsed
        # (e.g. Caofeidian/Tangshan PetroChina where the owner line wraps onto the
        # previous row's partition); 2 distinctive shared tokens make a strong
        # enough match to surface as a candidate (even if just for ambiguous).
        fuzzy_hits = []
        rp_tokens = _tokens_4plus(name_norm)
        for gk, gp in candidates:
            all_names = {gk[1]} | gp.get("aliases_norm", set())
            substring = any((name_norm in n) or (n in name_norm) for n in all_names)
            gp_tokens: set[str] = set()
            for n in all_names:
                gp_tokens |= _tokens_4plus(n)
            shared_tokens = rp_tokens & gp_tokens
            token_overlap = bool(shared_tokens)
            owner_overlap = bool(rp["owners_set"] & gp["owners_set"])
            if substring or (token_overlap and owner_overlap) or len(shared_tokens) >= 2:
                fuzzy_hits.append((gk, gp, {
                    "substring": substring,
                    "token_overlap": token_overlap,
                    "owner_overlap": owner_overlap,
                    "shared_token_count": len(shared_tokens),
                    "shared_tokens": sorted(shared_tokens),
                    "matched_against_names": sorted(all_names),
                }))

        if len(fuzzy_hits) == 1:
            gk, gp, criteria = fuzzy_hits[0]
            unit_matches, aligned_names = _align_units(rp, gp)
            matched_gp_keys.append(gk)
            aligned_unit_names_by_gp[gk] |= aligned_names
            cap_delta = rp["total_capacity_mtpa"] - gp["total_capacity_mtpa"]
            cap_pct = abs(cap_delta) / gp["total_capacity_mtpa"] * 100 if gp["total_capacity_mtpa"] else None
            owner_only_report = rp["owners_set"] - gp["owners_set"]
            owner_only_gem = gp["owners_set"] - rp["owners_set"]
            disagreements = []
            # Any non-zero capacity difference is a conflict (see Pass 1).
            if round(cap_delta, 2) != 0:
                pct_str = f"{cap_pct:.1f}%" if cap_pct is not None else "n/a"
                disagreements.append(f"capacity differs by {pct_str} (report={rp['total_capacity_mtpa']:.2f}, gem={gp['total_capacity_mtpa']:.2f})")
            if owner_only_report:
                disagreements.append(f"owners in report not in GEM: {sorted(owner_only_report)}")
            if owner_only_gem:
                disagreements.append(f"owners in GEM not in report: {sorted(owner_only_gem)}")
            fuzzy_matches.append({
                "match_type": "fuzzy",
                "confidence": "medium",
                "match_granularity": "unit" if unit_matches else "project",
                "country": rp["country"],
                "site_name": rp["site_name"],
                "gem_terminal_id": gp["terminal_id"],
                "gem_terminal_name": gp["terminal_name"],
                "gem_unit_name": gp["operating_unit_names"],
                "matched_alias": "",
                "section_type_report": rp["section_type"],
                "section_type_gem": gp["section_type"],
                "report_capacity_mtpa": round(rp["total_capacity_mtpa"], 2),
                "gem_capacity_mtpa": round(gp["total_capacity_mtpa"], 2),
                "capacity_delta_mtpa": round(cap_delta, 2),
                "capacity_delta_pct": round(cap_pct, 1) if cap_pct is not None else None,
                "owners_overlap": sorted(rp["owners_set"] & gp["owners_set"]),
                "owners_report_only": sorted(owner_only_report),
                "owners_gem_only": sorted(owner_only_gem),
                "report_train_count": rp["trains_count"],
                "report_sites_merged": sorted(rp["site_names"]) if len(rp["site_names"]) > 1 else [],
                "gem_operating_units": gp["operating_units"],
                "gem_total_units": gp["total_units"],
                "unit_matches": unit_matches,
                "match_criteria": criteria,
                "disagreements": disagreements,
                "needs_review": True,
            })
            gem_only_keys.discard(gk)
        elif len(fuzzy_hits) > 1:
            ambiguous.append({
                "country": rp["country"],
                "site_name": rp["site_name"],
                "report_capacity_mtpa": round(rp["total_capacity_mtpa"], 2),
                "candidate_count": len(fuzzy_hits),
                "candidates": [
                    {
                        "gem_terminal_id": gp["terminal_id"],
                        "gem_terminal_name": gp["terminal_name"],
                        "gem_capacity_mtpa": round(gp["total_capacity_mtpa"], 2),
                        "criteria": criteria,
                    }
                    for gk, gp, criteria in fuzzy_hits
                ],
            })
        else:
            still_only.append({
                "type": "report_only",
                "country": rp["country"],
                "site_name": rp["site_name"],
                "section_type": rp["section_type"],
                "report_capacity_mtpa": round(rp["total_capacity_mtpa"], 2),
                "owners_in_report": sorted(rp["owners_set"]),
                "trains_count": rp["trains_count"],
                "report_sites_merged": sorted(rp["site_names"]) if len(rp["site_names"]) > 1 else [],
            })

    gem_only = []
    for key in sorted(gem_only_keys):
        gp = gem_projects[key]
        # Only flag if operating — if shelved/cancelled/proposed, "GEM-only" is
        # expected (GEM tracks pre-operating, GIIGNL doesn't)
        if "operating" not in gp["status_set"]:
            continue
        gem_only.append({
            "type": "gem_only",
            "country": gp["country"],
            "terminal_id": gp["terminal_id"],
            "terminal_name": gp["terminal_name"],
            "section_type": gp["section_type"],
            "gem_capacity_mtpa": round(gp["total_capacity_mtpa"], 2),
            "status_set": sorted(gp["status_set"]),
            "operating_units": gp["operating_units"],
            "total_units": gp["total_units"],
            "fsru": gp["fsru"],
            "owners": sorted(gp["owners_set"]),
            "note": "GEM has this as operating but the report doesn't list it; investigate whether "
                    "report missed it (small/non-member/sanctioned) OR GEM has it wrong",
        })

    # Non-operating units of MATCHED projects. GIIGNL's tables are operating-only,
    # so each defaults to is_gem_only=True ("GEM has, GIIGNL doesn't") UNLESS the
    # unit was aligned to a report row, OR the §3.2.1 narrative-prose pass annotates
    # giignl_narrative_mention downstream (a confirmed forward phase, no conflict —
    # Reconciliation SOP §5.7). Scoped to matched projects only (gem-only projects
    # live wholly in giignl_to_action).
    nonoperating_units = []
    for gk in sorted(set(matched_gp_keys)):
        gp = gem_projects[gk]
        aligned = aligned_unit_names_by_gp.get(gk, set())
        for u in gp["units"]:
            if u["status"] not in _NONOP_STATUSES:
                continue
            nonoperating_units.append({
                "country": gp["country"],
                "gem_terminal_id": gp["terminal_id"],
                "gem_terminal_name": gp["terminal_name"],
                "gem_unit_name": u["unit_name"],
                "status": u["status"],
                "capacity_mtpa": round(u["capacity_mtpa"], 2),
                "start_year": u["start_year"],
                "section_type": gp["section_type"],
                "owners": sorted(u["owners_set"]),
                "giignl_narrative_mention": "",
                "is_gem_only": u["unit_name"] not in aligned,
            })

    return {
        "matches": matches,
        "fuzzy_matches": fuzzy_matches,
        "report_only": still_only,
        "gem_only_operating": gem_only,
        "nonoperating_units": nonoperating_units,
        "ambiguous": ambiguous,
        "stats": {
            "report_project_count": len(report_projects),
            "gem_project_count": len(gem_projects),
            "exact_matches": len(matches),
            "fuzzy_matches": len(fuzzy_matches),
            "unit_level_matches": sum(1 for m in matches + fuzzy_matches
                                      if m.get("match_granularity") == "unit"),
            "report_only_unmatched": len(still_only),
            "gem_only_operating": len(gem_only),
            "nonoperating_units": len(nonoperating_units),
            "ambiguous": len(ambiguous),
            "matches_with_disagreement": sum(1 for m in matches if m["disagreements"]),
        },
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--report", choices=["giignl", "igu"], default="giignl",
                   help="Report type (only affects metadata labels)")
    p.add_argument("--extracted", required=True,
                   help="Path to extracted report CSV (from giignl_extract.py)")
    p.add_argument("--gem-csv", default=DEFAULT_GEM_CSV)
    p.add_argument("--output", default="./report_diff.json")
    args = p.parse_args()

    with open(args.extracted, encoding="utf-8") as f:
        report_rows = list(csv.DictReader(f))

    gem_projects, alias_map = _build_gem_project_table(args.gem_csv)
    diff = _classify(report_rows, gem_projects, alias_map=alias_map)
    diff["report_type"] = args.report
    diff["extracted_csv"] = args.extracted
    diff["gem_csv"] = args.gem_csv

    Path(args.output).write_text(json.dumps(diff, indent=2, default=str))

    print(f"\n  Report: {args.report.upper()}")
    print(f"  Stats:")
    for k, v in diff["stats"].items():
        print(f"    {k:35} {v}")
    print(f"\n  Saved diff to {args.output}")


if __name__ == "__main__":
    main()
