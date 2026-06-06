"""
Build dedup indexes from the GEM export CSV, and score discovery candidates
against them.

Three indexes per Discovery SOP §6 and Update SOP §11.4:
  - project_index: (country_norm, terminal_name_norm) -> [terminal_rows]
      For matching discovery candidates against existing terminals by name.
  - sponsor_country_index: (country_norm, owner_norm) -> [terminal_rows]
      For matching by sponsor when name isn't an exact hit.
  - unit_index: UnitID -> unit_row
      For mass lookups by UnitID (used by fetch_timeline.py, stale_sweep.py).

Beyond building the indexes, this module implements the SOP §6 similarity
comparison (steps 4-6) that was previously left to eyeballing: for each
sponsor/name match it computes name similarity, location distance (haversine,
when both have lat/lng), and capacity ratio, flags the cancelled/shelved +
new-announcement "dead-and-revived" case, and returns a verdict + recommended
route (discovery_new / update_existing / update_dead_and_revived /
manual_review). See `match_candidate` / `match_candidates`.

Usage:
    python dedup_index.py                    # build indexes -> work/dedup_index.json
    python dedup_index.py match cands.json   # score candidates -> work/dedup_matches.json
    # Reads ./gem_export.csv + .colmap.json

Library:
    from dedup_index import build_indexes, match_candidate
    indexes = build_indexes("./gem_export.csv")          # (proj, sponsor, unit, all_rows)
    result = match_candidate({"country": "Vietnam",
                              "name": "Cai Mep LNG",
                              "sponsor": "AES",
                              "latitude": 10.5, "longitude": 107.0,
                              "capacity_mtpa": 3.0,
                              "status": "proposed"}, indexes)

Candidate dict accepts (all optional except country + name):
    country, name (or terminal_name), sponsor (or owner),
    latitude, longitude, capacity_mtpa (or capacity + capacity_units),
    status
"""
import csv
import difflib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

# Import sibling
sys.path.insert(0, str(Path(__file__).parent))
from normalize import (
    normalize_country,
    normalize_entity,
    normalize_terminal_name,
    parse_entity_list,
    to_mtpa,
)

# --- similarity thresholds (visible + tunable; deterministic) ---------------
NAME_SIM_DUPLICATE = 0.92   # near-identical name -> duplicate outright
NAME_SIM_STRONG = 0.84      # strong name corroboration
NAME_SIM_REVIEW = 0.60      # weak name overlap -> at least worth a look
DIST_SAME_SITE_KM = 1.5     # within this, almost certainly the same physical site
DIST_NEAR_KM = 10.0         # within this, same port/complex — corroborating
DIST_SAME_AREA_KM = 50.0    # within this, location is corroborating-ish
CAP_RATIO_NEAR = 0.85       # min/max capacity ratio >= this == within ~15%
REVIVED_STATUSES = {"cancelled", "shelved"}


def _load_colmap(csv_path):
    """Load the colmap.json sibling, or raise if missing."""
    map_path = Path(csv_path).with_suffix(".colmap.json")
    if not map_path.exists():
        raise RuntimeError(
            f"colmap.json not found at {map_path}. Run pull_gem_db.py first."
        )
    return json.loads(map_path.read_text())


def _to_float(x):
    try:
        if x is None or str(x).strip() == "":
            return None
        return float(str(x).strip())
    except (TypeError, ValueError):
        return None


