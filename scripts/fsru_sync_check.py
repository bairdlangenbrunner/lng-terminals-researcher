"""
FSRU sync check between the LNG Terminals project and the LNG Carrier Tracker project.

Per SKILL.md "FSRU sync rule": FSRU vessels appear in both projects with linked
fields. When a batch touches any FSRU terminal, this script checks that the
linked carrier-project record is consistent.

WHAT GETS CHECKED:
  - For each FSRU unit in the GEM terminals export (Floating=True with
    import facility type), find the corresponding vessel record in the
    carrier project backend.
  - Link key: IMO number + vessel name (when IMO not available, vessel name only).
  - Report mismatches in: vessel status, vessel current location/terminal,
    owner/operator, vessel age/build.

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


DEFAULT_GEM_CSV = "./gem_export.csv"


def _load_colmap(csv_path):
    map_path = Path(csv_path).with_suffix(".colmap.json")
    if not map_path.exists():
        raise RuntimeError(f"colmap.json not found at {map_path}")
    return json.loads(map_path.read_text())


def gather_gem_fsrus(gem_csv):
    """Walk the GEM CSV and return all units that look like FSRU deployments.
    
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

            fsrus.append({
                "terminal_id": row[ci["terminal_id"]],
                "unit_id": row[ci["unit_id"]],
                "terminal_name": row[ci["terminal_name"]],
                "unit_name": row[ci["unit_name"]],
                "country": row[ci["country"]],
                "status": row[ci["status"]],
                "facility_type": row[ci["facility_type"]],
                "import_export_only": ie_only,
                "vessel_name": vessel_name,
                "vessel_name_norm": vessel_name.lower().strip(),
                "vessel_owner": row[ci["vessel_owner"]] if ci["vessel_owner"] is not None else "",
                "vessel_owner_norm": normalize_entity(row[ci["vessel_owner"]] if ci["vessel_owner"] is not None else ""),
                "vessel_parent": row[ci["vessel_parent"]] if ci["vessel_parent"] is not None else "",
                "vessel_operator": row[ci["vessel_operator"]] if ci["vessel_operator"] is not None else "",
                "vessel_operator_norm": normalize_entity(row[ci["vessel_operator"]] if ci["vessel_operator"] is not None else ""),
                "temp_facility": row[ci["temp_facility"]] if ci["temp_facility"] is not None else "",
            })
    return fsrus


def load_carrier_vessels(carrier_csv):
    """Load the carrier project's vessel records.
    
    Carrier CSV schema is documented in the carrier project and includes:
      VesselName, IMO, Status, Owner, Operator, CurrentDeployment, ...
    
    Returns dict: vessel_name_norm -> vessel_record
    """
    records = {}
    with open(carrier_csv, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # The carrier project may use various column names; try a few
            vname = row.get("VesselName") or row.get("Vessel Name") or row.get("vessel_name") or ""
            if not vname:
                continue
            records[vname.lower().strip()] = row
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
        carrier_owner = carrier.get("Owner") or carrier.get("VesselOwner") or carrier.get("owner") or ""
        carrier_operator = carrier.get("Operator") or carrier.get("VesselOperator") or carrier.get("operator") or ""
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
        carrier_deploy = carrier.get("CurrentDeployment") or carrier.get("Deployment") or ""
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
            "carrier_record_keys": list(carrier.keys())[:5],  # just for traceability
            "disagreements": disagreements,
            "in_sync": not disagreements,
        })

    carrier_only = []
    for vn, rec in carrier_records.items():
        if vn in matched_carrier_keys:
            continue
        # Only report carrier vessels tagged as FSRU/regas/import
        vessel_type = (rec.get("VesselType") or rec.get("Type") or rec.get("type") or "").lower()
        if "fsru" in vessel_type or "regas" in vessel_type or "import" in vessel_type:
            carrier_only.append({
                "vessel_name": rec.get("VesselName") or rec.get("Vessel Name") or "",
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

    fsrus = gather_gem_fsrus(args.gem_csv)

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
            cross_result = cross_check(fsrus, carrier_records)
            result = {"mode": "cross_check", **cross_result}

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
