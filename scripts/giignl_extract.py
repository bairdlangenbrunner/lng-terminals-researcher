"""
Extract liquefaction and regasification tables from the GIIGNL Annual Report.

The 2026 edition shipped as a real PDF (v1.7) with a clean text layer, so we
parse it directly via `pdftotext -layout` rather than rendering pages to JPEG
and using a vision model. (Earlier editions shipped as a zip-of-JPEGs+OCR;
that pipeline is in git history if a future edition needs it back.)

Output is a flat CSV consumed by `report_diff.py` — column shape:
  section_type, report_page, country, site_name, type,
  owner, capacity_mtpa, capacity_bcm, start_year, trains, vessel_name, notes

`site_name` is stripped of train suffixes (T1, T2, T1-6, etc.) so multiple
GIIGNL train-rows roll up to one project-level entry, matching GEM's
TerminalName granularity per Reconciliation SOP §3.5. Per-row capacities
sum across the project via report_diff.py's existing aggregation.

Usage:
    python scripts/giignl_extract.py \\
        /Users/baird/Downloads/GIIGNL-2026-Annual-Report-0526b.pdf \\
        --output giignl_extracted.csv

The script auto-detects liquefaction and regasification table page ranges
by scanning for section-marker text at the top of each page.
"""
from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


# Sanity totals (printed in GIIGNL Executive Summary) used as ±2% gate.
# These get updated by edition; values below are for the 2026 edition.
EXPECTED_TOTALS = {
    2026: {"liquefaction": 524.0, "regasification": 1247.0},
}

# Page-top markers that identify a table page. Both phrases appear in the
# header band of every table page in the 2026 edition.
LIQ_PAGE_MARKER = "Liquefaction plants"
REGAS_PAGE_MARKER = "Regasification terminals"

# Output schema (must match what report_diff.py reads via csv.DictReader)
OUTPUT_COLUMNS = [
    "section_type", "report_page", "country", "site_name", "type",
    "owner", "capacity_mtpa", "capacity_bcm", "start_year",
    "trains", "vessel_name", "notes",
]


# ---------------------------------------------------------------------------
# pdftotext wrapper
# ---------------------------------------------------------------------------

