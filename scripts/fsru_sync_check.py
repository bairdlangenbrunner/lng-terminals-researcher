"""
FSRU sync check between the LNG Terminals project and the LNG Carrier Tracker project.

Per SKILL.md "FSRU sync rule": FSRU vessels appear in both projects with linked
fields. When a batch touches any FSRU terminal, this script checks that the
linked carrier-project record is consistent.

WHAT GETS CHECKED:
  - For each FSRU unit in the GEM terminals export (Floating=True with
    import facility type), find the corresponding vessel record in the
    carrier project backend. An FSRU is an IMPORT unit: the export's Floating
    flag is set on FLNG export units too, so facility_type is filtered.
  - Link key: vessel name (the GEM export carries no vessel IMO column).
  - Report mismatches in: owner/operator and deployment terminal.

GRACEFUL DEGRADATION:
  - If the carrier project backend is not accessible (no path provided OR
    path not found), the script short-circuits to a "skipped" result with a
    clear reason. This lets every batch run unconditionally without breaking
    when the carrier backend isn't in the same workspace.

Usage:
    python fsru_sync_check.py \\
        --carrier-export /path/to/carrier/vessels.csv \\
        --output ./fsru_sync.json
    
    # Or skip the carrier side and just enumerate the GEM-side FSRUs:
    python fsru_sync_check.py --gem-only --output ./fsru_sync.json
"""
import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from normalize import normalize_entity
from colmap import load_colmap as _load_colmap


DEFAULT_GEM_CSV = "./gem_export.csv"

# An FSRU is an import unit. The GEM export sets Floating=True on FLNG export
# units as well (95 of the 350 floating LNG units in the 2026-09 export), so
# without this filter the "FSRU fleet" handed to the carrier side is more than
# a quarter export vessels.
IMPORT_FACILITY_TYPES = ("import",)

# Headers the carrier project's backend has used for the fields compared here.
# First in each tuple is the live backend (lng-carriers-researcher
# work/backend.csv); the rest are older/alternative spellings. Reading only the
# later spellings is how this check came to pass silently on zero records.
CARRIER_NAME_HEADERS = ("Name", "VesselName", "Vessel Name", "vessel_name")
CARRIER_IMO_HEADERS = ("IMO number", "IMO", "imo")
CARRIER_OWNER_HEADERS = ("Shipowner", "Owner", "VesselOwner", "owner")
CARRIER_OPERATOR_HEADERS = ("Operator/charterer", "Operator", "VesselOperator",
                            "operator")
CARRIER_TYPE_HEADERS = ("Vessel type", "VesselType", "Type", "type")
# No deployment column in the carrier backend today; kept so the comparison
# lights up by itself if one is added.
CARRIER_DEPLOYMENT_HEADERS = ("CurrentDeployment", "Deployment")

# The carrier backend's header is not the first line -- the sheet carries a
# spreadsheet-column preamble row above it. Scan this far down for it.
CARRIER_HEADER_SCAN_ROWS = 20


def _first(record, headers):
    """First non-empty value in `record` under any of `headers`."""
    for h in headers:
        v = record.get(h)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def gather_gem_fsrus(gem_csv, facility_types=IMPORT_FACILITY_TYPES, excluded=None):
    """Walk the GEM CSV and return the units that are FSRU deployments.

    Floating=True is not enough on its own: the flag is set on FLNG export
    units too, and those are not FSRUs and have no carrier-side counterpart to
    reconcile. `facility_types` is the whitelist applied to facility_type
    (None keeps every floating unit); floating units it rejects are appended to
    `excluded` when a list is passed, so the drop is countable rather than
    invisible.

    Returns list of dicts with vessel-relevant fields.
    """
    colmap = _load_colmap(gem_csv)
    ci = {k: colmap.get(k) for k in [
        "terminal_id", "unit_id", "terminal_name", "unit_name",
        "country", "status", "facility_type", "fuel",
        "floating", "floating_vessel_name", "vessel_owner",
        "vessel_parent", "vessel_operator", "import_export_only",
        "temp_facility",
    ]}
    keep = tuple(t.lower() for t in facility_types) if facility_types else None

    fsrus = []
    with open(gem_csv, encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) < colmap["_total_columns"]:
                continue
            fuel = row[ci["fuel"]] if ci["fuel"] is not None else "LNG"
            if fuel != "LNG":
                continue
            floating = row[ci["floating"]] if ci["floating"] is not None else ""
            if not floating or floating.lower() not in ("true", "yes", "1"):
                continue
            vessel_name = row[ci["floating_vessel_name"]] if ci["floating_vessel_name"] is not None else ""
            ie_only = row[ci["import_export_only"]] if ci["import_export_only"] is not None else ""
            ftype = row[ci["facility_type"]] if ci["facility_type"] is not None else ""

            unit = {
                "terminal_id": row[ci["terminal_id"]],
                "unit_id": row[ci["unit_id"]],
                "terminal_name": row[ci["terminal_name"]],
                "unit_name": row[ci["unit_name"]],
                "country": row[ci["country"]],
                "status": row[ci["status"]],
                "facility_type": ftype,
                "import_export_only": ie_only,
                "vessel_name": vessel_name,
                "vessel_name_norm": vessel_name.lower().strip(),
                "vessel_owner": row[ci["vessel_owner"]] if ci["vessel_owner"] is not None else "",
                "vessel_owner_norm": normalize_entity(row[ci["vessel_owner"]] if ci["vessel_owner"] is not None else ""),
                "vessel_parent": row[ci["vessel_parent"]] if ci["vessel_parent"] is not None else "",
                "vessel_operator": row[ci["vessel_operator"]] if ci["vessel_operator"] is not None else "",
                "vessel_operator_norm": normalize_entity(row[ci["vessel_operator"]] if ci["vessel_operator"] is not None else ""),
                "temp_facility": row[ci["temp_facility"]] if ci["temp_facility"] is not None else "",
            }

            if keep is not None and ftype.strip().lower() not in keep:
                if excluded is not None:
                    excluded.append(unit)
                continue
            fsrus.append(unit)
    return fsrus


