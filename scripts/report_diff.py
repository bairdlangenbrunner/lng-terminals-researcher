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
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from normalize import (
    normalize_country, normalize_entity, normalize_terminal_name,
    parse_entity_list, transliterate_to_english,
)


DEFAULT_GEM_CSV = "./gem_export.csv"


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
        "terminal_id", "terminal_name", "country", "facility_type",
        "status", "fuel", "owner", "capacity_mtpa", "floating",
        "import_export_only", "other_names", "local_names", "language",
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
            p["total_units"] += 1
            if status == "operating":
                p["operating_units"] += 1
                p["total_capacity_mtpa"] += cap
            p["owners_set"].update(owner_tags)
            if floating and floating.lower() in ("true", "yes", "1"):
                p["fsru"] = True

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
    # Group report rows by (country, name, section_type) — collapse subtotal rows.
    # section_type is part of the key so a site with both liquefaction and
    # regasification rows in GIIGNL maps to two separate report-side projects,
    # mirroring the GEM-side keying.
    report_projects = {}
    for r in report_rows:
        if (r.get("notes") or "").lower().startswith("country subtotal"):
            continue
        country_norm = normalize_country(r.get("country", ""))
        name_norm = normalize_terminal_name(r.get("site_name", ""))
        section_type = r.get("section_type", "")
        if not country_norm or not name_norm or not section_type:
            continue
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
            }
        rp = report_projects[key]
        rp["total_capacity_mtpa"] += cap
        rp["owners_set"].update(owner_tags)
        rp["trains_count"] += 1
        rp["rows"].append(r)

    # Pass 1: exact match — first try canonical TerminalName, then OtherNames alias.
    matches = []
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

    for rp_key in matched_report_keys:
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
        if cap_pct is not None and cap_pct > 10:
            disagreements.append(f"capacity differs by {cap_pct:.1f}% (report={rp['total_capacity_mtpa']:.2f}, gem={gp['total_capacity_mtpa']:.2f})")
        if owner_only_report:
            disagreements.append(f"owners in report not in GEM: {sorted(owner_only_report)}")
        if owner_only_gem:
            disagreements.append(f"owners in GEM not in report: {sorted(owner_only_gem)}")

        matches.append({
            "match_type": "exact_via_alias" if via_alias else "exact",
            "confidence": confidence,
            "country": rp["country"],
            "site_name": rp["site_name"],
            "gem_terminal_id": gp["terminal_id"],
            "gem_terminal_name": gp["terminal_name"],
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
            "gem_operating_units": gp["operating_units"],
            "gem_total_units": gp["total_units"],
            "disagreements": disagreements,
        })

    # Pass 2: fuzzy on remaining report-only rows
    ambiguous = []
    fuzzy_matches = []
    still_only = []
    for key in giignl_only_keys:
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
        # Token extraction: strip leading/trailing non-word chars (parens,
        # commas, periods) so "(tangshan)," tokenizes as "tangshan".
        import string as _string
        def _tokens_4plus(s: str) -> set[str]:
            out = set()
            for raw in s.split():
                clean = raw.strip(_string.punctuation + "()[]{}")
                if len(clean) >= 4:
                    out.add(clean)
            return out
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
            fuzzy_matches.append({
                "match_type": "fuzzy",
                "confidence": "medium",
                "country": rp["country"],
                "site_name": rp["site_name"],
                "gem_terminal_id": gp["terminal_id"],
                "gem_terminal_name": gp["terminal_name"],
                "section_type_report": rp["section_type"],
                "section_type_gem": gp["section_type"],
                "report_capacity_mtpa": round(rp["total_capacity_mtpa"], 2),
                "gem_capacity_mtpa": round(gp["total_capacity_mtpa"], 2),
                "owners_overlap": sorted(rp["owners_set"] & gp["owners_set"]),
                "match_criteria": criteria,
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
            })

    gem_only = []
    for key in gem_only_keys:
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

    return {
        "matches": matches,
        "fuzzy_matches": fuzzy_matches,
        "report_only": still_only,
        "gem_only_operating": gem_only,
        "ambiguous": ambiguous,
        "stats": {
            "report_project_count": len(report_projects),
            "gem_project_count": len(gem_projects),
            "exact_matches": len(matches),
            "fuzzy_matches": len(fuzzy_matches),
            "report_only_unmatched": len(still_only),
            "gem_only_operating": len(gem_only),
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
