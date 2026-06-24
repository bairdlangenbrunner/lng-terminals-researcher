"""
Look up entities in the GEM entity system to avoid creating duplicates.

Per Update SOP §8 and Discovery SOP §9: the GEM entity system is shared
across all trackers. Creating a duplicate entity is real cleanup work for
the Ownership Team. Always run this before staging a new entity.

Two lookup modes:
  - Local: scan the current GEM export for the entity in existing rows
           (catches entities that already appear as Owner/Operator/Parent
           in some existing terminal)
  - Remote: query the GEM web UI entity search endpoint (catches entities
            that exist in the entity system but aren't currently linked
            to any terminal in our local data)

The remote lookup uses the same session cookies as pull_gem_db.py.

CAVEAT: The remote endpoint URL pattern is heuristic — the exact GEM entity
search URL is not documented in this codebase. The local search is reliable
and should be the primary check; remote is a useful supplement when local misses.

WHY --country DOES NOT FILTER MATCHES (lesson from a real duplicate, 2026-06-24):
GEM entities are SHARED across all trackers and across countries — the developer
of a new terminal in one country very often already appears on a project in
another. `entity_lookup.py "LNG Alliance" --country Singapore` once returned
not_found because LNG Alliance only appeared on an India terminal, and the entity
got wrongly staged as new — a duplicate. So `--country` NEVER hides a match: the
local scan ALWAYS walks every row, reports the entity as `found` if it exists
ANYWHERE, and uses --country only to ANNOTATE which matches are in-country vs.
elsewhere (with a loud cross_country_warning when the only matches are elsewhere).
Before staging any new entity, run this BARE (no --country) and with --remote.

Usage:
    python entity_lookup.py "TotalEnergies"                 # the check to trust
    python entity_lookup.py "TotalEnergies" --remote        # also query the entity system
    python entity_lookup.py "TotalEnergies" --country "France"  # annotate only, never filters
"""
import argparse
import csv
import json
import os
import subprocess
import sys
import urllib.parse
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from normalize import normalize_entity, normalize_country


DEFAULT_BASE_URL = "https://internal-project-db-host"
DEFAULT_CSV = "./gem_export.csv"
_DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _load_colmap(csv_path):
    map_path = Path(csv_path).with_suffix(".colmap.json")
    if not map_path.exists():
        raise RuntimeError(f"colmap.json not found at {map_path}")
    return json.loads(map_path.read_text())


def lookup_local(name, country=None, csv_path=DEFAULT_CSV):
    """Search the GEM CSV for the entity across Owner/Operator/Parent/Vessel* fields.

    ALWAYS scans every row regardless of `country`. The entity is reported as
    `found` if it exists ANYWHERE in the export; `country` only annotates which
    matches are in that country vs. elsewhere. This is deliberate: a `--country`
    filter that skipped other-country rows once produced a false `not_found` and a
    duplicate entity (see module docstring). `--country` must never gate a match.

    Returns dict with:
      - canonical_name: normalize_entity(name)
      - distinct_terminal_ids: deduplicated terminal IDs where this entity appears
        (across ALL countries)
      - matched_countries: normalized countries where the entity appears
      - in_filter_country / other_country_matches / cross_country_warning:
        country-annotation fields, populated only when `country` is given
      - parent_entity_ids_seen: if entity appears as Owner with a Parent ID, those IDs
    """
    canonical = normalize_entity(name)
    country_norm = normalize_country(country) if country else None

    colmap = _load_colmap(csv_path)
    fields_to_search = ["owner", "parent", "operator", "vessel_owner",
                        "vessel_parent", "vessel_operator"]
    field_indices = {f: colmap.get(f) for f in fields_to_search if colmap.get(f) is not None}

    ci_tid = colmap["terminal_id"]
    ci_country = colmap["country"]
    ci_parent_id = colmap.get("parent_entity_id")

    field_match_counts = Counter()
    terminal_matches = set()
    raw_variants = Counter()
    parent_entity_ids = set()
    matched_countries = set()           # normalized countries where the entity appears
    in_filter_tids = set()              # matches inside the --country filter
    other_country_tids = set()          # matches in any OTHER country
    other_countries = set()

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            if len(row) < colmap["_total_columns"]:
                continue
            # NB: NO country-based `continue` here — every row is always scanned.
            row_country = row[ci_country]
            row_country_norm = normalize_country(row_country)
            row_tid = row[ci_tid]

            for field, idx in field_indices.items():
                val = row[idx]
                if not val:
                    continue
                # Split on commas — owner field may be JV with multiple names
                for part in val.split(","):
                    part = part.strip()
                    if "%" in part:
                        part = part.rsplit("(", 1)[0].rsplit(" ", 1)[0].strip()
                    if normalize_entity(part) == canonical:
                        field_match_counts[field] += 1
                        raw_variants[part] += 1
                        terminal_matches.add(row_tid)
                        if row_country_norm:
                            matched_countries.add(row_country_norm)
                        # Country annotation (filter never hides — only labels).
                        if country_norm is not None:
                            if row_country_norm == country_norm:
                                in_filter_tids.add(row_tid)
                            else:
                                other_country_tids.add(row_tid)
                                if row_country:
                                    other_countries.add(row_country.strip())
                        # If this is the Owner field and there's a Parent Entity ID, capture it
                        if field == "owner" and ci_parent_id is not None:
                            pid = row[ci_parent_id].strip()
                            if pid:
                                parent_entity_ids.add(pid)

    found = bool(field_match_counts)
    out = {
        "query": name,
        "canonical_name": canonical,
        "country_filter": country,
        "country_filter_norm": country_norm,
        "field_match_counts": dict(field_match_counts),
        "raw_variants_seen": dict(raw_variants),
        "distinct_terminal_count": len(terminal_matches),
        "distinct_terminal_ids": sorted(terminal_matches),
        "matched_countries": sorted(matched_countries),
        "parent_entity_ids_seen": sorted(parent_entity_ids),
        "result": "found" if found else "not_found_in_local_data",
    }
    if country_norm is not None:
        out["in_filter_country"] = bool(in_filter_tids)
        out["other_country_matches"] = {
            "terminal_ids": sorted(other_country_tids),
            "countries": sorted(other_countries),
        }
        # The exact trap that produced a duplicate: found, but ONLY in other countries.
        if found and not in_filter_tids:
            out["cross_country_warning"] = (
                f"Entity FOUND, but only on terminals OUTSIDE --country {country!r} "
                f"(in {sorted(other_countries)}). This is an EXISTING GEM entity — "
                f"reuse its ID, do NOT stage as new. The --country filter would have "
                f"hidden this; it never does."
            )
    return out