def build_indexes(csv_path):
    """Build all three indexes from the GEM CSV.

    Returns (project_index, sponsor_country_index, unit_index, all_rows).
    Each row_data also carries latitude/longitude/capacity_mtpa so the
    similarity comparison (match_candidate) can run off the same structures.
    """
    colmap = _load_colmap(csv_path)

    # Required column indices
    ci_tid = colmap.get("terminal_id")
    ci_uid = colmap.get("unit_id")
    ci_country = colmap.get("country")
    ci_terminal_name = colmap.get("terminal_name")
    ci_unit_name = colmap.get("unit_name")
    ci_owner = colmap.get("owner")
    ci_status = colmap.get("status")
    ci_facility_type = colmap.get("facility_type")
    ci_fuel = colmap.get("fuel")
    # Optional columns used by the similarity comparison
    ci_lat = colmap.get("latitude")
    ci_lng = colmap.get("longitude")
    ci_cap_mtpa = colmap.get("capacity_mtpa")
    ci_other_names = colmap.get("other_names")

    if None in (ci_tid, ci_uid, ci_country, ci_terminal_name, ci_owner):
        sys.exit("ERROR: required columns missing from colmap. Re-run pull_gem_db.py.")

    project_idx = defaultdict(list)
    sponsor_idx = defaultdict(list)
    unit_idx = {}
    all_rows = []

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        for row_num, row in enumerate(reader, start=2):
            if len(row) < colmap["_total_columns"]:
                # Skip malformed rows
                continue
            tid = row[ci_tid]
            uid = row[ci_uid]
            country = row[ci_country]
            tname = row[ci_terminal_name]
            uname = row[ci_unit_name]
            owner = row[ci_owner]
            status = row[ci_status] if ci_status is not None else ""
            ftype = row[ci_facility_type] if ci_facility_type is not None else ""
            fuel = row[ci_fuel] if ci_fuel is not None else ""
            lat = row[ci_lat] if ci_lat is not None else ""
            lng = row[ci_lng] if ci_lng is not None else ""
            cap_mtpa = row[ci_cap_mtpa] if ci_cap_mtpa is not None else ""
            other_names = row[ci_other_names] if ci_other_names is not None else ""

            country_norm = normalize_country(country)
            tname_norm = normalize_terminal_name(tname)

            row_data = {
                "row_num": row_num,
                "terminal_id": tid,
                "unit_id": uid,
                "country": country,
                "country_norm": country_norm,
                "terminal_name": tname,
                "terminal_name_norm": tname_norm,
                "unit_name": uname,
                "owner": owner,
                "status": status,
                "facility_type": ftype,
                "fuel": fuel,
                "other_names": other_names,
                "latitude": _to_float(lat),
                "longitude": _to_float(lng),
                "capacity_mtpa": _to_float(cap_mtpa),
            }
            all_rows.append(row_data)

            # Index by terminal name (project-level)
            if country_norm and tname_norm:
                project_idx[f"{country_norm}|{tname_norm}"].append(row_data)

            # Index by (sponsor, country) — split owner string into individual entities
            if country_norm and owner:
                # owner can be comma-separated; index each
                for part in owner.split(","):
                    part = part.strip()
                    if not part:
                        continue
                    # Strip percentage suffix if present
                    if "%" in part:
                        part = part.rsplit("(", 1)[0].rsplit(" ", 1)[0]
                    owner_norm = normalize_entity(part)
                    if owner_norm:
                        sponsor_idx[f"{country_norm}|{owner_norm}"].append(row_data)

            # Index by UnitID
            if uid:
                unit_idx[uid] = row_data

    return dict(project_idx), dict(sponsor_idx), unit_idx, all_rows


# --- similarity comparison (Discovery SOP §6 steps 4-6) --------------------

def _haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km, or None if any coord is missing."""
    if None in (lat1, lon1, lat2, lon2):
        return None
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def _name_similarity(cand_norm, gem_row):
    """Best name ratio between the candidate and a GEM row's name + OtherNames."""
    names = [gem_row.get("terminal_name_norm") or ""]
    for alt in (gem_row.get("other_names") or "").split(","):
        alt = alt.strip()
        if alt:
            names.append(normalize_terminal_name(alt))
    best = 0.0
    for n in names:
        if not n:
            continue
        best = max(best, difflib.SequenceMatcher(None, cand_norm, n).ratio())
    return best


