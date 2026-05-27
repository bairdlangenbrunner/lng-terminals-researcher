"""
Status timeline state machine — validation and current-status derivation.

Per lifecycle_rules.md:
  - Legal state transitions
  - Anchor year invariants
  - Current status = closest non-planned non-FID entry to bottom of timeline

Used by build_review_package.py when staging status timeline additions.

This is a guardrail, not a gate — surfaces issues to qa_review rather than
blocking. Per Update SOP §3.2, validation failures get warnings but stage anyway.

Usage as CLI (rare):
    python status_timeline.py validate-transition <current_status> <new_status>
    python status_timeline.py derive-current <timeline.json>

Library:
    from status_timeline import (
        is_legal_transition, validate_timeline_entry,
        derive_current_status, validate_anchor_invariants
    )
"""
import argparse
import json
import sys


# Per lifecycle_rules.md — legal forward transitions
LEGAL_TRANSITIONS = {
    "proposed": {"construction", "shelved", "cancelled"},
    "construction": {"operating", "shelved"},  # "construction → shelved" is rare per methodology
    "operating": {"idled", "mothballed", "retired"},
    "idled": {"operating", "mothballed", "retired"},
    "mothballed": {"operating", "retired"},
    "retired": set(),  # terminal
    "shelved": {"cancelled", "construction", "operating"},  # revival is possible
    "cancelled": {"proposed"},  # only via dead-and-revived per lifecycle_rules.md edge case
}

# Statuses excluded when deriving current status from a timeline
EXCLUDED_FROM_CURRENT = {"FID"}  # FID is a milestone, not a status


def is_legal_transition(from_status, to_status):
    """Check if from_status → to_status is a legal transition.
    
    Returns (bool, reason_if_false).
    """
    if from_status == to_status:
        return (True, "no transition")
    if from_status not in LEGAL_TRANSITIONS:
        return (False, f"unknown from_status {from_status!r}")
    if to_status not in LEGAL_TRANSITIONS:
        return (False, f"unknown to_status {to_status!r}")
    allowed = LEGAL_TRANSITIONS[from_status]
    if to_status not in allowed:
        return (False,
                f"{from_status} → {to_status} not in legal transitions. "
                f"Legal from {from_status}: {sorted(allowed) or '(terminal — no outbound)'}. "
                f"If this is a 'dead-and-revived' case (cancelled → proposed) it requires "
                f"either same-fundamentals revival on same unit OR a new unit.")
    return (True, "OK")


def validate_timeline_entry(entry, prior_timeline=None):
    """Validate a single timeline entry against the methodology rules.
    
    Args:
      entry: dict with keys status, sub_status, year, part_of_year, notes
      prior_timeline: optional list of prior entries (for context-dependent rules)
    
    Returns list of warnings (empty = valid).
    """
    warnings = []
    status = entry.get("status", "").lower()
    sub_status = entry.get("sub_status", "").lower()
    year = entry.get("year")

    # Substatus must match status family
    active_statuses = {"construction", "operating", "idled", "mothballed", "retired"}
    dormancy_statuses = {"shelved", "cancelled"}
    valid_substatuses = {
        "proposed": {"", "actual"},  # actual is rare but observed
        "construction": {"actual", "planned"},
        "operating": {"actual", "planned"},
        "idled": {"actual", "planned"},
        "mothballed": {"actual", "planned"},
        "retired": {"actual", "planned"},
        "shelved": {"confirmed", "inferred 2 y"},
        "cancelled": {"confirmed", "inferred 4 y", "actual"},  # actual is rare
        "fid": {"actual", "planned"},
    }
    expected = valid_substatuses.get(status)
    if expected is not None and sub_status not in expected:
        warnings.append(
            f"substatus {sub_status!r} not valid for status {status!r}; expected one of {sorted(expected)}"
        )

    # Year sanity
    if year:
        try:
            y = int(year)
            if y < 1960 or y > 2100:
                warnings.append(f"year {year} outside plausible range (1960-2100)")
        except (TypeError, ValueError):
            warnings.append(f"year {year!r} is not an integer")

    # Inferred shelved/cancelled require timeline support (no recent active entries)
    if sub_status in ("inferred 2 y", "inferred 4 y"):
        if prior_timeline is None:
            warnings.append("inferred status proposed without prior timeline context; "
                          "cannot verify dormancy")
        else:
            # Check that no active entries exist in the last 2 years (for inferred 2 y)
            # This is a sanity check — actual stale_sweep.py does the heavy lifting
            recent_active = [e for e in prior_timeline
                            if e.get("year") and str(e.get("status", "")).lower() in active_statuses
                            and e.get("sub_status") == "actual"]
            if recent_active:
                latest_active = max(int(e["year"]) for e in recent_active if str(e["year"]).isdigit())
                if year and int(year) - latest_active < 2:
                    warnings.append(
                        f"inferred status proposed but timeline has active entry within 2 years "
                        f"(latest active: {latest_active}); inference may be premature"
                    )

    return warnings