def lookup_remote(name, base_url=DEFAULT_BASE_URL, timeout=30):
    """Query the GEM web UI entity search.
    
    CAVEAT: The exact entity search URL is not documented. This is best-effort.
    If it returns nothing, the local lookup is the more reliable check.
    """
    sid = os.environ.get("GEM_PROJECT_DB_SESSIONID")
    csrf = os.environ.get("GEM_PROJECT_DB_CSRFTOKEN")
    if not sid or not csrf:
        return {"result": "skipped_no_auth", "_warning": "Set GEM_PROJECT_DB_SESSIONID/CSRFTOKEN for remote lookup"}

    # Heuristic URL — GEM entity search is typically at /entities/?q=<name>
    url = f"{base_url}/entities/?q={urllib.parse.quote(name)}"
    tmp = "/tmp/entity_lookup.html"
    cookie = f"sessionid={sid}; csrftoken={csrf}"

    result = subprocess.run(
        ["curl", "-sL", "-A", _DEFAULT_UA,
         "-H", f"Cookie: {cookie}",
         "-o", tmp,
         "-w", "%{http_code}",
         "--max-time", str(timeout),
         url],
        capture_output=True, text=True, timeout=timeout + 5,
    )
    status = result.stdout.strip() or "000"

    if status != "200":
        return {
            "result": "remote_lookup_failed",
            "http_status": status,
            "_warning": f"Remote entity search returned {status}. URL pattern may be wrong; verify in browser."
        }

    try:
        with open(tmp, encoding="utf-8", errors="replace") as f:
            html = f.read()
    except Exception as e:
        return {"result": "remote_lookup_failed", "_warning": str(e)}

    # Heuristic: look for entity links in the response
    import re
    # Common pattern: <a href="/entities/<ID>/">Entity Name</a>
    links = re.findall(r'href="(/entities/[^"]+)"[^>]*>([^<]+)</a>', html)

    return {
        "result": "found_remote" if links else "no_remote_match",
        "candidates": [{"href": h, "name": n.strip()} for h, n in links[:20]],
        "raw_html_size": len(html),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("name", help="Entity name to look up (e.g. 'TotalEnergies')")
    p.add_argument("--country",
                   help="ANNOTATE matches by in-/out-of-country only; NEVER filters them "
                        "out (entities are shared across countries). Run BARE before staging.")
    p.add_argument("--csv", default=DEFAULT_CSV, help="GEM export CSV path")
    p.add_argument("--remote", action="store_true",
                   help="Also query the GEM entity system remotely (requires auth env vars)")
    args = p.parse_args()

    local_result = lookup_local(args.name, country=args.country, csv_path=args.csv)
    print(json.dumps(local_result, indent=2))

    if local_result["result"] == "found":
        warn = local_result.get("cross_country_warning")
        if warn:
            print(f"\n  ⚠ {warn}", file=sys.stderr)
        else:
            print(f"\n  → Entity '{args.name}' (canonical: '{local_result['canonical_name']}') "
                  f"appears in {local_result['distinct_terminal_count']} terminals "
                  f"({', '.join(local_result['matched_countries']) or 'unknown country'}). "
                  f"Reuse existing entity ID; do NOT create a new one.", file=sys.stderr)
    elif args.remote:
        print(f"\n  Local lookup found nothing; trying remote...", file=sys.stderr)
        remote_result = lookup_remote(args.name)
        print(json.dumps(remote_result, indent=2))
    else:
        print(f"\n  Local lookup found nothing. Before staging as new, RE-RUN WITH --remote "
              f"to query the entity system (and confirm you ran this BARE, without --country, "
              f"which would not have hidden a match but is the check to trust). Only then add "
              f"as a new entity (entity_additions sheet in batch xlsx).",
              file=sys.stderr)

    if args.country and local_result["result"] == "not_found_in_local_data":
        # Defensive nudge: a not_found under --country is exactly when the old bug bit.
        print(f"\n  NOTE: --country was set. This scan ignored it for matching (it can't hide "
              f"a match), so not_found here means not_found anywhere in the local export.",
              file=sys.stderr)


if __name__ == "__main__":
    main()