def _terminal_aggregates(all_rows):
    """Collapse unit-rows to terminal-level aggregates for comparison."""
    aggs = {}
    for r in all_rows:
        tid = r["terminal_id"]
        a = aggs.get(tid)
        if a is None:
            a = {
                "terminal_id": tid,
                "terminal_name": r["terminal_name"],
                "terminal_name_norm": r["terminal_name_norm"],
                "other_names": r["other_names"],
                "country": r["country"],
                "country_norm": r["country_norm"],
                "owners": set(),
                "statuses": set(),
                "latitude": r["latitude"],
                "longitude": r["longitude"],
                "capacity_mtpa": 0.0,
                "_has_cap": False,
            }
            aggs[tid] = a
        if a["latitude"] is None and r["latitude"] is not None:
            a["latitude"] = r["latitude"]
        if a["longitude"] is None and r["longitude"] is not None:
            a["longitude"] = r["longitude"]
        if r["capacity_mtpa"] is not None:
            a["capacity_mtpa"] += r["capacity_mtpa"]
            a["_has_cap"] = True
        if r["status"]:
            a["statuses"].add(str(r["status"]).strip().lower())
        for owner in parse_entity_list(r["owner"] or ""):
            on = normalize_entity(owner)
            if on:
                a["owners"].add(on)
    return aggs


# Cache aggregates per all_rows object so scoring many candidates is cheap.
_AGG_CACHE = {}


def _get_aggregates(all_rows):
    key = id(all_rows)
    cached = _AGG_CACHE.get(key)
    if cached is None or cached[0] is not len(all_rows):
        agg = _terminal_aggregates(all_rows)
        _AGG_CACHE[key] = (len(all_rows), agg)
        return agg
    return cached[1]


def _candidate_capacity_mtpa(candidate):
    cap = _to_float(candidate.get("capacity_mtpa"))
    if cap is not None:
        return cap
    raw = _to_float(candidate.get("capacity"))
    if raw is None:
        return None
    try:
        return to_mtpa(raw, candidate.get("capacity_units") or "mtpa")
    except Exception:
        return None


def _score_pair(candidate, cand_name_norm, cand_owner_norms, cand_lat, cand_lng,
                cand_cap, agg):
    """Score one candidate against one GEM terminal aggregate.

    Returns a dict of signals + a 0-1 composite score, or None if there's no
    plausible relationship at all.
    """
    name_sim = _name_similarity(cand_name_norm, agg)
    dist = _haversine_km(cand_lat, cand_lng, agg["latitude"], agg["longitude"])

    cap_ratio = None
    if cand_cap and agg["_has_cap"] and agg["capacity_mtpa"]:
        hi = max(cand_cap, agg["capacity_mtpa"])
        lo = min(cand_cap, agg["capacity_mtpa"])
        cap_ratio = (lo / hi) if hi else None

    sponsor_overlap = bool(cand_owner_norms & agg["owners"])

    # Composite (deterministic weighted blend of the signals that are present).
    name_component = name_sim  # always available
    loc_component = None
    if dist is not None:
        loc_component = 1.0 if dist <= DIST_NEAR_KM else max(0.0, 1.0 - (dist / DIST_SAME_AREA_KM))
    cap_component = cap_ratio  # None if not comparable

    weights = {"name": 0.5, "loc": 0.3, "cap": 0.2}
    num = weights["name"] * name_component
    den = weights["name"]
    if loc_component is not None:
        num += weights["loc"] * loc_component
        den += weights["loc"]
    if cap_component is not None:
        num += weights["cap"] * cap_component
        den += weights["cap"]
    score = num / den if den else 0.0
    # Sponsor agreement is a corroborator, not a primary axis — small bonus.
    if sponsor_overlap:
        score = min(1.0, score + 0.05)

    # Is there anything worth reporting?
    if name_sim < NAME_SIM_REVIEW and not sponsor_overlap and not (dist is not None and dist <= DIST_NEAR_KM):
        return None

    return {
        "terminal_id": agg["terminal_id"],
        "terminal_name": agg["terminal_name"],
        "gem_status": sorted(agg["statuses"]),
        "name_similarity": round(name_sim, 3),
        "distance_km": round(dist, 2) if dist is not None else None,
        "capacity_ratio": round(cap_ratio, 3) if cap_ratio is not None else None,
        "sponsor_overlap": sponsor_overlap,
        "score": round(score, 3),
    }


