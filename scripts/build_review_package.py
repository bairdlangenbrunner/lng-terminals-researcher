"""
Assemble the batch review xlsx from staged JSON inputs.

Modes:
  - update: produces sheets for updates, status_timeline_additions, entity_additions,
            stale_sweep, country_notes_contributions, qa_review, fsru_sync (if any),
            and a README
  - discovery: produces new_terminals, new_units, status_timeline_additions,
               entity_additions, monitor_list, country_notes_contributions,
               qa_review, fsru_sync (if any), and README
  - reconciliation: produces giignl_diff, giignl_to_action, qa_review, README
                    (other sheets present but empty)

Input JSON files (collected from prior script outputs OR built in-session):
  - ./staged_updates.json
  - ./staged_new_terminals.json
  - ./staged_new_units.json
  - ./staged_status_timeline.json
  - ./staged_entity_additions.json
  - ./staged_monitor_list.json
  - ./staged_country_notes.json
  - ./staged_qa_review.json
  - ./stale_sweep.json
  - ./fsru_sync.json
  - ./report_diff.json (for reconciliation mode)
  - ./prior_monitor_list.json (optional, for monitor_list roll-forward)

Color conventions per SKILL.md:
  - green:  hex EEF7EE — primary/regulatory-grade source
  - yellow: hex FFF8E1 — single non-primary source OR value implied
  - red:    hex FFE5E5 — single weak source (prefer leaving blank)
  - blue:   hex E5F0FF — re-verified, unchanged (terminals-specific)

Read-only columns (per gem_db_schema.md): NEVER written by this script.
  - Computed: CapacityinMtpa, CapacityinBcm/y, TotImport*, TotExport*, CostUSD, CostEuro, etc.
  - Out-of-scope: PCINotes, PCI3-6, LH2, NH3, SyntheticLNG, RetrofitProposed,
    AltFuelPrelimAgreement, AltFuelCallMarketInterest

Usage:
    python build_review_package.py --mode update --output ../batches/batch_<date>.xlsx
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

try:
    import openpyxl
    from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
except ImportError:
    sys.exit("ERROR: openpyxl not installed. Run: pip install --break-system-packages openpyxl")


# Colors
GREEN = PatternFill("solid", fgColor="EEF7EE")
YELLOW = PatternFill("solid", fgColor="FFF8E1")
RED = PatternFill("solid", fgColor="FFE5E5")
BLUE = PatternFill("solid", fgColor="E5F0FF")
GRAY = PatternFill("solid", fgColor="EEEEEE")  # header
NONE_FILL = PatternFill("none")

HEADER_FONT = Font(bold=True)
THIN = Side(border_style="thin", color="CCCCCC")
CELL_BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

CONFIDENCE_TO_FILL = {
    "green": GREEN,
    "yellow": YELLOW,
    "red": RED,
    "blue": BLUE,
    "": NONE_FILL,
    None: NONE_FILL,
}

# Columns NEVER written by this script (per gem_db_schema.md)
READ_ONLY_COLUMNS = {
    # Computed
    "TerminalID", "UnitID", "Wiki",
    "CapacityinMtpa", "CapacityinBcm/y",
    "TotImportLNGTerminalCapacityinMtpa", "TotImportLNGTerminalCapacityinBcm/y",
    "TotExportLNGTerminalCapacityinMtpa", "TotExportLNGTerminalCapacityinBcm/y",
    "CostUSD", "CostEuro",
    "TotKnownTerminalCostsUSD", "TotTerminalCost [ref]",
    # Out-of-scope
    "PCINotes", "PCI3", "PCI4", "PCI5", "PCI6",
    "LH2", "NH3", "SyntheticLNG", "RetrofitProposed",
    "AltFuelPrelimAgreement", "AltFuelCallMarketInterest",
}


def _safe_load(path, default=None):
    """Load JSON; return default if not found or unparseable."""
    if not Path(path).exists():
        return default
    try:
        return json.loads(Path(path).read_text())
    except json.JSONDecodeError as e:
        print(f"  WARNING: {path} is not valid JSON ({e}); treating as empty", file=sys.stderr)
        return default


def _autosize(ws, max_width=60):
    """Best-effort column auto-sizing."""
    for col_idx, col in enumerate(ws.columns, start=1):
        max_len = 0
        for cell in col:
            try:
                val = str(cell.value) if cell.value is not None else ""
                max_len = max(max_len, len(val))
            except Exception:
                pass
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max(max_len + 2, 10), max_width)


def _write_header(ws, headers, start_row=1):
    for col_idx, h in enumerate(headers, start=1):
        cell = ws.cell(row=start_row, column=col_idx, value=h)
        cell.font = HEADER_FONT
        cell.fill = GRAY
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        cell.border = CELL_BORDER
        if h in READ_ONLY_COLUMNS:
            cell.font = Font(bold=True, italic=True, color="888888")


def _write_row(ws, row_dict, headers, row_idx, confidence_map=None):
    """Write a single data row. confidence_map maps column→fill."""
    confidence_map = confidence_map or {}
    for col_idx, h in enumerate(headers, start=1):
        if h in READ_ONLY_COLUMNS:
            continue  # never write read-only columns
        value = row_dict.get(h)
        cell = ws.cell(row=row_idx, column=col_idx, value=value)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        cell.border = CELL_BORDER
        if h in confidence_map:
            cell.fill = CONFIDENCE_TO_FILL.get(confidence_map[h], NONE_FILL)


def build_readme(wb, mode, inputs_summary):
    ws = wb.create_sheet("README")
    today = date.today().isoformat()
    ws["A1"] = f"LNG Terminals batch review package — {mode} mode"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = f"Generated: {today}"
    ws["A3"] = ""
    rows = [
        ("Mode", mode),
        ("Sheets included", ", ".join(s for s in wb.sheetnames if s != "README")),
        ("", ""),
        ("Color conventions", ""),
        ("  Green", "Primary/regulatory-grade source — apply with confidence"),
        ("  Yellow", "Single non-primary source OR value implied — review before applying"),
        ("  Red", "Single weak source — consider leaving blank instead"),
        ("  Blue", "Re-verified unchanged — value reconfirmed against current source(s)"),
        ("  None", "Searched but no confirming source found"),
        ("", ""),
        ("Read-only columns", "Italicized headers — never edit; these are GEM-computed or out-of-scope"),
        ("", ""),
        ("Input summary", ""),
    ]
    for k, v in inputs_summary.items():
        rows.append((f"  {k}", v))
    for i, (k, v) in enumerate(rows, start=4):
        ws.cell(row=i, column=1, value=k)
        ws.cell(row=i, column=2, value=v)
    ws.column_dimensions["A"].width = 30
    ws.column_dimensions["B"].width = 80


def build_updates_sheet(wb, updates):
    ws = wb.create_sheet("updates")
    # Common update fields plus the cluster of [ref] partners
    headers = [
        "terminal_id", "unit_id", "terminal_name", "unit_name", "country",
        "field_name", "old_value", "new_value",
        "ref_url", "confidence", "source_tier", "source_notes",
        "scope_note", "researcher_initials",
    ]
    _write_header(ws, headers)
    for i, u in enumerate(updates, start=2):
        confidence_map = {"new_value": u.get("confidence")}
        _write_row(ws, u, headers, i, confidence_map=confidence_map)
    _autosize(ws)


def build_new_terminals_sheet(wb, new_terminals):
    ws = wb.create_sheet("new_terminals")
    # Schema-aligned columns the user would create at terminal level
    headers = [
        "TerminalName", "OtherNames", "LocalNames", "Language",
        "FacilityType", "Fuel", "Country/Area", "Region", "SubRegion",
        "State/Province", "Prefecture/District",
        "Latitude", "Longitude", "Accuracy", "Location",
        "Owner", "Parent", "ParentHQCountry", "Parent GEM Entity ID", "Operator",
        "AssociatedTerminals",
        "ProposalYear", "ProposalMonth",
        "OriginalPlannedStartYear", "LatestPlannedStartYear",
        "ConstructionYear", "ConstructionMonth",
        "ActualStartYear", "ActualStartMonth", "ActualStartYear2", "ActualStartYear3",
        "Status", "Substatus", "FIDStatus", "FIDYear",
        "ShelvedYear", "CancelledYear", "StopYear", "PlannedStopYear",
        "Capacity", "CapacityUnits", "Cost", "CostUnits", "CostYear",
        "Offshore", "Floating", "FloatingVesselName",
        "VesselOwner", "VesselParent", "VesselOperator",
        "TempFacility", "ImportExportOnly", "CaptiveGasPower",
        "PowerPlantsSupplied", "Pipelines",
        "Opposition", "ESJNotes", "Defeated",
        "CCS", "CCSNotes",
        # [ref] columns
        "FacilityType [ref]", "Owner [ref]", "Operator [ref]", "Status [ref]",
        "Capacity [ref]", "ProposalDate [ref]", "ConstructionDate [ref]",
        "StartDate [ref]", "ShelvedYear [ref]", "CancelledYear [ref]",
        "StopYear [ref]", "Location [ref]", "AssociatedTerminals [ref]",
        "PowerPlantsSupplied [ref]", "CaptiveGasPower [ref]",
        "Pipelines [ref]", "Cost [ref]", "FIDYear [ref]", "Financing [ref]",
        "FloatingVesselName [ref]", "VesselOwner [ref]", "VesselOperator [ref]",
        "Source [ref]",
        # Meta
        "ResearcherNotesProject", "ResearcherNotesUnit", "Source",
        "researcher_initials", "confidence_overall",
    ]
    _write_header(ws, headers)
    for i, t in enumerate(new_terminals, start=2):
        cm = t.get("confidence_per_field", {})
        _write_row(ws, t, headers, i, confidence_map=cm)
    _autosize(ws)


def build_new_units_sheet(wb, new_units):
    ws = wb.create_sheet("new_units")
    headers = [
        "terminal_id", "TerminalName",  # existing terminal context
        "UnitName", "UnitName Local",
        "Capacity", "CapacityUnits",
        "Status", "Substatus", "FIDStatus", "FIDYear",
        "ProposalYear", "ConstructionYear", "OriginalPlannedStartYear",
        "LatestPlannedStartYear", "ActualStartYear",
        "ShelvedYear", "CancelledYear",
        "Floating", "FloatingVesselName", "VesselOwner", "VesselOperator",
        # [ref]
        "Capacity [ref]", "ProposalDate [ref]", "ConstructionDate [ref]",
        "StartDate [ref]", "ShelvedYear [ref]", "CancelledYear [ref]",
        "FloatingVesselName [ref]", "VesselOwner [ref]", "VesselOperator [ref]",
        "Source [ref]",
        "ResearcherNotesUnit",
        "researcher_initials", "confidence_overall",
    ]
    _write_header(ws, headers)
    for i, u in enumerate(new_units, start=2):
        cm = u.get("confidence_per_field", {})
        _write_row(ws, u, headers, i, confidence_map=cm)
    _autosize(ws)


def build_status_timeline_sheet(wb, timeline_entries):
    ws = wb.create_sheet("status_timeline_additions")
    headers = [
        "terminal_id", "unit_id", "terminal_name", "unit_name",
        "operation", "status", "sub_status", "year", "part_of_year",
        "notes", "source_url", "confidence",
        "validation_warnings", "legal_transition_check",
        "researcher_initials",
    ]
    _write_header(ws, headers)
    for i, e in enumerate(timeline_entries, start=2):
        cm = {"status": e.get("confidence")}
        _write_row(ws, e, headers, i, confidence_map=cm)
    _autosize(ws)


def build_entity_additions_sheet(wb, entity_additions):
    ws = wb.create_sheet("entity_additions")
    headers = [
        "entity_name", "entity_type", "country_of_hq", "parent_entity",
        "rationale_for_new_entity", "lookup_was_run", "lookup_result_summary",
        "referenced_by_terminals", "referenced_by_units",
        "researcher_initials",
    ]
    _write_header(ws, headers)
    for i, e in enumerate(entity_additions, start=2):
        _write_row(ws, e, headers, i)
    _autosize(ws)


def build_giignl_diff_sheet(wb, diff):
    ws = wb.create_sheet("giignl_diff")
    headers = [
        "match_type", "confidence", "country", "site_name",
        "gem_terminal_id", "gem_terminal_name",
        "section_type_report", "section_type_gem",
        "report_capacity_mtpa", "gem_capacity_mtpa",
        "capacity_delta_mtpa", "capacity_delta_pct",
        "owners_overlap", "owners_report_only", "owners_gem_only",
        "report_train_count", "gem_operating_units", "gem_total_units",
        "disagreements",
    ]
    _write_header(ws, headers)
    row_idx = 2
    for m in diff.get("matches", []) + diff.get("fuzzy_matches", []):
        # Stringify list-valued fields for cell display
        row = {k: (", ".join(map(str, v)) if isinstance(v, list) else v) for k, v in m.items()}
        cm = {}
        if m.get("disagreements"):
            cm = {"disagreements": "yellow"}
        if m.get("confidence") == "medium":
            cm["confidence"] = "yellow"
        _write_row(ws, row, headers, row_idx, confidence_map=cm)
        row_idx += 1
    _autosize(ws)


def build_giignl_to_action_sheet(wb, diff):
    ws = wb.create_sheet("giignl_to_action")
    headers = [
        "action_category", "country", "site_name",
        "gem_terminal_id", "gem_terminal_name",
        "report_capacity_mtpa", "gem_capacity_mtpa",
        "section_type", "owners",
        "recommended_workflow", "notes",
    ]
    _write_header(ws, headers)
    row_idx = 2
    # GIIGNL-only → potential discovery candidates
    for r in diff.get("report_only", []):
        row = {
            "action_category": "report_only_potential_discovery",
            "country": r["country"],
            "site_name": r["site_name"],
            "gem_terminal_id": "",
            "gem_terminal_name": "",
            "report_capacity_mtpa": r.get("report_capacity_mtpa"),
            "gem_capacity_mtpa": "",
            "section_type": r["section_type"],
            "owners": ", ".join(r.get("owners_in_report", [])),
            "recommended_workflow": "Discovery (investigate; may already exist under different name)",
            "notes": "",
        }
        _write_row(ws, row, headers, row_idx, confidence_map={"action_category": "yellow"})
        row_idx += 1
    # GEM-only operating → investigate why report missed
    for r in diff.get("gem_only_operating", []):
        row = {
            "action_category": "gem_only_operating",
            "country": r["country"],
            "site_name": r["terminal_name"],
            "gem_terminal_id": r["terminal_id"],
            "gem_terminal_name": r["terminal_name"],
            "report_capacity_mtpa": "",
            "gem_capacity_mtpa": r.get("gem_capacity_mtpa"),
            "section_type": r["section_type"],
            "owners": ", ".join(r.get("owners", [])),
            "recommended_workflow": "Update (verify GEM status; may be small/non-member/sanctioned)",
            "notes": r.get("note", ""),
        }
        _write_row(ws, row, headers, row_idx, confidence_map={"action_category": "yellow"})
        row_idx += 1
    # Ambiguous
    for r in diff.get("ambiguous", []):
        row = {
            "action_category": "ambiguous_disambiguate",
            "country": r["country"],
            "site_name": r["site_name"],
            "gem_terminal_id": ", ".join(c["gem_terminal_id"] for c in r.get("candidates", [])),
            "gem_terminal_name": ", ".join(c["gem_terminal_name"] for c in r.get("candidates", [])),
            "report_capacity_mtpa": r.get("report_capacity_mtpa"),
            "gem_capacity_mtpa": ", ".join(str(c.get("gem_capacity_mtpa")) for c in r.get("candidates", [])),
            "section_type": "",
            "owners": "",
            "recommended_workflow": "Manual disambiguation needed",
            "notes": f"Has {r.get('candidate_count')} candidate matches",
        }
        _write_row(ws, row, headers, row_idx, confidence_map={"action_category": "red"})
        row_idx += 1
    # Matches with disagreement → potential updates
    for m in diff.get("matches", []):
        if not m.get("disagreements"):
            continue
        row = {
            "action_category": "matched_with_disagreement",
            "country": m["country"],
            "site_name": m["site_name"],
            "gem_terminal_id": m["gem_terminal_id"],
            "gem_terminal_name": m["gem_terminal_name"],
            "report_capacity_mtpa": m.get("report_capacity_mtpa"),
            "gem_capacity_mtpa": m.get("gem_capacity_mtpa"),
            "section_type": m.get("section_type_gem"),
            "owners": ", ".join(m.get("owners_overlap", [])),
            "recommended_workflow": "Update (investigate disagreement; do NOT auto-apply report values)",
            "notes": "; ".join(m.get("disagreements", [])),
        }
        _write_row(ws, row, headers, row_idx, confidence_map={"action_category": "yellow"})
        row_idx += 1
    _autosize(ws)


def build_fsru_sync_sheet(wb, fsru_sync):
    ws = wb.create_sheet("fsru_sync")
    if fsru_sync.get("mode") in ("skipped", "gem_only"):
        ws["A1"] = "FSRU sync check skipped"
        ws["A2"] = fsru_sync.get("_skip_reason", "")
        ws["A3"] = f"GEM-side FSRU count: {fsru_sync.get('stats', {}).get('gem_fsru_count', 0)}"
        return
    headers = [
        "gem_terminal_id", "gem_unit_id", "gem_terminal_name",
        "vessel_name", "in_sync", "disagreements", "_notes",
    ]
    _write_header(ws, headers)
    for i, m in enumerate(fsru_sync.get("matched_pairs", []), start=2):
        row = {
            "gem_terminal_id": m["gem_terminal_id"],
            "gem_unit_id": m["gem_unit_id"],
            "gem_terminal_name": m["gem_terminal_name"],
            "vessel_name": m["vessel_name"],
            "in_sync": m["in_sync"],
            "disagreements": json.dumps(m.get("disagreements", []), default=str),
            "_notes": "",
        }
        cm = {} if m["in_sync"] else {"disagreements": "yellow"}
        _write_row(ws, row, headers, i, confidence_map=cm)
    _autosize(ws)


def build_monitor_list_sheet(wb, monitor_list, prior_monitor=None):
    """Per Discovery SOP §5: monitor_list rolls forward across batches."""
    ws = wb.create_sheet("monitor_list")
    headers = [
        "country", "candidate_name", "sponsor_or_proposer",
        "first_observed_batch", "last_observed_batch",
        "current_state", "missing_threshold_elements",
        "watch_for", "best_lead_url", "notes",
    ]
    _write_header(ws, headers)
    # Merge prior monitor with new — by (country, candidate_name)
    combined = {}
    for entry in (prior_monitor or []):
        key = (entry.get("country"), entry.get("candidate_name"))
        combined[key] = entry
    for entry in monitor_list:
        key = (entry.get("country"), entry.get("candidate_name"))
        if key in combined:
            # Update existing — preserve first_observed_batch
            combined[key]["last_observed_batch"] = entry.get("last_observed_batch") or combined[key].get("last_observed_batch")
            for k, v in entry.items():
                if k not in ("first_observed_batch",) and v:
                    combined[key][k] = v
        else:
            combined[key] = entry
    for i, e in enumerate(combined.values(), start=2):
        _write_row(ws, e, headers, i)
    _autosize(ws)


def build_stale_sweep_sheet(wb, stale_data):
    ws = wb.create_sheet("stale_sweep")
    headers = [
        "terminal_id", "unit_id", "terminal_name", "unit_name", "country",
        "status", "substatus", "last_updated",
        "flag", "severity", "reason",
    ]
    _write_header(ws, headers)
    row_idx = 2
    for f in stale_data.get("flagged_units", []):
        for uf in f.get("flags", []):
            row = {
                "terminal_id": f["terminal_id"],
                "unit_id": f["unit_id"],
                "terminal_name": f["terminal_name"],
                "unit_name": f["unit_name"],
                "country": f["country"],
                "status": f["status"],
                "substatus": f["substatus"],
                "last_updated": f["last_updated"],
                "flag": uf["flag"],
                "severity": uf["severity"],
                "reason": uf["reason"],
            }
            severity_to_color = {"high": "yellow", "medium": "yellow", "low": ""}
            cm = {"flag": severity_to_color.get(uf["severity"], "")}
            _write_row(ws, row, headers, row_idx, confidence_map=cm)
            row_idx += 1
    _autosize(ws)


def build_country_notes_sheet(wb, notes):
    ws = wb.create_sheet("country_notes_contributions")
    headers = [
        "country", "topic", "contribution",
        "source_url", "researcher_initials",
    ]
    _write_header(ws, headers)
    for i, n in enumerate(notes, start=2):
        _write_row(ws, n, headers, i)
    _autosize(ws)


def build_qa_review_sheet(wb, qa_items):
    ws = wb.create_sheet("qa_review")
    headers = [
        "category", "terminal_id", "unit_id", "terminal_name",
        "issue", "severity", "suggested_action", "researcher_initials",
    ]
    _write_header(ws, headers)
    for i, q in enumerate(qa_items, start=2):
        cm = {"severity": "red" if q.get("severity") == "high" else "yellow" if q.get("severity") == "medium" else ""}
        _write_row(ws, q, headers, i, confidence_map=cm)
    _autosize(ws)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["update", "discovery", "reconciliation"], required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--inputs-dir", default=".")
    args = p.parse_args()

    inputs_dir = Path(args.inputs_dir)
    wb = openpyxl.Workbook()
    wb.remove(wb.active)  # remove default empty sheet

    # Load inputs based on mode
    inputs_summary = {}
    if args.mode == "update":
        updates = _safe_load(inputs_dir / "staged_updates.json", default=[])
        timeline = _safe_load(inputs_dir / "staged_status_timeline.json", default=[])
        entity_adds = _safe_load(inputs_dir / "staged_entity_additions.json", default=[])
        stale = _safe_load(inputs_dir / "stale_sweep.json", default={"flagged_units": []})
        country_notes = _safe_load(inputs_dir / "staged_country_notes.json", default=[])
        qa = _safe_load(inputs_dir / "staged_qa_review.json", default=[])
        fsru = _safe_load(inputs_dir / "fsru_sync.json", default={"mode": "skipped", "_skip_reason": "not run"})

        inputs_summary = {
            "updates": len(updates),
            "status_timeline_additions": len(timeline),
            "entity_additions": len(entity_adds),
            "stale_flagged_units": len(stale.get("flagged_units", [])),
            "country_notes": len(country_notes),
            "qa_review_items": len(qa),
            "fsru_sync_mode": fsru.get("mode"),
        }

        build_readme(wb, "update", inputs_summary)
        if updates:
            build_updates_sheet(wb, updates)
        if timeline:
            build_status_timeline_sheet(wb, timeline)
        if entity_adds:
            build_entity_additions_sheet(wb, entity_adds)
        if fsru.get("matched_pairs") or fsru.get("mode") == "cross_check":
            build_fsru_sync_sheet(wb, fsru)
        if stale.get("flagged_units"):
            build_stale_sweep_sheet(wb, stale)
        if country_notes:
            build_country_notes_sheet(wb, country_notes)
        if qa:
            build_qa_review_sheet(wb, qa)

    elif args.mode == "discovery":
        new_terms = _safe_load(inputs_dir / "staged_new_terminals.json", default=[])
        new_units = _safe_load(inputs_dir / "staged_new_units.json", default=[])
        timeline = _safe_load(inputs_dir / "staged_status_timeline.json", default=[])
        entity_adds = _safe_load(inputs_dir / "staged_entity_additions.json", default=[])
        monitor = _safe_load(inputs_dir / "staged_monitor_list.json", default=[])
        prior_monitor = _safe_load(inputs_dir / "prior_monitor_list.json", default=[])
        country_notes = _safe_load(inputs_dir / "staged_country_notes.json", default=[])
        qa = _safe_load(inputs_dir / "staged_qa_review.json", default=[])
        fsru = _safe_load(inputs_dir / "fsru_sync.json", default={"mode": "skipped"})

        inputs_summary = {
            "new_terminals": len(new_terms),
            "new_units": len(new_units),
            "status_timeline_additions": len(timeline),
            "entity_additions": len(entity_adds),
            "monitor_list_new": len(monitor),
            "monitor_list_prior": len(prior_monitor or []),
            "country_notes": len(country_notes),
            "qa_review_items": len(qa),
        }

        build_readme(wb, "discovery", inputs_summary)
        if new_terms:
            build_new_terminals_sheet(wb, new_terms)
        if new_units:
            build_new_units_sheet(wb, new_units)
        if timeline:
            build_status_timeline_sheet(wb, timeline)
        if entity_adds:
            build_entity_additions_sheet(wb, entity_adds)
        build_monitor_list_sheet(wb, monitor, prior_monitor=prior_monitor)
        if fsru.get("matched_pairs"):
            build_fsru_sync_sheet(wb, fsru)
        if country_notes:
            build_country_notes_sheet(wb, country_notes)
        if qa:
            build_qa_review_sheet(wb, qa)

    elif args.mode == "reconciliation":
        diff = _safe_load(inputs_dir / "report_diff.json", default={})
        qa = _safe_load(inputs_dir / "staged_qa_review.json", default=[])

        inputs_summary = {
            "report_type": diff.get("report_type", "?"),
            **diff.get("stats", {}),
            "qa_review_items": len(qa),
        }

        build_readme(wb, "reconciliation", inputs_summary)
        if diff:
            build_giignl_diff_sheet(wb, diff)
            build_giignl_to_action_sheet(wb, diff)
        if qa:
            build_qa_review_sheet(wb, qa)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    wb.save(args.output)
    print(f"\n  Wrote {args.output}")
    print(f"  Sheets: {', '.join(wb.sheetnames)}")
    print(f"  Input summary:")
    for k, v in inputs_summary.items():
        print(f"    {k:35} {v}")


if __name__ == "__main__":
    main()
