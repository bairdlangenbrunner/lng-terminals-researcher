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
# Two-pass page extraction
# ---------------------------------------------------------------------------
#
# Why two-pass: GIIGNL data rows span multiple physical lines (site name
# above the data line, vessel name and owner cell continuations below).
# A simple "capacity numeric = new row" detector starts the row on the
# wrong line and pulls in fragments from the next row's pre-data lines.
#
# Pass 1: classify each non-blank line as data, country_label, country_subtotal,
#         super_region, or generic_continuation.
# Pass 2: for each data line, gather the lines around it (split at midpoints
#         between consecutive data lines) and merge all their cell-fragments
#         into one logical row.
# Pass 3: backfill country from labels by line-proximity.


def _classify_lines(
    lines: list[str], columns: list[ColumnSpec], cap_col_name: str,
) -> tuple[list[int], list[tuple[int, str]], set[int]]:
    """Returns (data_line_indices, country_label_records, skip_indices).

    Multi-line country labels (e.g. "Mauritania/" + "Senegal" on consecutive
    lines, "Equatorial" + "Guinea") are merged: only the first line's index
    is kept, with the combined text.
    """
    data_idxs: list[int] = []
    raw_labels: list[tuple[int, str]] = []
    skip: set[int] = set()
    for i, ln in enumerate(lines):
        if not ln.strip():
            continue
        if _SUPER_REGION_RE.match(ln):
            skip.add(i)
            continue
        is_sub, _ = _is_country_subtotal_line(ln, columns)
        if is_sub:
            skip.add(i)
            continue
        is_label, country = _is_country_label_line(ln, columns)
        if is_label:
            raw_labels.append((i, country))
            skip.add(i)
            continue
        if _is_data_row_start(ln, columns, cap_col_name):
            data_idxs.append(i)

    # Merge consecutive country labels (multi-line wrap like "Mauritania/"
    # then "Senegal"). Two labels merge iff no data line lies between them
    # AND they're within ~3 lines of each other.
    merged_labels: list[tuple[int, str]] = []
    for i, (line_idx, txt) in enumerate(raw_labels):
        if merged_labels:
            prev_idx, prev_txt = merged_labels[-1]
            gap = line_idx - prev_idx
            intervening_data = any(prev_idx < d < line_idx for d in data_idxs)
            if gap <= 3 and not intervening_data:
                # Merge: trim trailing "/" or "-" before joining
                stitched = prev_txt.rstrip("/-").rstrip() + (
                    "/" if prev_txt.rstrip().endswith("/") else " "
                ) + txt
                merged_labels[-1] = (prev_idx, stitched.strip())
                continue
        merged_labels.append((line_idx, txt))
    return data_idxs, merged_labels, skip


def _partition_lines_by_data(
    lines: list[str], data_idxs: list[int], skip: set[int],
) -> dict[int, list[int]]:
    """Assign each non-blank, non-skipped line to its owning data-line row.

    Boundaries: midpoint between consecutive data lines.
    """
    if not data_idxs:
        return {}
    boundaries = []
    for i in range(len(data_idxs) - 1):
        mid = (data_idxs[i] + data_idxs[i + 1]) // 2
        boundaries.append(mid)
    assignments: dict[int, list[int]] = {i: [] for i in range(len(data_idxs))}
    cur_row = 0
    for i, ln in enumerate(lines):
        if not ln.strip():
            continue
        if i in skip:
            continue
        while cur_row < len(boundaries) and i > boundaries[cur_row]:
            cur_row += 1
        assignments[cur_row].append(i)
    return assignments