def derive_current_status(timeline):
    """Per methodology: current status = closest non-planned non-FID entry to bottom of timeline.
    
    Args:
      timeline: ordered list of entries (top to bottom; bottom = most recent)
    
    Returns the current status string, or empty if no derivable status.
    """
    for entry in reversed(timeline):
        status = entry.get("status", "").lower()
        sub_status = entry.get("sub_status", "").lower()
        if status in (s.lower() for s in EXCLUDED_FROM_CURRENT):
            continue
        if sub_status == "planned":
            continue
        return status
    return ""


def validate_anchor_invariants(anchor_years):
    """Check anchor year ordering invariants per lifecycle_rules.md.
    
    Args:
      anchor_years: dict with keys like proposal_year, construction_year, etc.
                    Values may be int or string-int.
    
    Returns list of warnings (empty = valid).
    """
    warnings = []

    def _y(key):
        v = anchor_years.get(key)
        if v is None or v == "":
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    py = _y("proposal_year")
    cy = _y("construction_year")
    ay = _y("actual_start_year")
    opy = _y("original_planned_start")
    lpy = _y("latest_planned_start")
    sy = _y("shelved_year")
    cancy = _y("cancelled_year")
    stopy = _y("stop_year")

    # ProposalYear ≤ ConstructionYear ≤ ActualStartYear
    if py is not None and cy is not None and py > cy:
        warnings.append(f"ProposalYear ({py}) > ConstructionYear ({cy})")
    if cy is not None and ay is not None and cy > ay:
        warnings.append(f"ConstructionYear ({cy}) > ActualStartYear ({ay})")
    if py is not None and ay is not None and py > ay:
        warnings.append(f"ProposalYear ({py}) > ActualStartYear ({ay})")

    # OriginalPlannedStartYear ≤ LatestPlannedStartYear
    if opy is not None and lpy is not None and opy > lpy:
        warnings.append(
            f"OriginalPlannedStartYear ({opy}) > LatestPlannedStartYear ({lpy}); "
            f"latest planned cannot be earlier than original"
        )

    # ActualStartYear ≤ StopYear
    if ay is not None and stopy is not None and ay > stopy:
        warnings.append(f"ActualStartYear ({ay}) > StopYear ({stopy})")

    # ShelvedYear ≤ CancelledYear
    if sy is not None and cancy is not None and sy > cancy:
        warnings.append(f"ShelvedYear ({sy}) > CancelledYear ({cancy})")

    return warnings


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)

    p_trans = sub.add_parser("validate-transition")
    p_trans.add_argument("from_status")
    p_trans.add_argument("to_status")

    p_derive = sub.add_parser("derive-current")
    p_derive.add_argument("timeline_json", help="Path to a JSON file with the timeline")

    args = p.parse_args()

    if args.command == "validate-transition":
        ok, reason = is_legal_transition(args.from_status, args.to_status)
        print(f"  {args.from_status} → {args.to_status}: {'OK' if ok else 'INVALID'}")
        print(f"  reason: {reason}")
        sys.exit(0 if ok else 1)

    if args.command == "derive-current":
        timeline = json.loads(open(args.timeline_json).read())
        current = derive_current_status(timeline)
        print(f"  Derived current status: {current or '(none)'}")
        # Also show what would be excluded
        excluded = []
        for e in reversed(timeline):
            if e.get("sub_status", "").lower() == "planned":
                excluded.append(f"  excluded (planned): {e}")
            elif e.get("status", "").lower() == "fid":
                excluded.append(f"  excluded (FID milestone): {e}")
            else:
                excluded.append(f"  → derived from: {e}")
                break
        for e in excluded:
            print(e)


if __name__ == "__main__":
    main()