def load_carrier_vessels(carrier_csv):
    """Load the carrier project's vessel records, keyed by normalized name.

    Two things about the real file (lng-carriers-researcher work/backend.csv)
    that a plain DictReader gets wrong, and both fail silently -- an empty
    result reads as "nothing to reconcile" rather than as a broken read:
      - the header is NOT the first line. The sheet's first row is a
        spreadsheet-column preamble ("1","2","3",...), which DictReader would
        take as the field names.
      - the vessel-name column is `Name`, not `VesselName`.

    So: locate the header row by looking for a recognized name column, and read
    from there. No such row in the first CARRIER_HEADER_SCAN_ROWS raises -- an
    unreadable carrier export has to be loud, not an empty dict.

    Returns dict: vessel_name_norm -> vessel_record (the raw row, by header).
    """
    with open(carrier_csv, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))

    header_idx = None
    for i, row in enumerate(rows[:CARRIER_HEADER_SCAN_ROWS]):
        if any(c.strip() in CARRIER_NAME_HEADERS for c in row):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError(
            f"{carrier_csv}: no vessel-name column found in the first "
            f"{CARRIER_HEADER_SCAN_ROWS} rows (looked for "
            f"{', '.join(CARRIER_NAME_HEADERS)}). Is this the carrier backend CSV?"
        )

    header = [c.strip() for c in rows[header_idx]]
    records = {}
    for row in rows[header_idx + 1:]:
        rec = {h: (row[i] if i < len(row) else "")
               for i, h in enumerate(header) if h}
        vname = _first(rec, CARRIER_NAME_HEADERS)
        if not vname:
            continue
        records[vname.lower().strip()] = rec
    return records