def _merge_lines_into_cells(
    lines: list[str], line_idxs: list[int], columns: list[ColumnSpec],
) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Combine fragments from each line in line_idxs into one cell dict.

    Returns (merged_str_per_col, fragments_per_col). The fragment list is
    needed downstream when the regas vessel-name parser needs to distinguish
    the site-name fragment (first one) from the vessel-name fragment (later
    one that contains "(FSRU)" etc.) — joining them loses that structure.
    """
    cells: dict[str, list[str]] = {col.name: [] for col in columns}
    for idx in line_idxs:
        ln = lines[idx]
        for col in columns:
            frag = col.slice(ln)
            if frag:
                if cells[col.name] and cells[col.name][-1] == frag:
                    continue
                cells[col.name].append(frag)
    merged = {name: " ".join(parts) for name, parts in cells.items()}
    return merged, cells


def _assign_countries_sequential(
    rows_with_meta: list[tuple[int, str, dict]],
    labels: list[tuple[int, str]],
) -> None:
    """Mutate each row dict's 'country' field via a sequential walk.

    rows_with_meta = list of (data_line_idx, explicit_country_from_cell, row_dict)
                     in row order.
    labels         = list of (label_line_idx, country) in line order.

    Algorithm: walk events (rows + labels) in line order. Maintain a running
    `current_country`. When a row has an explicit country, that updates
    current_country and the row gets it. When a row has no explicit country,
    it inherits current_country (i.e., the most recent country-anchor event).
    Rows seen before any country event are buffered and back-filled when the
    first event arrives.

    Replaces the earlier "nearest-label" heuristic which misassigned rows
    when continuation lines stretched the line-index gap between labels
    (e.g., Sabine Pass T2-T6 inherit USA from T1's explicit cell, not from
    whichever label happened to be closer by raw line distance).
    """
    events = []
    for data_idx, explicit, row in rows_with_meta:
        events.append((data_idx, 1, explicit, row))  # 1 sorts after labels at tie
    for line_idx, country in labels:
        events.append((line_idx, 0, country, None))
    events.sort(key=lambda e: (e[0], e[1]))

    current_country = ""
    pending: list[dict] = []
    for _, kind, payload, row in events:
        if kind == 0:  # label
            for r in pending:
                r["country"] = payload
            pending = []
            current_country = payload
        else:  # row
            if payload:  # explicit country in cell
                for r in pending:
                    r["country"] = payload
                pending = []
                current_country = payload
                row["country"] = payload
            elif current_country:
                row["country"] = current_country
            else:
                pending.append(row)
                row["country"] = ""
    # Rows still pending at end-of-page have no country.


# ---------------------------------------------------------------------------
# Page-level extraction
# ---------------------------------------------------------------------------

def _extract_liquefaction_page(
    page_text: str, page_num: int,
) -> tuple[list[dict], float]:
    columns, hdr_idx = _find_columns_by_header(page_text, LIQ_HEADER_KEYWORDS)
    if hdr_idx < 0:
        return [], 0.0
    lines = page_text.splitlines()
    body_lines = lines[hdr_idx + 1:]
    cap_col = "(MTPA)"

    data_idxs, labels, skip = _classify_lines(body_lines, columns, cap_col)
    assignments = _partition_lines_by_data(body_lines, data_idxs, skip)

    rows: list[dict] = []
    rows_with_meta: list[tuple[int, str, dict]] = []
    page_cap_sum = 0.0
    for row_idx, data_idx in enumerate(data_idxs):
        merged, _frags = _merge_lines_into_cells(body_lines, assignments[row_idx], columns)
        project_raw = merged.get("Project", "").strip()
        if not project_raw:
            continue
        site_name, trains, status_hint = _strip_train_suffix(project_raw)
        explicit_country = ""
        for idx in assignments[row_idx]:
            ln = body_lines[idx]
            cell = columns[0].slice(ln).strip()
            if cell and not _SUPER_REGION_RE.match(ln) and ":" not in cell \
               and not _COUNTRY_SUBTOTAL_RE.match(cell) and not _NUM_RE.match(cell):
                explicit_country = cell
                break
        cap_text = merged.get(cap_col, "").split()[0] if merged.get(cap_col, "") else ""
        cap_mtpa = _parse_float(cap_text) or 0.0
        page_cap_sum += cap_mtpa
        start_year = _parse_int(merged.get("date", ""))
        notes_parts = [f"row name: {project_raw}"]
        if status_hint:
            notes_parts.append(f"status hint: {status_hint}")
        row = {
            "section_type": "liquefaction",
            "report_page": page_num,
            "country": "",  # assigned below
            "site_name": site_name,
            "type": "",
            "owner": merged.get("Owner(s)", "").strip(),
            "capacity_mtpa": f"{cap_mtpa:g}",
            "capacity_bcm": "",
            "start_year": str(start_year) if start_year else "",
            "trains": trains,
            "vessel_name": "",
            "notes": "; ".join(notes_parts),
        }
        rows.append(row)
        rows_with_meta.append((data_idx, explicit_country, row))
    _assign_countries_sequential(rows_with_meta, labels)
    return rows, page_cap_sum


def _extract_regasification_page(
    page_text: str, page_num: int,
) -> tuple[list[dict], float]:
    columns, hdr_idx = _find_columns_by_header(page_text, REGAS_HEADER_KEYWORDS)
    if hdr_idx < 0:
        return [], 0.0
    lines = page_text.splitlines()
    body_lines = lines[hdr_idx + 1:]
    cap_col = "(MTPA)"

    data_idxs, labels, skip = _classify_lines(body_lines, columns, cap_col)
    assignments = _partition_lines_by_data(body_lines, data_idxs, skip)

    rows: list[dict] = []
    rows_with_meta: list[tuple[int, str, dict]] = []
    page_cap_sum = 0.0
    for row_idx, data_idx in enumerate(data_idxs):
        merged, frags = _merge_lines_into_cells(body_lines, assignments[row_idx], columns)
        site_fragments = frags.get("Site", [])
        site_raw = " ".join(site_fragments).strip()
        if not site_raw:
            continue
        # Use the fragment list to separate site name from vessel name.
        # The site name is typically the first fragment(s); the vessel name
        # appears in a later fragment containing "(FSRU)" / "(FLNG)" etc.
        vessel_name = ""
        site_parts: list[str] = []
        for frag in site_fragments:
            m_tag = re.search(r"\(\s*(FSRU|FLNG|FSU|FRU)\s*\)", frag, re.IGNORECASE)
            if m_tag:
                # This fragment is the vessel name. Strip the (FSRU) tag.
                vessel_clean = re.sub(
                    r"\s*\(\s*(?:FSRU|FLNG|FSU|FRU)\s*\)\s*", " ",
                    frag, flags=re.IGNORECASE,
                ).strip()
                vessel_name = vessel_clean
            else:
                site_parts.append(frag)
        site_name = " ".join(site_parts).strip() or site_raw

        explicit_country = ""
        for idx in assignments[row_idx]:
            ln = body_lines[idx]
            cell = columns[0].slice(ln).strip()
            if cell and not _SUPER_REGION_RE.match(ln) and ":" not in cell \
               and not _COUNTRY_SUBTOTAL_RE.match(cell) and not _NUM_RE.match(cell):
                explicit_country = cell
                break

        cap_text = merged.get(cap_col, "").split()[0] if merged.get(cap_col, "") else ""
        cap_mtpa = _parse_float(cap_text) or 0.0
        page_cap_sum += cap_mtpa
        start_year = _parse_int(merged.get("date", ""))
        concept = merged.get("Concept", "").strip().lower()
        type_val = ""
        if "offshore" in concept or vessel_name:
            type_val = "FSRU" if vessel_name else "offshore"
        elif "onshore" in concept:
            type_val = "onshore"
        notes_parts = [f"row name: {site_raw}"]
        row = {
            "section_type": "regasification",
            "report_page": page_num,
            "country": "",  # assigned below
            "site_name": site_name,
            "type": type_val,
            "owner": merged.get("Owner", "").strip(),
            "capacity_mtpa": f"{cap_mtpa:g}",
            "capacity_bcm": "",
            "start_year": str(start_year) if start_year else "",
            "trains": "",
            "vessel_name": vessel_name,
            "notes": "; ".join(notes_parts),
        }
        rows.append(row)
        rows_with_meta.append((data_idx, explicit_country, row))
    _assign_countries_sequential(rows_with_meta, labels)
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