def _verdict_for(match, candidate):
    """Map a best-match signal bundle to a verdict + recommended route."""
    name_sim = match["name_similarity"]
    dist = match["distance_km"]
    cap = match["capacity_ratio"]
    very_near = dist is not None and dist <= DIST_SAME_SITE_KM
    near = dist is not None and dist <= DIST_NEAR_KM
    cap_near = cap is not None and cap >= CAP_RATIO_NEAR
    sponsor = match["sponsor_overlap"]

    revived = bool(set(match["gem_status"]) & REVIVED_STATUSES)
    cand_status = (candidate.get("status") or "proposed").strip().lower()
    is_new_proposal = cand_status in ("", "proposed", "construction")

    if name_sim >= NAME_SIM_DUPLICATE or (very_near and (name_sim >= NAME_SIM_STRONG or cap_near)):
        verdict = "duplicate"
    elif (name_sim >= NAME_SIM_STRONG
          # same physical site is strong when ANY other signal agrees — including
          # a revived GEM record + a fresh proposal (dead-and-revived projects are
          # routinely renamed, so name similarity is low by design)
          or (very_near and (revived or sponsor or cap_near or name_sim >= NAME_SIM_REVIEW))
          or (sponsor and near and cap_near)
          or (near and cap_near and name_sim >= NAME_SIM_REVIEW)):
        verdict = "likely_duplicate"
    elif (sponsor and name_sim >= NAME_SIM_REVIEW) or near or name_sim >= NAME_SIM_REVIEW:
        verdict = "review"
    else:
        verdict = "new"

    if verdict in ("duplicate", "likely_duplicate"):
        if revived and is_new_proposal:
            route = "update_dead_and_revived"
        else:
            route = "update_existing"
    elif verdict == "review":
        route = "manual_review"
    else:
        route = "discovery_new"
    return verdict, route, revived


def match_candidate(candidate, indexes, top_n=5):
    """Score one discovery candidate against the GEM indexes (SOP §6 steps 4-6).

    `indexes` is the tuple from build_indexes(). Returns a dict with the
    candidate echo, a verdict, a recommended route, and the ranked matches.
    """
    project_idx, sponsor_idx, unit_idx, all_rows = indexes
    aggs = _get_aggregates(all_rows)

    cand_country_norm = normalize_country(candidate.get("country") or "")
    cand_name = candidate.get("name") or candidate.get("terminal_name") or ""
    cand_name_norm = normalize_terminal_name(cand_name)
    cand_sponsor_raw = candidate.get("sponsor") or candidate.get("owner") or ""
    cand_owner_norms = {normalize_entity(p) for p in parse_entity_list(cand_sponsor_raw)}
    cand_owner_norms.discard("")
    cand_lat = _to_float(candidate.get("latitude"))
    cand_lng = _to_float(candidate.get("longitude"))
    cand_cap = _candidate_capacity_mtpa(candidate)

    # Candidate set of GEM terminals to score: same-country only (country is the
    # one field every dedup/index tool keys off).
    candidate_tids = set()
    for agg in aggs.values():
        if cand_country_norm and agg["country_norm"] == cand_country_norm:
            candidate_tids.add(agg["terminal_id"])

    matches = []
    for tid in candidate_tids:
        scored = _score_pair(
            candidate, cand_name_norm, cand_owner_norms, cand_lat, cand_lng,
            cand_cap, aggs[tid],
        )
        if scored:
            matches.append(scored)

    # Deterministic order: score desc, then terminal_id for stable ties.
    matches.sort(key=lambda m: (-m["score"], str(m["terminal_id"])))

    if matches:
        verdict, route, revived = _verdict_for(matches[0], candidate)
    else:
        verdict, route, revived = "new", "discovery_new", False

    return {
        "candidate": {
            "country": candidate.get("country"),
            "name": cand_name,
            "sponsor": cand_sponsor_raw,
            "capacity_mtpa": cand_cap,
            "status": candidate.get("status"),
        },
        "verdict": verdict,
        "recommended_route": route,
        "dead_and_revived": revived,
        "matches": matches[:top_n],
    }


