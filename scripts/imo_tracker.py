"""
IMO lookup for FSRU / FLNG vessels.

Used when a terminal involves a named floating vessel and the IMO number is
needed (e.g. to confirm vessel identity for cross-tracker FSRU sync, or to
disambiguate vessels with similar names).

Ported from the LNG Carrier Tracker project. The carrier project established
that marinetraffic.org (note: .org, not .com) is the most reliable free
endpoint — most other sources require login or rate-limit aggressively.

CAVEATS:
  - marinetraffic.org has spotty availability and may rate-limit. Use a
    polite delay between lookups.
  - For terminals work, vessel IMO is rarely the bottleneck — most FSRU
    vessels are well-known and IMO is published in sponsor IR / trade press.
    Use this script when those primary sources fail.

Usage:
    python imo_tracker.py "BW Singapore"
    python imo_tracker.py "Höegh Gallant"
"""
import argparse
import re
import subprocess
import sys
import time
import urllib.parse


_DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _fetch(url, timeout=30):
    tmp = "/tmp/imo_lookup.html"
    result = subprocess.run(
        ["curl", "-sL", "-A", _DEFAULT_UA,
         "-o", tmp,
         "-w", "%{http_code}",
         "--max-time", str(timeout),
         url],
        capture_output=True, text=True, timeout=timeout + 5,
    )
    status = result.stdout.strip() or "000"
    try:
        with open(tmp, encoding="utf-8", errors="replace") as f:
            return status, f.read()
    except Exception:
        return status, ""


def lookup_imo(vessel_name, delay_seconds=2):
    """Look up IMO for a vessel name via marinetraffic.org.
    
    Returns dict with:
      - vessel_name: query
      - imo: extracted IMO number, or None
      - http_status: HTTP status of the search page
      - candidates: list of (name, imo) tuples seen on the search page
      - _warning: optional warning string
    """
    # Search URL pattern — marinetraffic.org accepts query strings on the homepage search
    search_url = f"https://www.marinetraffic.org/?searchphrase=all&searchword={urllib.parse.quote(vessel_name)}"
    status, html = _fetch(search_url)

    out = {
        "vessel_name": vessel_name,
        "imo": None,
        "http_status": status,
        "candidates": [],
        "_warning": None,
    }

    if status != "200":
        out["_warning"] = (
            f"marinetraffic.org returned HTTP {status}. "
            f"Site may be rate-limiting or unavailable. "
            f"Try sponsor IR, trade press, or another vessel DB (vesselfinder.com, equasis.org)."
        )
        return out

    # marinetraffic.org list pages typically render vessel results as anchor tags
    # with the IMO and vessel name in proximity. Pattern is heuristic.
    # Look for explicit IMO numbers (7 digits, often labeled "IMO")
    imo_pattern = re.compile(r"\bIMO[:\s#]*(\d{7})\b", re.IGNORECASE)
    imos_found = imo_pattern.findall(html)

    # Also try to associate IMOs with vessel names from anchor text
    # Pattern: <a href="..."><something containing vessel name></a> ... IMO 1234567
    anchor_pattern = re.compile(
        r'<a[^>]*>([^<]{3,80})</a>[^<]{0,200}?\bIMO[:\s#]*(\d{7})\b',
        re.IGNORECASE | re.DOTALL,
    )
    for m in anchor_pattern.finditer(html):
        candidate_name = m.group(1).strip()
        candidate_imo = m.group(2)
        out["candidates"].append({"name": candidate_name, "imo": candidate_imo})

    # If we have a clear-best match (substring match against vessel_name), pick it
    vn_lower = vessel_name.lower()
    best = None
    for c in out["candidates"]:
        if vn_lower in c["name"].lower() or c["name"].lower() in vn_lower:
            best = c
            break

    if best:
        out["imo"] = best["imo"]
    elif imos_found:
        # Couldn't match a candidate's name, but IMOs were on the page
        # Could be a single-result page where the name didn't render in the anchor text
        # Be conservative: report all and let the caller pick
        out["_warning"] = (
            f"Found {len(set(imos_found))} IMO(s) on page but couldn't match to vessel name. "
            f"Manual verification recommended. IMOs seen: {sorted(set(imos_found))}"
        )

    time.sleep(delay_seconds)  # polite delay
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("vessel_name", help="Vessel name to look up (e.g. 'BW Singapore')")
    p.add_argument("--delay", type=float, default=2.0, help="Delay seconds after fetch (politeness)")
    args = p.parse_args()

    result = lookup_imo(args.vessel_name, delay_seconds=args.delay)
    import json
    print(json.dumps(result, indent=2))

    if result["imo"]:
        print(f"\n  → IMO for '{args.vessel_name}': {result['imo']}", file=sys.stderr)
        sys.exit(0)
    elif result["_warning"]:
        print(f"\n  WARNING: {result['_warning']}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"\n  No IMO found for '{args.vessel_name}'.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
