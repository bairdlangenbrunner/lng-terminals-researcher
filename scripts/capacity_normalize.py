"""
Capacity conversion and range-handling for LNG terminals.

Per Unit Conventions:
  - Standard LNG units: mtpa (preferred) or bcm/y
  - 1 mtpa LNG ≈ 1.36 bcm/y natural gas
  - For ranges: record MAX in database, range in wiki Background

Used by build_review_package.py when staging capacity changes.

Usage:
    python capacity_normalize.py 5.2 mtpa          # convert to bcm/y
    python capacity_normalize.py "5.2 to 5.6 mtpa" # range parse
    python capacity_normalize.py 0.6 "MMcf/d"      # exotic unit conversion

Library:
    from capacity_normalize import to_mtpa, parse_range, normalize_for_db
"""
import argparse
import re
import sys
from pathlib import Path

# Reuse normalize.py's conversion logic
sys.path.insert(0, str(Path(__file__).parent))
from normalize import to_mtpa as _to_mtpa, to_bcm_per_y as _to_bcm


def to_mtpa(value, unit):
    """Convert (value, unit) → mtpa float, or None if unit unknown."""
    return _to_mtpa(value, unit)


def to_bcm(value, unit):
    """Convert (value, unit) → bcm/y float, or None if unit unknown."""
    return _to_bcm(value, unit)


def parse_range(s):
    """Parse a capacity range string into (min, max, unit) tuple.
    
    Examples:
        "5.2 mtpa"           -> (5.2, 5.2, "mtpa")
        "5.2 to 5.6 mtpa"    -> (5.2, 5.6, "mtpa")
        "5.2-5.6 mtpa"       -> (5.2, 5.6, "mtpa")
        "5.2–5.6 MTPA"       -> (5.2, 5.6, "mtpa")
        "around 5.2 mtpa"    -> (5.2, 5.2, "mtpa")
    
    Returns (None, None, None) if parse fails.
    """
    if not s:
        return (None, None, None)
    s = str(s).strip().lower()
    # Strip common qualifier words
    for word in ("around", "approximately", "about", "circa", "~"):
        if s.startswith(word):
            s = s[len(word):].strip()
    # Range pattern: number [separator] number unit
    m = re.match(
        r"(\d+(?:\.\d+)?)\s*[-–to]+\s*(\d+(?:\.\d+)?)\s*([a-z/]+)",
        s,
    )
    if m:
        return (float(m.group(1)), float(m.group(2)), m.group(3))
    # Single value
    m = re.match(r"(\d+(?:\.\d+)?)\s*([a-z/]+)", s)
    if m:
        v = float(m.group(1))
        return (v, v, m.group(2))
    return (None, None, None)


def normalize_for_db(value, unit):
    """Normalize a capacity for storage in the database.
    
    Returns dict with:
      - value: numeric value to store in Capacity field
      - unit: normalized unit string for CapacityUnits
      - mtpa_equivalent: convenient mtpa value (None if unit unknown)
      - bcm_equivalent: convenient bcm/y value (None if unit unknown)
      - warning: optional warning string if unit isn't standard for LNG
    """
    out = {
        "value": value,
        "unit": unit.lower() if unit else "",
        "mtpa_equivalent": to_mtpa(value, unit),
        "bcm_equivalent": to_bcm(value, unit),
        "warning": None,
    }
    norm_unit = out["unit"]
    standard_lng_units = ("mtpa", "bcm/y", "mt/y", "bcm/year")
    if norm_unit and norm_unit not in standard_lng_units:
        out["warning"] = (
            f"Non-standard LNG unit {norm_unit!r}. "
            f"Per methodology, use 'mtpa' or 'bcm/y' for LNG terminals. "
            f"If a new unit is genuinely needed, flag Rob/Baird to add it to the dropdown."
        )
    return out


def normalize_range_for_db(range_str):
    """Parse a range string and produce the DB-storable (max) plus the range note.
    
    Per methodology: "If a range of baseload/nameplate/nominal capacity values
    is found, record the range with appropriate citations on the wiki page
    Background section and the maximum value in the spreadsheet."
    
    Returns dict with:
      - db_value: max value (to store in Capacity field)
      - db_unit: unit
      - range_min, range_max: parsed range
      - wiki_note: text to add to wiki Background ("Capacity reported as X-Y unit")
    """
    lo, hi, unit = parse_range(range_str)
    if lo is None:
        return None
    out = {
        "db_value": hi,  # MAX for database per methodology
        "db_unit": unit,
        "range_min": lo,
        "range_max": hi,
        "wiki_note": None,
    }
    if lo != hi:
        out["wiki_note"] = f"Capacity reported as {lo}-{hi} {unit} range; database records max."
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("value", help="Capacity value or range string")
    p.add_argument("unit", nargs="?", default=None, help="Capacity unit (omit for range parse)")
    args = p.parse_args()

    # Try range parse first
    if args.unit is None:
        # Treat as full range string
        r = normalize_range_for_db(args.value)
        if r:
            print(f"  Range parse result:")
            for k, v in r.items():
                print(f"    {k:15} = {v}")
            return
        else:
            sys.exit(f"Could not parse {args.value!r} as a range")

    # Simple value + unit
    try:
        v = float(args.value)
    except ValueError:
        sys.exit(f"{args.value!r} is not numeric")
    result = normalize_for_db(v, args.unit)
    print(f"  Normalized capacity:")
    for k, v in result.items():
        if v is not None:
            print(f"    {k:18} = {v}")


if __name__ == "__main__":
    main()