def match_candidates(candidates, indexes, top_n=5):
    return [match_candidate(c, indexes, top_n=top_n) for c in candidates]


def main():
    args = sys.argv[1:]
    csv_path = "./gem_export.csv"
    if not Path(csv_path).exists():
        sys.exit(f"ERROR: {csv_path} not found. Run pull_gem_db.py first.")

    # --- match mode: score discovery candidates against the indexes ---
    if args and args[0] == "match":
        if len(args) < 2:
            sys.exit("Usage: python dedup_index.py match <candidates.json>")
        cand_path = Path(args[1])
        if not cand_path.exists():
            sys.exit(f"ERROR: candidates file not found: {cand_path}")
        candidates = json.loads(cand_path.read_text(encoding="utf-8"))
        if isinstance(candidates, dict):
            candidates = candidates.get("candidates", [])
        indexes = build_indexes(csv_path)
        results = match_candidates(candidates, indexes)
        tally = defaultdict(int)
        for r in results:
            tally[r["recommended_route"]] += 1
        print(f"  Scored {len(results)} candidate(s) against GEM:")
        for route in sorted(tally):
            print(f"    {route}: {tally[route]}")
        for r in results:
            best = r["matches"][0] if r["matches"] else None
            line = f"    [{r['recommended_route']}] {r['candidate']['country']}: {r['candidate']['name']}"
            if best:
                line += (f"  ~ {best['terminal_name']} (score {best['score']}"
                         f", name {best['name_similarity']}"
                         + (f", {best['distance_km']}km" if best['distance_km'] is not None else "")
                         + (", revived" if r["dead_and_revived"] else "") + ")")
            print(line)
        out_path = Path("work/dedup_matches.json")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str))
        print(f"\n  Saved to {out_path}")
        return

    # --- default: build indexes (backward compatible) ---
    project_idx, sponsor_idx, unit_idx, all_rows = build_indexes(csv_path)

    print(f"  Total unit-rows: {len(all_rows)}")
    print(f"  Unique terminals: {len(set(r['terminal_id'] for r in all_rows))}")
    print(f"  Project index keys (country|name): {len(project_idx)}")
    print(f"  Sponsor index keys (country|owner): {len(sponsor_idx)}")
    print(f"  Unit index entries: {len(unit_idx)}")

    # Sanity: project-key collisions (>1 row = multi-unit project, expected)
    multi_unit = {k: v for k, v in project_idx.items() if len(v) > 1}
    print(f"\n  Multi-unit projects (project_idx keys with >1 row): {len(multi_unit)}")

    # Sanity: sponsors with many projects
    top_sponsors = sorted(sponsor_idx.items(), key=lambda x: -len(x[1]))[:10]
    print(f"\n  Top 10 (country|sponsor) by unit-row count:")
    for k, v in top_sponsors:
        print(f"    {k}: {len(v)} rows")

    out = {
        "project_index": project_idx,
        "sponsor_country_index": sponsor_idx,
        # unit_idx is not serialized — it's used in-memory only
        "stats": {
            "total_rows": len(all_rows),
            "unique_terminals": len(set(r["terminal_id"] for r in all_rows)),
            "project_keys": len(project_idx),
            "sponsor_keys": len(sponsor_idx),
            "unit_keys": len(unit_idx),
            "multi_unit_projects": len(multi_unit),
        },
    }
    out_path = Path("work/dedup_index.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2, default=str))
    print(f"\n  Saved to {out_path}")


if __name__ == "__main__":
    main()