def cross_check(fsrus, carrier_records):
    """Compare GEM FSRU data against carrier vessel records.
    
    Returns dict with:
      - matched: list of matched pairs with any disagreements flagged
      - gem_only: FSRUs in GEM with no corresponding carrier record
      - carrier_only: vessels in carrier with no matching GEM unit
        (only reported for carriers tagged as FSRU/regas vessels)
    """
    matched = []
    gem_only = []
    matched_carrier_keys = set()

    for fsru in fsrus:
        vn = fsru["vessel_name_norm"]
        if not vn:
            gem_only.append({**fsru, "_reason": "no vessel name in GEM record"})
            continue

        carrier = carrier_records.get(vn)
        if carrier is None:
            # Try substring match
            substring_hits = [
                (k, v) for k, v in carrier_records.items()
                if vn in k or k in vn
            ]
            if len(substring_hits) == 1:
                carrier = substring_hits[0][1]
                matched_carrier_keys.add(substring_hits[0][0])
            elif len(substring_hits) > 1:
                gem_only.append({**fsru, "_reason": f"ambiguous vessel name; multiple carrier matches: {[k for k, v in substring_hits]}"})
                continue
            else:
                gem_only.append({**fsru, "_reason": f"vessel '{fsru['vessel_name']}' not in carrier records"})
                continue
        else:
            matched_carrier_keys.add(vn)

        # Compare owner / operator
        disagreements = []
        carrier_owner = _first(carrier, CARRIER_OWNER_HEADERS)
        carrier_operator = _first(carrier, CARRIER_OPERATOR_HEADERS)
        carrier_owner_norm = normalize_entity(carrier_owner)
        carrier_operator_norm = normalize_entity(carrier_operator)

        if (fsru["vessel_owner_norm"] and carrier_owner_norm
                and fsru["vessel_owner_norm"] != carrier_owner_norm):
            disagreements.append({
                "field": "owner",
                "gem_value": fsru["vessel_owner"],
                "carrier_value": carrier_owner,
                "gem_canonical": fsru["vessel_owner_norm"],
                "carrier_canonical": carrier_owner_norm,
            })
        if (fsru["vessel_operator_norm"] and carrier_operator_norm
                and fsru["vessel_operator_norm"] != carrier_operator_norm):
            disagreements.append({
                "field": "operator",
                "gem_value": fsru["vessel_operator"],
                "carrier_value": carrier_operator,
                "gem_canonical": fsru["vessel_operator_norm"],
                "carrier_canonical": carrier_operator_norm,
            })

        # Compare status / deployment
        carrier_deploy = _first(carrier, CARRIER_DEPLOYMENT_HEADERS)
        # The carrier deployment field should reference the same terminal
        if carrier_deploy and fsru["terminal_name"]:
            if (fsru["terminal_name"].lower() not in carrier_deploy.lower()
                    and carrier_deploy.lower() not in fsru["terminal_name"].lower()):
                disagreements.append({
                    "field": "deployment",
                    "gem_terminal": fsru["terminal_name"],
                    "carrier_deployment": carrier_deploy,
                    "_note": "Carrier record references different deployment than GEM terminal",
                })

        matched.append({
            "gem_terminal_id": fsru["terminal_id"],
            "gem_unit_id": fsru["unit_id"],
            "gem_terminal_name": fsru["terminal_name"],
            "gem_status": fsru["status"],
            "vessel_name": fsru["vessel_name"],
            "carrier_imo": _first(carrier, CARRIER_IMO_HEADERS),
            "carrier_record_keys": list(carrier.keys())[:5],  # just for traceability
            "disagreements": disagreements,
            "in_sync": not disagreements,
        })

    carrier_only = []
    for vn, rec in carrier_records.items():
        if vn in matched_carrier_keys:
            continue
        # Only report carrier vessels tagged as FSRU/regas/import
        vessel_type = _first(rec, CARRIER_TYPE_HEADERS).lower()
        if "fsru" in vessel_type or "regas" in vessel_type or "import" in vessel_type:
            carrier_only.append({
                "vessel_name": _first(rec, CARRIER_NAME_HEADERS),
                "vessel_type": vessel_type,
                "carrier_record_excerpt": {k: rec[k] for k in list(rec.keys())[:8]},
                "_note": "Vessel tagged FSRU/regas in carrier project but has no matching GEM terminal unit",
            })

    return {
        "matched_pairs": matched,
        "gem_only_fsrus": gem_only,
        "carrier_only_fsrus": carrier_only,
        "stats": {
            "gem_fsru_count": len(fsrus),
            "carrier_record_count": len(carrier_records),
            "matched_pair_count": len(matched),
            "matched_with_disagreement": sum(1 for m in matched if not m["in_sync"]),
            "gem_only_count": len(gem_only),
            "carrier_only_count": len(carrier_only),
        },
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--gem-csv", default=DEFAULT_GEM_CSV)
    p.add_argument("--carrier-export",
                   help="Path to carrier project vessels CSV. If omitted, runs in --gem-only mode.")
    p.add_argument("--gem-only", action="store_true",
                   help="Enumerate GEM-side FSRUs only; skip carrier cross-check")
    p.add_argument("--output", default="./fsru_sync.json")
    args = p.parse_args()

    excluded = []
    fsrus = gather_gem_fsrus(args.gem_csv, excluded=excluded)

    if args.gem_only or not args.carrier_export:
        result = {
            "mode": "gem_only",
            "_skip_reason": (
                "carrier_export not provided OR --gem-only flag set; "
                "cross-check skipped. To enable sync check, supply the carrier "
                "project's vessels CSV with --carrier-export."
            ),
            "gem_fsrus": fsrus,
            "stats": {"gem_fsru_count": len(fsrus)},
        }
    else:
        if not Path(args.carrier_export).exists():
            result = {
                "mode": "skipped",
                "_skip_reason": f"carrier_export path not found: {args.carrier_export}",
                "gem_fsrus": fsrus,
                "stats": {"gem_fsru_count": len(fsrus)},
            }
        else:
            carrier_records = load_carrier_vessels(args.carrier_export)
            if not carrier_records:
                # Readable, and empty. Say so -- a zero-record cross-check
                # "passes" without having compared anything.
                result = {
                    "mode": "skipped",
                    "_skip_reason": (
                        f"carrier_export has a vessel-name column but no vessel "
                        f"rows: {args.carrier_export}"
                    ),
                    "gem_fsrus": fsrus,
                    "stats": {"gem_fsru_count": len(fsrus)},
                }
            else:
                cross_result = cross_check(fsrus, carrier_records)
                result = {"mode": "cross_check", **cross_result}

    result.setdefault("stats", {})["gem_non_import_floating_excluded"] = len(excluded)

    Path(args.output).write_text(json.dumps(result, indent=2, default=str))

    print(f"  Mode: {result.get('mode')}")
    print(f"  Stats:")
    for k, v in result.get("stats", {}).items():
        print(f"    {k:35} {v}")
    if result.get("_skip_reason"):
        print(f"\n  Note: {result['_skip_reason']}")
    print(f"\n  Wrote {args.output}")


if __name__ == "__main__":
    main()