def _pdftotext(pdf_path: str, first: int, last: int) -> str:
    """Return -layout text for pages [first, last] inclusive (1-indexed)."""
    result = subprocess.run(
        ["pdftotext", "-layout", "-f", str(first), "-l", str(last),
         pdf_path, "-"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout


def _page_count(pdf_path: str) -> int:
    out = subprocess.run(
        ["pdfinfo", pdf_path], capture_output=True, text=True, check=True,
    ).stdout
    m = re.search(r"Pages:\s+(\d+)", out)
    if not m:
        sys.exit(f"ERROR: pdfinfo gave no page count for {pdf_path}")
    return int(m.group(1))


def _find_table_pages(pdf_path: str, marker: str) -> list[int]:
    """Return 1-indexed pages whose first ~200 chars contain `marker`."""
    n = _page_count(pdf_path)
    text = _pdftotext(pdf_path, 1, n)
    # pdftotext emits a form-feed character (\x0c) between pages.
    page_texts = text.split("\x0c")
    hits = []
    for i, pt in enumerate(page_texts):
        # Marker has to be in the top band — discard pages where the phrase
        # only appears as a small caption far down the page.
        head = pt[:400]
        if marker in head:
            hits.append(i + 1)
    return hits


# ---------------------------------------------------------------------------
# Column-boundary detection
# ---------------------------------------------------------------------------

@dataclass
class ColumnSpec:
    """One column's name and inclusive [start, end) character positions in a line."""
    name: str
    start: int
    end: int  # exclusive

    def slice(self, line: str) -> str:
        return line[self.start:self.end].strip()


def _find_columns_by_header(
    page_text: str, header_keywords: list[str],
) -> tuple[list[ColumnSpec], int]:
    """Locate the header line and derive column [start, end) ranges from it.

    Returns (columns, header_line_index_within_page).

    Algorithm:
      - Find the line containing the FIRST keyword (`Country` for liq tables,
        `Market` for regas tables) at left margin
      - On that line, locate each keyword's position; column N runs from
        keyword N's start to keyword N+1's start (last column to line end)
    """
    lines = page_text.splitlines()
    header_line_idx = None
    for i, ln in enumerate(lines):
        # Strict match: first keyword must be the first non-space token on
        # the line, AND all keywords must appear in order.
        stripped = ln.lstrip()
        if not stripped.startswith(header_keywords[0]):
            continue
        positions = []
        cursor = 0
        ok = True
        for kw in header_keywords:
            pos = ln.find(kw, cursor)
            if pos == -1:
                ok = False
                break
            positions.append(pos)
            cursor = pos + len(kw)
        if ok:
            header_line_idx = i
            break
    if header_line_idx is None:
        return [], -1

    header_line = lines[header_line_idx]
    positions = []
    cursor = 0
    for kw in header_keywords:
        pos = header_line.find(kw, cursor)
        positions.append(pos)
        cursor = pos + len(kw)

    # Build [start, end) per column. End of column N = start of column N+1.
    # For the last column, extend to a generous large number (full line width).
    columns = []
    for n, kw in enumerate(header_keywords):
        start = positions[n]
        end = positions[n + 1] if n + 1 < len(positions) else 10_000
        columns.append(ColumnSpec(name=kw, start=start, end=end))
    return columns, header_line_idx


# Header keywords per table type. Use the position-stable words from each
# header. Avoided ambiguous words (e.g. "Number" appears twice in liq header).
LIQ_HEADER_KEYWORDS = [
    "Country", "Project", "(MTPA)", "of trains", "of tanks", "(liq,m3)",
    "Owner(s)", "Operator", "MT - LT Buyer(s)", "date",
]
REGAS_HEADER_KEYWORDS = [
    "Market", "Site", "Concept", "of tanks", "(liq m3)", "vaporizers",
    "(MTPA)", "Owner", "Operator", "Access", "offered", "date",
]


# ---------------------------------------------------------------------------
# Row parsing
# ---------------------------------------------------------------------------

# A train suffix on a GIIGNL project name. Handles all of:
#   " T2", " T1-6", " T7-12", " T1 - T6", " T1 – T6" (en-dash, with spaces)
# Strip this off site_name and record in `trains`.
_TRAIN_SUFFIX_RE = re.compile(
    r"\s+(T\d+(?:\s*[-–]\s*T?\d+)?)\s*$"
)

# Super-region markers in GIIGNL liquefaction tables, e.g.
# "ATLANTIC BASIN: 236.5 MTPA", "PACIFIC BASIN: 122 MTPA", "MIDDLE EAST: ...".
# These appear at the top of multi-country blocks and should be ignored
# (they are NOT country labels).
_SUPER_REGION_RE = re.compile(
    r"^\s*(ATLANTIC BASIN|PACIFIC BASIN|MIDDLE EAST|AFRICA|EUROPE|ASIA|"
    r"NORTH AMERICA|SOUTH AMERICA|AMERICAS)\s*[:\s]\s*[\d,.]+\s*MTPA\s*$",
    re.IGNORECASE,
)

# A status-hint parenthetical, e.g. "(Mothballed)", "(Idle)".
_STATUS_HINT_RE = re.compile(r"\(([^)]+)\)\s*$")

# A pure numeric capacity (e.g. "5.5", "0.9", "10").
_NUM_RE = re.compile(r"^-?\d+(?:\.\d+)?$")

# A "Country X.Y MTPA" or "Country X MTPA" subtotal line: country label cell
# spans across the whole row and a separate MTPA total appears below it.
_COUNTRY_SUBTOTAL_RE = re.compile(r"^([\d,.]+)\s*MTPA\s*$")


def _strip_train_suffix(project: str) -> tuple[str, str, str]:
    """Return (site_name, trains, status_hint).

    "Yamal LNG T2"               -> ("Yamal LNG", "T2", "")
    "Calcasieu Pass LNG T1-6"    -> ("Calcasieu Pass LNG", "T1-6", "")
    "Atlantic LNG T1 (Mothballed)" -> ("Atlantic LNG", "T1", "Mothballed")
    "MLNG Dua"                   -> ("MLNG Dua", "", "")
    """
    s = project.strip()
    # First peel off any trailing parenthetical (status hint).
    status_hint = ""
    m_status = _STATUS_HINT_RE.search(s)
    if m_status:
        candidate = m_status.group(1).strip()
        # Only treat as status hint if it's a short word like "Mothballed",
        # "Idle", etc. (avoid eating "100%" or year parentheticals)
        if candidate.isalpha() and len(candidate) <= 20:
            status_hint = candidate
            s = s[: m_status.start()].rstrip()

    trains = ""
    m_train = _TRAIN_SUFFIX_RE.search(s)
    if m_train:
        trains = m_train.group(1).strip()
        s = s[: m_train.start()].rstrip()
    return s, trains, status_hint


@dataclass
class LogicalRow:
    """One in-progress data row being built across multiple physical lines."""
    section_type: str
    country: str
    cells: dict[str, str] = field(default_factory=dict)

    def append(self, col: str, fragment: str) -> None:
        if not fragment:
            return
        prior = self.cells.get(col, "")
        self.cells[col] = (prior + " " + fragment).strip() if prior else fragment


def _is_country_label_line(
    line: str, columns: list[ColumnSpec],
) -> tuple[bool, str]:
    """A country-label line has text only in the leftmost column and is
    otherwise blank. Returns (is_label, country_text).
    """
    if not columns:
        return False, ""
    # Reject super-region markers like "ATLANTIC BASIN: 236.5 MTPA".
    if _SUPER_REGION_RE.match(line):
        return False, ""
    left = columns[0].slice(line)
    # Everything to the right of the first column should be blank.
    right_text = line[columns[0].end:].strip()
    if left and not right_text:
        # Skip if "left" is a numeric (that'd be a country subtotal handled separately)
        if _COUNTRY_SUBTOTAL_RE.match(left):
            return False, ""
        # Skip if "left" is a pure number
        if _NUM_RE.match(left):
            return False, ""
        # Skip if "left" contains ":" (likely a super-region marker that
        # leaked through the column slice).
        if ":" in left:
            return False, ""
        return True, left
    return False, ""


def _is_country_subtotal_line(
    line: str, columns: list[ColumnSpec],
) -> tuple[bool, float]:
    """A country-subtotal line has text like '24.9 MTPA' in the leftmost column
    and nothing in the data columns. Returns (is_subtotal, mtpa_value).
    """
    if not columns:
        return False, 0.0
    left = columns[0].slice(line)
    right_text = line[columns[0].end:].strip()
    m = _COUNTRY_SUBTOTAL_RE.match(left)
    if m and not right_text:
        try:
            return True, float(m.group(1).replace(",", ""))
        except ValueError:
            return False, 0.0
    return False, 0.0


def _is_data_row_start(
    line: str, columns: list[ColumnSpec], capacity_col_name: str,
) -> bool:
    """A new logical data row starts when the capacity column has a numeric value."""
    cap_col = next((c for c in columns if c.name == capacity_col_name), None)
    if cap_col is None:
        return False
    cap_text = cap_col.slice(line)
    return bool(cap_text) and bool(_NUM_RE.match(cap_text.split()[0])) if cap_text else False


def _parse_float(s: str) -> float | None:
    s = s.strip().replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _parse_int(s: str) -> int | None:
    s = s.strip().replace(",", "").replace(".", "")
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Page-level extraction
# ---------------------------------------------------------------------------

def _extract_liquefaction_page(
    page_text: str, page_num: int,
) -> tuple[list[dict], float]:
    """Returns (rows, page_capacity_sum_mtpa)."""
    columns, hdr_idx = _find_columns_by_header(page_text, LIQ_HEADER_KEYWORDS)
    if hdr_idx < 0:
        return [], 0.0
    lines = page_text.splitlines()
    data_lines = lines[hdr_idx + 1:]

    rows: list[dict] = []
    current_country = ""
    current_row: LogicalRow | None = None
    page_cap_sum = 0.0

    def flush():
        nonlocal current_row, page_cap_sum
        if current_row is None:
            return
        c = current_row.cells
        project_raw = c.get("Project", "").strip()
        site_name, trains, status_hint = _strip_train_suffix(project_raw)
        cap_mtpa = _parse_float(c.get("(MTPA)", "").split()[0] if c.get("(MTPA)", "") else "")
        if cap_mtpa is None:
            cap_mtpa = 0.0
        page_cap_sum += cap_mtpa
        start_year = _parse_int(c.get("date", ""))
        notes_parts = [f"row name: {project_raw}"]
        if status_hint:
            notes_parts.append(f"status hint: {status_hint}")
        rows.append({
            "section_type": "liquefaction",
            "report_page": page_num,
            "country": current_row.country,
            "site_name": site_name,
            "type": "",
            "owner": c.get("Owner(s)", "").strip(),
            "capacity_mtpa": f"{cap_mtpa:g}",
            "capacity_bcm": "",
            "start_year": str(start_year) if start_year else "",
            "trains": trains,
            "vessel_name": "",
            "notes": "; ".join(notes_parts),
        })
        current_row = None

    cap_col_name = "(MTPA)"
    for ln in data_lines:
        if not ln.strip():
            continue

        # Check country subtotal first (it appears below the country header).
        is_sub, _ = _is_country_subtotal_line(ln, columns)
        if is_sub:
            # subtotal: doesn't introduce a row; just metadata
            continue

        is_label, country = _is_country_label_line(ln, columns)
        if is_label:
            flush()
            current_country = country
            continue

        if _is_data_row_start(ln, columns, cap_col_name):
            flush()
            current_row = LogicalRow(
                section_type="liquefaction", country=current_country,
            )
            for col in columns:
                current_row.cells[col.name] = col.slice(ln)
            continue

        # Continuation line — append text from each non-empty cell
        # to the corresponding cell of the in-progress row.
        if current_row is not None:
            for col in columns:
                frag = col.slice(ln)
                if frag:
                    # Country column on continuation lines often holds a
                    # leftover country name — skip if it matches the existing
                    # country to avoid duplicating.
                    if col.name == "Country" and frag == current_row.country:
                        continue
                    current_row.append(col.name, frag)
    flush()
    return rows, page_cap_sum


def _extract_regasification_page(
    page_text: str, page_num: int,
) -> tuple[list[dict], float]:
    columns, hdr_idx = _find_columns_by_header(page_text, REGAS_HEADER_KEYWORDS)
    if hdr_idx < 0:
        return [], 0.0
    lines = page_text.splitlines()
    data_lines = lines[hdr_idx + 1:]

    rows: list[dict] = []
    current_country = ""
    current_row: LogicalRow | None = None
    page_cap_sum = 0.0

    def flush():
        nonlocal current_row, page_cap_sum
        if current_row is None:
            return
        c = current_row.cells
        site_raw = c.get("Site", "").strip()
        # Regas tables sometimes include FSRU vessel name in site, e.g.
        # "Ain Sokhna 3 (Energos Eskimo)" or "Escobar / Excelerate Expedient (FSRU)"
        site_name = site_raw
        vessel_name = ""
        # Pull out (Vessel Name) parenthetical if present
        m = re.search(r"\(([^)]+)\)\s*$", site_raw)
        if m:
            inner = m.group(1).strip()
            # FSRU vessel names typically contain a word, not "FSRU" alone.
            if inner.lower() not in ("fsru", "flng", "fsu", "fru") and not inner.isdigit():
                vessel_name = inner
            site_name = site_raw[: m.start()].strip()

        cap_mtpa = _parse_float(c.get("(MTPA)", "").split()[0] if c.get("(MTPA)", "") else "")
        if cap_mtpa is None:
            cap_mtpa = 0.0
        page_cap_sum += cap_mtpa
        start_year = _parse_int(c.get("date", ""))
        concept = c.get("Concept", "").strip().lower()
        type_val = ""
        if "offshore" in concept or vessel_name:
            type_val = "FSRU" if vessel_name else "offshore"
        elif "onshore" in concept:
            type_val = "onshore"
        notes_parts = [f"row name: {site_raw}"]
        rows.append({
            "section_type": "regasification",
            "report_page": page_num,
            "country": current_row.country,
            "site_name": site_name,
            "type": type_val,
            "owner": c.get("Owner", "").strip(),
            "capacity_mtpa": f"{cap_mtpa:g}",
            "capacity_bcm": "",
            "start_year": str(start_year) if start_year else "",
            "trains": "",
            "vessel_name": vessel_name,
            "notes": "; ".join(notes_parts),
        })
        current_row = None

    cap_col_name = "(MTPA)"
    for ln in data_lines:
        if not ln.strip():
            continue

        is_sub, _ = _is_country_subtotal_line(ln, columns)
        if is_sub:
            continue

        is_label, country = _is_country_label_line(ln, columns)
        if is_label:
            flush()
            current_country = country
            continue

        if _is_data_row_start(ln, columns, cap_col_name):
            flush()
            current_row = LogicalRow(
                section_type="regasification", country=current_country,
            )
            for col in columns:
                current_row.cells[col.name] = col.slice(ln)
            continue

        if current_row is not None:
            for col in columns:
                frag = col.slice(ln)
                if frag:
                    if col.name == "Market" and frag == current_row.country:
                        continue
                    current_row.append(col.name, frag)
    flush()
    return rows, page_cap_sum


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def extract(pdf_path: str, output_csv: str, year: int = 2026) -> dict:
    print(f"Scanning {pdf_path} for liquefaction and regasification pages...")
    liq_pages = _find_table_pages(pdf_path, LIQ_PAGE_MARKER)
    regas_pages = _find_table_pages(pdf_path, REGAS_PAGE_MARKER)
    print(f"  Liquefaction pages: {liq_pages}")
    print(f"  Regasification pages: {regas_pages}")

    all_rows: list[dict] = []
    liq_total = 0.0
    regas_total = 0.0

    if liq_pages:
        full_text = _pdftotext(pdf_path, liq_pages[0], liq_pages[-1])
        page_texts = full_text.split("\x0c")
        for offset, page_num in enumerate(range(liq_pages[0], liq_pages[-1] + 1)):
            if page_num not in liq_pages:
                continue
            if offset >= len(page_texts):
                continue
            page_rows, cap_sum = _extract_liquefaction_page(page_texts[offset], page_num)
            all_rows.extend(page_rows)
            liq_total += cap_sum
            print(f"    page {page_num}: {len(page_rows)} liq rows, {cap_sum:.1f} MTPA")

    if regas_pages:
        full_text = _pdftotext(pdf_path, regas_pages[0], regas_pages[-1])
        page_texts = full_text.split("\x0c")
        for offset, page_num in enumerate(range(regas_pages[0], regas_pages[-1] + 1)):
            if page_num not in regas_pages:
                continue
            if offset >= len(page_texts):
                continue
            page_rows, cap_sum = _extract_regasification_page(page_texts[offset], page_num)
            all_rows.extend(page_rows)
            regas_total += cap_sum
            print(f"    page {page_num}: {len(page_rows)} regas rows, {cap_sum:.1f} MTPA")

    # Write CSV.
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        w.writeheader()
        for r in all_rows:
            w.writerow(r)

    print(f"\nWrote {len(all_rows)} rows to {output_csv}")
    print(f"  Liquefaction total: {liq_total:.1f} MTPA")
    print(f"  Regasification total: {regas_total:.1f} MTPA")

    summary = {
        "liq_total": liq_total,
        "regas_total": regas_total,
        "liq_page_count": len(liq_pages),
        "regas_page_count": len(regas_pages),
        "row_count": len(all_rows),
    }

    expected = EXPECTED_TOTALS.get(year)
    if expected:
        for kind, total in [("liquefaction", liq_total), ("regasification", regas_total)]:
            exp = expected[kind]
            diff_pct = abs(total - exp) / exp * 100
            mark = "OK" if diff_pct <= 2 else "OUT OF TOLERANCE (>2%)"
            print(f"  {kind} vs expected {exp:.0f}: delta {total - exp:+.1f} ({diff_pct:.1f}%) [{mark}]")
            summary[f"{kind}_expected"] = exp
            summary[f"{kind}_diff_pct"] = diff_pct
    return summary


def main():
    p = argparse.ArgumentParser()
    p.add_argument("pdf", help="Path to GIIGNL annual report PDF")
    p.add_argument("--output", default="giignl_extracted.csv",
                   help="Output CSV path (default: giignl_extracted.csv)")
    p.add_argument("--year", type=int, default=2026,
                   help="Report edition year (for sanity-check totals)")
    args = p.parse_args()

    if not Path(args.pdf).exists():
        sys.exit(f"ERROR: PDF not found at {args.pdf}")
    extract(args.pdf, args.output, year=args.year)


if __name__ == "__main__":
    main()
