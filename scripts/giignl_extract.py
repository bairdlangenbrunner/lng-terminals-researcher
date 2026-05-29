"""
Extract liquefaction and regasification tables from the GIIGNL Annual Report.

The 2026 edition shipped as a real PDF (v1.7) with a clean text layer, so we
parse it directly via `pdftotext -layout` rather than rendering pages to JPEG
and using a vision model. (Earlier editions shipped as a zip-of-JPEGs+OCR;
that pipeline is in git history if a future edition needs it back.)

Output is a flat CSV consumed by `report_diff.py` — column shape:
  section_type, report_page, country, site_name, type,
  owner, capacity_mtpa, capacity_bcm, start_year, trains, vessel_name, notes,
  status

`status` is the canonical non-operating lifecycle status when GIIGNL annotates a
row with a status parenthetical ("Bontang Train E (Mothballed)", "Balhaf T1
(stopped)") — empty for the normal operating row. GIIGNL's liq/regas tables are
operating-only, so report_diff treats a non-empty status as a cue to EXCLUDE the
row from the operating-capacity comparison and corroborate the matching GEM
non-operating unit instead.

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
    "trains", "vessel_name", "notes", "status",
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

# Page footer, a standalone line "<page#> - GIIGNL Annual Report <year> Edition".
# It sits at the bottom of every table page; if not skipped, the line-merge pass
# folds it into the last data row of the page and the column slicer splits the
# footer text across cells (e.g. "Annual" → country cell "… GIIGNL An" + site cell
# "nual Report 2026 Edition"), corrupting that row (QatarEnergy LNG S(2) T4, Yamal
# T1, Ruwais, etc.). Matched leniently so an edition-year or spacing change still
# trips it.
_PAGE_FOOTER_RE = re.compile(
    r"GIIGNL\s+Annual\s+Report\s+\d{4}\s+Edition", re.IGNORECASE
)

# Zero-width characters GIIGNL embeds mid-token (e.g. "S(2 )" -> "S(2<U+200B>)").
# Stripped from names so the designator token "S(2)" survives intact for matching.
_ZERO_WIDTH_RE = re.compile("[​‌‍﻿]")


def _clean_text(s: str) -> str:
    return _ZERO_WIDTH_RE.sub("", s) if s else s


# A status-hint parenthetical, e.g. "(Mothballed)", "(Idle)".
_STATUS_HINT_RE = re.compile(r"\(([^)]+)\)\s*$")

# Maps a GIIGNL status-hint word (the parenthetical peeled off a name) to a
# canonical NON-operating GEM lifecycle status. GIIGNL's liq/regas tables are
# operating-only, but a few rows are annotated as not-currently-operating —
# "Bontang Train E (Mothballed)", "Balhaf T1 (stopped)", "Atlantic LNG T1
# (Mothballed)". report_diff uses the status to drop the row from the operating
# total (so it isn't a spurious capacity conflict) and to corroborate the GEM
# non-op unit it lines up with. An UNRECOGNIZED hint maps to "" — the row stays
# operating and the raw hint survives only as a note (we don't guess on words we
# don't know, e.g. a stray "100%" that slipped the numeric guard).
_NONOP_STATUS_HINTS = {
    "mothballed": "mothballed", "mothball": "mothballed", "mothballing": "mothballed",
    "idle": "idled", "idled": "idled", "idling": "idled",
    "stopped": "idled", "stop": "idled", "suspended": "idled",
    "shut": "idled", "shutdown": "idled", "halted": "idled", "paused": "idled",
    "retired": "retired", "decommissioned": "retired", "closed": "retired",
    "cancelled": "cancelled", "canceled": "cancelled",
    "shelved": "shelved",
}


def _status_from_hint(hint: str) -> str:
    """Canonical non-operating status for a parenthetical hint, or '' if the hint
    isn't a recognized non-op word.  'Mothballed' -> 'mothballed'."""
    if not hint:
        return ""
    return _NONOP_STATUS_HINTS.get(re.sub(r"[^a-z]", "", hint.lower()), "")

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
        # "Idle", etc. (avoid eating "100%" or year parentheticals). A facility-type
        # tag — "(FLNG)", "(FSRU)", "(FSU)", "(FRU)" — is part of the terminal NAME,
        # not a status, so keep it (e.g. "Prelude (FLNG)" must stay intact).
        if candidate.isalpha() and len(candidate) <= 20 \
                and candidate.upper() not in ("FLNG", "FSRU", "FSU", "FRU", "FPSO"):
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
    """A country-subtotal line has text like '24.9 MTPA' in the leftmost
    column. The right side of the line MAY contain owner/operator wrap-text
    from an adjacent row — GIIGNL typesets the subtotal as a centered band
    that physically overlaps with owner-cell text from a neighboring row when
    pdftotext linearizes the page. We require the CAPACITY column to be
    empty to distinguish a subtotal from a real data row (data rows always
    have a capacity value; subtotals don't).
    """
    if not columns:
        return False, 0.0
    left = columns[0].slice(line)
    m = _COUNTRY_SUBTOTAL_RE.match(left)
    if not m:
        return False, 0.0
    cap_col = next((c for c in columns if c.name == "(MTPA)"), None)
    if cap_col and cap_col.slice(line).strip():
        return False, 0.0
    try:
        return True, float(m.group(1).replace(",", ""))
    except ValueError:
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
) -> tuple[list[int], list[tuple[int, str]], set[int], list[tuple[int, float]]]:
    """Returns (data_line_indices, country_label_records, skip_indices, subtotals).

    Multi-line country labels (e.g. "Mauritania/" + "Senegal" on consecutive
    lines, "Equatorial" + "Guinea") are merged: only the first line's index
    is kept, with the combined text.

    Subtotals are captured (not just skipped) so _assign_countries_sequential
    can use them as per-country capacity budgets — once cumulative capacity
    for current_country exceeds its subtotal, subsequent rows go into pending
    (awaiting the next country label) rather than inheriting current_country.
    This handles the case where Country X ends and Country Y's rows start
    before Y's label appears (e.g. Bangladesh's 2 rows end on page 55, then
    China's many rows start before China's label appears mid-block).
    """
    data_idxs: list[int] = []
    raw_labels: list[tuple[int, str]] = []
    skip: set[int] = set()
    subtotals: list[tuple[int, float]] = []
    for i, ln in enumerate(lines):
        if not ln.strip():
            continue
        if _PAGE_FOOTER_RE.search(ln):
            skip.add(i)
            continue
        if _SUPER_REGION_RE.match(ln):
            skip.add(i)
            continue
        is_sub, mtpa = _is_country_subtotal_line(ln, columns)
        if is_sub:
            subtotals.append((i, mtpa))
            # GIIGNL vertically centers the country label + subtotal within a
            # block, so the subtotal sometimes lands ON a data row's physical
            # lines — carrying that row's name-column fragment (e.g. "N(3) T6"
            # beside "77.0 MTPA"). Skipping the whole line then drops the train
            # code and the row degrades to a bare "QatarEnergy LNG". Only skip a
            # PURE subtotal line; if the name column (col 1) has text, leave the
            # line for the merge pass so the fragment reaches its data row.
            name_frag = columns[1].slice(ln) if len(columns) > 1 else ""
            if not name_frag:
                skip.add(i)
            continue
        # Embedded subtotal on a *data* row: GIIGNL centers the country
        # label+subtotal band onto a data row, so col 0 reads "156.4 MTPA" while
        # the row ALSO carries a real capacity (South Korea's subtotal sits on
        # the Pyeong-Taek row, Spain's 49.3 on El Musel, Japan's 221.2 on Himeji).
        # _is_country_subtotal_line rejects these because the capacity column is
        # filled, so the per-country budget is lost and the centered block's
        # leading rows never get reclaimed. Record the budget here (so the
        # cross-page reclaim can use it) but do NOT skip — the line is still a
        # data row, and the explicit-country extractor already ignores a
        # "X MTPA" col-0 cell, so the row keeps its real country.
        if columns:
            _left0 = columns[0].slice(ln)
            _m_emb = _COUNTRY_SUBTOTAL_RE.match(_left0)
            if _m_emb and _is_data_row_start(ln, columns, cap_col_name):
                try:
                    subtotals.append((i, float(_m_emb.group(1).replace(",", ""))))
                except ValueError:
                    pass
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
                stitched = prev_txt.rstrip("/-").rstrip() + (
                    "/" if prev_txt.rstrip().endswith("/") else " "
                ) + txt
                merged_labels[-1] = (prev_idx, stitched.strip())
                continue
        merged_labels.append((line_idx, txt))
    return data_idxs, merged_labels, skip, subtotals


def _partition_lines_by_data(
    lines: list[str], data_idxs: list[int], skip: set[int],
    columns: list[ColumnSpec] | None = None, cap_col_name: str = "(MTPA)",
) -> dict[int, list[int]]:
    """Assign each non-blank, non-skipped line to its owning data-line row.

    Each line goes to the NEAREST data line by row distance — equivalent to the
    old midpoint split for the common case. The fix is the TIE: when a line sits
    exactly between two data rows, a GIIGNL multi-line site name whose leading
    line lands on the midpoint was being swallowed by the row above. A tie line
    that carries a NAME-column fragment which begins a new name (starts
    uppercase, no capacity) belongs to the row BELOW (its leading name); a
    lowercase fragment ("...project)") or owner-wrap text is a continuation of
    the row ABOVE. This recovers e.g. APLNG T2 (no longer fused with "Darwin LNG
    (new") and Darwin's full name "Darwin LNG (new supply source Barossa
    project)", and Croatia "Krk".
    """
    if not data_idxs:
        return {}
    name_col = columns[1] if (columns and len(columns) > 1) else None
    cap_col = next((c for c in columns if c.name == cap_col_name), None) if columns else None
    assignments: dict[int, list[int]] = {i: [] for i in range(len(data_idxs))}
    for i, ln in enumerate(lines):
        if not ln.strip() or i in skip:
            continue
        best_dist = min(abs(i - d) for d in data_idxs)
        tied = [r for r, d in enumerate(data_idxs) if abs(i - d) == best_dist]
        if len(tied) == 1:
            row = tied[0]
        else:
            row = min(tied)  # default: continuation/owner-wrap → row above
            if name_col is not None:
                name_frag = name_col.slice(ln)
                cap_frag = cap_col.slice(ln) if cap_col else ""
                # A tie line is the LEADING name of the row BELOW only if it
                # *starts* a new name: capitalized first char, not a continuation.
                # Continuations stay with the row ABOVE — they start lowercase, are
                # a bare "Expansion"/"Extension", or dangle a closing paren (more
                # ")" than "(", e.g. "...Ahmeyim Phase 1)" tailing the prior row).
                if name_frag and not cap_frag and name_frag[:1].isupper():
                    bal = name_frag.count("(") - name_frag.count(")")
                    has_facility_tag = bool(
                        re.search(r"\(\s*(?:FSRU|FLNG|FSU|FRU)\s*\)", name_frag, re.IGNORECASE))
                    is_continuation = (
                        bal < 0
                        or name_frag.strip().lower() in ("expansion", "extension")
                        # a facility-tagged fragment is a VESSEL trailing its terminal
                        # (e.g. "Italis LNG (FSRU)" under Piombino), not a new name
                        or has_facility_tag
                    )
                    if not is_continuation:
                        row = max(tied)  # leading name-start → row below
        assignments[row].append(i)
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
    rows_with_meta: list[tuple[int, str, dict, float]],
    labels: list[tuple[int, str]],
    subtotals: list[tuple[int, float]],
) -> None:
    """Mutate each row dict's 'country' field via a sequential walk.

    rows_with_meta = list of (data_line_idx, explicit_country_from_cell,
                              row_dict, capacity_mtpa) in row order.
    labels         = list of (label_line_idx, country) in line order.
    subtotals      = list of (subtotal_line_idx, mtpa_value) in line order.
                     Each subtotal applies to the country that's CURRENT at
                     the moment the subtotal line is encountered (GIIGNL
                     typesets the subtotal right under its country label).

    Algorithm: walk events (rows + labels + subtotals) in line order.
    Maintain `current_country`, an expected-capacity budget for that
    country (from its subtotal, if encountered), and a cumulative capacity
    counter. A row without explicit country inherits current_country UNLESS
    doing so would push cumulative beyond the budget — then it goes into
    pending, waiting for the next country label to backfill it.

    This handles three layout variants found in GIIGNL 2026:
    1. Block starts with explicit-country cell on first row (e.g. Sabine
       Pass T1 has USA in cell; T2-T6 inherit).
    2. Block starts with no explicit-country, label appears mid-block
       (label backfills any pending rows from the previous block's "tail").
    3. Country X's block ends and Country Y's rows start BEFORE Y's label
       (the capacity budget detects the boundary: once X's subtotal is
       exceeded, subsequent rows go pending and get backfilled to Y).
    """
    # Tolerance: cumulative may exceed subtotal slightly due to GIIGNL rounding
    # (subtotals are 1-decimal; per-row capacities are 1-decimal too). Tight
    # tolerance is important: with 10% slop the USA block of ~128 MTPA can
    # absorb the first ~13 MTPA of the next country's rows before triggering
    # pending. 2% allows true rounding but catches block boundaries.
    BUDGET_TOLERANCE = 1.02

    events = []
    for data_idx, explicit, row, cap in rows_with_meta:
        events.append((data_idx, 2, ("row", explicit, row, cap)))
    for line_idx, country in labels:
        events.append((line_idx, 0, ("label", country)))
    for line_idx, mtpa in subtotals:
        events.append((line_idx, 1, ("subtotal", mtpa)))
    events.sort(key=lambda e: (e[0], e[1]))

    current_country = ""
    current_budget: float | None = None
    cumulative = 0.0
    pending: list[dict] = []
    subtotal_by_country: dict[str, float] = {}

    for _, _, payload in events:
        kind = payload[0]
        if kind == "label":
            country = payload[1]
            for r in pending:
                r["country"] = country
            pending = []
            current_country = country
            current_budget = None  # reset; next subtotal sets it
            cumulative = 0.0
        elif kind == "subtotal":
            mtpa = payload[1]
            # Subtotal applies to current_country (visually it's right below
            # the label). If we haven't seen a current_country yet, ignore.
            if current_country:
                current_budget = mtpa
                subtotal_by_country[current_country] = mtpa
        elif kind == "row":
            explicit, row, cap = payload[1], payload[2], payload[3]
            if explicit:
                for r in pending:
                    r["country"] = explicit
                pending = []
                current_country = explicit
                current_budget = None  # caller-supplied subtotal unknown for this country yet
                cumulative = cap
                row["country"] = explicit
            elif current_country and current_budget is not None and \
                    cumulative + cap > current_budget * BUDGET_TOLERANCE:
                # This row would push past the current country's subtotal budget,
                # so it probably belongs to the next country. Park it.
                pending.append(row)
                row["country"] = ""
            elif current_country:
                row["country"] = current_country
                cumulative += cap
            else:
                pending.append(row)
                row["country"] = ""
    # Rows still pending at end-of-page have no country.

    # Post-pass: reclaim leading rows misattributed to the previous country
    # using the published per-country subtotals (see _truecup_country_subtotals).
    _truecup_country_subtotals(rows_with_meta, subtotal_by_country)


def _truecup_country_subtotals(
    rows_with_meta: list[tuple[int, str, dict, float]],
    subtotal_by_country: dict[str, float],
    reach_low: float = 0.94,
    reach_high: float = 1.02,
) -> None:
    """Reassign leading misattributed rows using GIIGNL per-country subtotals.

    GIIGNL vertically centers each country label + subtotal within its block, so
    the rows ABOVE the label inherit the *previous* country during the sequential
    walk. The budget guard in _assign_countries_sequential only catches this when
    the previous country's page-local cumulative reaches its subtotal — which
    fails when the previous country's block spilled over from an earlier page (its
    cumulative restarts at 0 on each page, so it never approaches its full-country
    subtotal). Concrete failure: page 36's Brunei block (T1–T5, 7.2 MTPA subtotal)
    has "Brunei" typeset next to T3, so T1/T2 inherited Australia — whose 85.8 MTPA
    block began on page 35, leaving page 36's Australia cumulative far below budget.

    This post-pass repairs it: a country whose assigned rows fall short of its
    published subtotal *tentatively* pulls the contiguous rows directly above it
    (currently tagged to the previous country), then COMMITS the reassignment only
    if doing so brings the run's capacity to within [reach_low, reach_high] of the
    subtotal — i.e. the block is now fully accounted for on this page.

    The commit gate is essential: a country whose own block spans pages (e.g.
    China regasification, 264 MTPA across pages 55–57) has only part of its rows on
    any one page, so its run is "short" of the global subtotal and would otherwise
    greedily pull the *previous* country's rows (US regas terminals) into it. Since
    those pulls never reach the subtotal, the commit gate rejects them and the rows
    stay put. Brunei's pulled rows reach 7.0 ≈ 7.2 → committed. The
    reach band absorbs GIIGNL's independent 1-decimal subtotal rounding.

    Also guarded to fire only on a fully-contained block — preceded AND followed by
    a different country on the same page.
    """
    n = len(rows_with_meta)
    if n == 0:
        return
    caps = [cap for _, _, _, cap in rows_with_meta]
    countries = [row["country"] for _, _, row, _ in rows_with_meta]

    i = 0
    while i < n:
        c = countries[i]
        j = i
        while j < n and countries[j] == c:
            j += 1
        # Run [i, j) is one country. Fire only on a fully-contained block: it
        # must have a known subtotal and be bracketed by other countries on this
        # page (guards against page-straddling blocks that only look "short").
        S = subtotal_by_country.get(c) if c else None
        contained = i > 0 and j < n and countries[i - 1] != c and countries[j] != c
        if S is not None and contained:
            # Only reclaim rows from the SINGLE immediately-preceding country
            # (the centered label makes a block's leading rows inherit exactly the
            # one country above it). Never pull THROUGH that country into an
            # earlier one — that's what turned "China is short of its 173 MTPA
            # subtotal" into swallowing the whole USA + Bangladesh blocks above it.
            prev_country = countries[i - 1]
            cur = sum(caps[i:j])
            pulled = []
            k = i - 1
            while k >= 0 and cur < S * reach_low and countries[k] == prev_country:
                if cur + caps[k] <= S * reach_high:
                    pulled.append(k)
                    cur += caps[k]
                    k -= 1
                else:
                    break
            # Commit only if the block is now complete (rows reach the subtotal).
            # If consuming the preceding country's tail still falls short, the
            # current country spans pages and the rows aren't ours — leave them.
            if pulled and S * reach_low <= cur <= S * reach_high:
                for idx in pulled:
                    rows_with_meta[idx][2]["country"] = c
                    countries[idx] = c
        i = j


def _robust_subtotal_map(
    data_idxs: list[int],
    rows: list[dict],
    subtotals: list[tuple[int, float]],
) -> dict[str, float]:
    """Attribute each subtotal to the country of its NEAREST data row (by line).

    The sequential walk attributes a subtotal to whatever country is "current"
    when the subtotal line is reached — which is wrong when GIIGNL centers the
    label+subtotal mid-block (the subtotal for "Oman" lands while the walk still
    has the previous country current, so Oman's 11.4 MTPA gets misfiled under
    USA). Anchoring instead to the nearest data row, whose country is already
    resolved (often via an embedded explicit label), is robust to the centering.
    Used to feed _reclaim_cross_page; the per-page true-up keeps its own map.
    """
    out: dict[str, float] = {}
    if not data_idxs:
        return out
    for sub_line, mtpa in subtotals:
        nearest = min(range(len(data_idxs)), key=lambda r: abs(data_idxs[r] - sub_line))
        country = rows[nearest]["country"]
        if country:
            out[country] = mtpa
    return out


def _reclaim_cross_page(
    rows: list[dict],
    subtotal_by_country: dict[str, float],
    reach_low: float = 0.94,
    reach_high: float = 1.02,
    max_iter: int = 8,
) -> None:
    """Cross-page sibling of _truecup_country_subtotals (operates on a whole section).

    The per-page true-up cannot repair a country whose block spans pages — its
    page-local cumulative never reaches the full-country subtotal. Run on the
    section's rows concatenated in report order, a page-spanning country (Qatar
    liquefaction, pages 34-35, 77.0 MTPA) reaches its subtotal and reclaims the
    leading rows the sequential walk stranded on the previous country (N(1)/N(2)
    inherited "Oman" because the "Qatar" label is centered next to N(3) T6).

    For each contained, short country run, reclaim contiguous rows from the SINGLE
    immediately-preceding country (nearest first), choosing the pull count whose
    running total lands CLOSEST to the published subtotal, then commit only if that
    best total is within [reach_low, reach_high] of the subtotal. Iterated to a
    fixpoint because reclaims chain: Qatar must vacate N(1)/N(2) from Oman's run
    before Oman's run is short enough to reclaim Oman T1 from USA. Convergence holds
    — a run that has reached its subtotal is no longer short, so no row is pulled
    twice.

    Closest-to-subtotal (not merely "within band") matters: a naive greedy that
    stops anywhere under reach_high tacks an extra small row onto the block — e.g.
    Indonesia (24.9 MTPA) needs Bontang E/F/G (→25.0) but a greedy pull would also
    swallow Canada's Tilbury LNG (0.3, →25.3, still under the 2% ceiling).

    Same two guards as the per-page pass: never pull THROUGH more than one
    preceding country, and commit only on reaching the published subtotal — so a
    genuinely page-straddling country like China regas (whose global run already
    sums to its subtotal) is never short and never over-pulls the block above it.
    """
    n = len(rows)
    if n == 0:
        return
    caps = [_parse_float(r["capacity_mtpa"]) or 0.0 for r in rows]
    for _ in range(max_iter):
        countries = [r["country"] for r in rows]
        changed = False
        i = 0
        while i < n:
            c = countries[i]
            j = i
            while j < n and countries[j] == c:
                j += 1
            S = subtotal_by_country.get(c) if c else None
            contained = i > 0 and j < n and countries[i - 1] != c and countries[j] != c
            if S is not None and contained:
                base = sum(caps[i:j])
                if base < S * reach_low:  # short → try to reclaim leading rows
                    prev_country = countries[i - 1]
                    cur = base
                    best_m, best_dist, best_cur = 0, abs(base - S), base
                    m, k = 0, i - 1
                    while k >= 0 and countries[k] == prev_country:
                        cur += caps[k]
                        m += 1
                        if abs(cur - S) < best_dist:
                            best_m, best_dist, best_cur = m, abs(cur - S), cur
                        if cur >= S:  # past the subtotal — distance only grows
                            break
                        k -= 1
                    if best_m >= 1 and S * reach_low <= best_cur <= S * reach_high:
                        for off in range(best_m):
                            idx = i - 1 - off
                            rows[idx]["country"] = c
                            countries[idx] = c
                        changed = True
            i = j
        if not changed:
            break


# Multi-word country names GIIGNL typesets across stacked lines, where a leading
# fragment can land ON a data row (becoming that row's "explicit country") while
# the remainder is a clean label — so the merged_labels stitch in _classify_lines
# misses it and the block fragments into two ADJACENT country runs (e.g. "South"
# on the Jeju row + "Korea" as a label on the rows below). Keyed by the
# (lowercased) raw fragment pair → the canonical full name.
_SPLIT_COUNTRY_JOINS = {
    ("south", "korea"): "South Korea",
    ("equatorial", "guinea"): "Equatorial Guinea",
    ("papua", "new guinea"): "Papua New Guinea",
    ("papua new", "guinea"): "Papua New Guinea",
    ("trinidad &", "tobago"): "Trinidad and Tobago",
    ("trinidad and", "tobago"): "Trinidad and Tobago",
    ("trinidad", "tobago"): "Trinidad and Tobago",
    ("mauritania", "senegal"): "Mauritania",  # GEM files GTA under Mauritania
    ("mauritania/", "senegal"): "Mauritania",
}


def _norm_frag(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().rstrip("/").strip().lower())


def _country_runs(rows: list[dict]) -> list[tuple[int, int, str]]:
    """Contiguous (start, end, country) runs over rows in report order."""
    runs: list[tuple[int, int, str]] = []
    i, n = 0, len(rows)
    while i < n:
        c = rows[i]["country"]
        j = i
        while j < n and rows[j]["country"] == c:
            j += 1
        runs.append((i, j, c))
        i = j
    return runs


def _merge_split_country_runs(rows: list[dict]) -> dict[str, str]:
    """Re-stitch two adjacent country runs that are fragments of one multi-word
    country (e.g. 'South' + 'Korea' → 'South Korea').

    Returns {old_raw_country: canonical_full_name} so the caller can re-key the
    per-country subtotal map (the subtotal was attributed to one of the
    fragments). Mutates each affected row's 'country'. Conservative: fires only
    on the explicit whitelist of known split country names, so two genuinely
    distinct adjacent countries are never merged.
    """
    renames: dict[str, str] = {}
    runs = _country_runs(rows)
    for r in range(len(runs) - 1):
        a_s, a_e, a_c = runs[r]
        b_s, b_e, b_c = runs[r + 1]
        if not a_c or not b_c:
            continue
        full = _SPLIT_COUNTRY_JOINS.get((_norm_frag(a_c), _norm_frag(b_c)))
        if not full:
            continue
        for k in range(a_s, b_e):
            rows[k]["country"] = full
        if a_c != full:
            renames[a_c] = full
        if b_c != full:
            renames[b_c] = full
    return renames


# Narrow, edition-specific site→country fallbacks for the few LIQUEFACTION blocks
# whose country label is so badly interleaved with the multi-line data row that
# the structural walk can't resolve it: GIIGNL stacks "Equatorial"/"Guinea"
# ABOVE and BELOW the single EG LNG row, and "Mauritania/"/"Senegal" around the
# multi-line Tortue/Gimi FLNG row, so neither the label stitcher nor the
# subtotal reclaim can recover them. Each maps a distinctive site-name substring
# to the country GEM files the terminal under (GEM keeps GTA under "Mauritania").
# Auditable, exact, and guarded by distinctive substrings — re-verify per edition.
_SITE_COUNTRY_OVERRIDES = [
    ("eg lng", "Equatorial Guinea"),
    ("png lng", "Papua New Guinea"),
    ("tortue", "Mauritania"),
]


def _apply_site_country_overrides(rows: list[dict]) -> None:
    for r in rows:
        site = (r.get("site_name") or "").lower()
        for sub, country in _SITE_COUNTRY_OVERRIDES:
            if sub in site:
                r["country"] = country
                break


def _reassign_country_islands(
    rows: list[dict], subtotal_by_country: dict[str, float],
    reach_low: float = 0.94, reach_high: float = 1.02,
) -> None:
    """Reassign a country-A run sandwiched between two country-B runs (B…A…B)
    back to B when A's published subtotal is ALREADY satisfied by A's OTHER rows
    — i.e. the island is extra capacity the sequential walk's leftover-budget
    greedily absorbed from B.

    Concrete case: Japan's small Hachinohe/Hatsukaichi/Hibiki rows (3.9 MTPA) get
    tagged Indonesia between two Japan runs because Indonesia's centered label
    splits its block, leaving ~7.9 MTPA of unused Indonesia budget that the next
    small rows "fit" into. Indonesia's real 11.5 MTPA subtotal is already met by
    its six genuine rows, so the island is reassigned back to Japan. The
    subtotal-satisfied guard keeps a legitimate island from being moved.
    """
    n = len(rows)
    caps = [_parse_float(r["capacity_mtpa"]) or 0.0 for r in rows]
    tot: dict[str, float] = {}
    for idx in range(n):
        tot[rows[idx]["country"]] = tot.get(rows[idx]["country"], 0.0) + caps[idx]
    for i, j, c in _country_runs(rows):
        if not c or i == 0 or j == n:
            continue
        b_prev, b_next = rows[i - 1]["country"], rows[j]["country"]
        S = subtotal_by_country.get(c)
        if not (b_prev and b_prev == b_next and b_prev != c and S):
            continue
        island = sum(caps[i:j])
        others = tot[c] - island
        if others >= S * reach_low and (others + island) > S * reach_high:
            for k in range(i, j):
                rows[k]["country"] = b_prev


# ---------------------------------------------------------------------------
# Page-level extraction
# ---------------------------------------------------------------------------

def _extract_liquefaction_page(
    page_text: str, page_num: int,
) -> tuple[list[dict], float]:
    columns, hdr_idx = _find_columns_by_header(page_text, LIQ_HEADER_KEYWORDS)
    if hdr_idx < 0:
        return [], 0.0, {}
    lines = page_text.splitlines()
    body_lines = lines[hdr_idx + 1:]
    cap_col = "(MTPA)"

    data_idxs, labels, skip, subtotals = _classify_lines(body_lines, columns, cap_col)
    assignments = _partition_lines_by_data(body_lines, data_idxs, skip, columns, cap_col)

    rows: list[dict] = []
    rows_with_meta: list[tuple[int, str, dict, float]] = []
    page_cap_sum = 0.0
    for row_idx, data_idx in enumerate(data_idxs):
        merged, _frags = _merge_lines_into_cells(body_lines, assignments[row_idx], columns)
        project_raw = _clean_text(merged.get("Project", "").strip())
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
            "status": _status_from_hint(status_hint),
        }
        rows.append(row)
        rows_with_meta.append((data_idx, explicit_country, row, cap_mtpa))
    _assign_countries_sequential(rows_with_meta, labels, subtotals)
    return rows, page_cap_sum, _robust_subtotal_map(data_idxs, rows, subtotals)


def _extract_regasification_page(
    page_text: str, page_num: int,
) -> tuple[list[dict], float]:
    columns, hdr_idx = _find_columns_by_header(page_text, REGAS_HEADER_KEYWORDS)
    if hdr_idx < 0:
        return [], 0.0, {}
    lines = page_text.splitlines()
    body_lines = lines[hdr_idx + 1:]
    cap_col = "(MTPA)"

    data_idxs, labels, skip, subtotals = _classify_lines(body_lines, columns, cap_col)
    assignments = _partition_lines_by_data(body_lines, data_idxs, skip, columns, cap_col)

    rows: list[dict] = []
    rows_with_meta: list[tuple[int, str, dict, float]] = []
    page_cap_sum = 0.0
    for row_idx, data_idx in enumerate(data_idxs):
        merged, frags = _merge_lines_into_cells(body_lines, assignments[row_idx], columns)
        site_fragments = [_clean_text(s) for s in frags.get("Site", [])]
        site_raw = " ".join(site_fragments).strip()
        if not site_raw:
            continue
        # Use the fragment list to separate site name from vessel name.
        # The site name is typically the first fragment(s); the vessel name
        # appears in a later fragment containing "(FSRU)" / "(FLNG)" etc.
        vessel_name = ""
        site_parts: list[str] = []
        tagged: list[str] = []  # facility-tagged fragments, tag stripped
        for frag in site_fragments:
            m_tag = re.search(r"\(\s*(FSRU|FLNG|FSU|FRU)\s*\)", frag, re.IGNORECASE)
            if m_tag:
                # Facility-tagged fragment — usually the vessel name. Strip the tag.
                vessel_clean = re.sub(
                    r"\s*\(\s*(?:FSRU|FLNG|FSU|FRU)\s*\)\s*", " ",
                    frag, flags=re.IGNORECASE,
                ).strip()
                tagged.append(vessel_clean)
                vessel_name = vessel_clean
            else:
                site_parts.append(frag)
        # When GIIGNL tags the SITE itself too (e.g. "Ravenna (FSRU)" as the site
        # label plus "BW Singapore (FSRU)" as the vessel), every fragment is tagged
        # and site_parts is empty. Treat the first tagged fragment as the site and
        # the last as the vessel rather than falling back to the joined raw string
        # ("Ravenna (FSRU) BW Singapore (FSRU)"). Only fires for 2+ tagged frags, so
        # the common single-vessel-fragment case is untouched.
        if not site_parts and len(tagged) >= 2:
            # Drop a dangling conjunction left by a dual-vessel row
            # ("Tenaga Empat (FSU) and Tenaga Satu (FSU)" -> site "Tenaga Empat").
            site_parts = [re.sub(r"\s+(?:and|&)\s*$", "", tagged[0], flags=re.IGNORECASE).strip()]
            vessel_name = tagged[-1]
        site_name = " ".join(site_parts).strip() or site_raw

        # A status parenthetical on a regas site ("... (Mothballed)") isn't a
        # facility tag (those were peeled above), so it survives in site_name —
        # peel it the same way the liq path does so the row carries a status.
        regas_status = ""
        m_st = _STATUS_HINT_RE.search(site_name)
        if m_st:
            st = _status_from_hint(m_st.group(1))
            if st:
                regas_status = st
                site_name = site_name[: m_st.start()].rstrip()

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
            "status": regas_status,
        }
        rows.append(row)
        rows_with_meta.append((data_idx, explicit_country, row, cap_mtpa))
    _assign_countries_sequential(rows_with_meta, labels, subtotals)
    return rows, page_cap_sum, _robust_subtotal_map(data_idxs, rows, subtotals)


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
        liq_rows: list[dict] = []
        liq_subtotals: dict[str, float] = {}
        for offset, page_num in enumerate(range(liq_pages[0], liq_pages[-1] + 1)):
            if page_num not in liq_pages:
                continue
            if offset >= len(page_texts):
                continue
            page_rows, cap_sum, page_subs = _extract_liquefaction_page(page_texts[offset], page_num)
            liq_rows.extend(page_rows)
            liq_subtotals.update(page_subs)
            liq_total += cap_sum
            print(f"    page {page_num}: {len(page_rows)} liq rows, {cap_sum:.1f} MTPA")
        # Re-stitch split multi-word country labels (re-key their subtotals),
        # reassign greedily-absorbed country islands, then run the cross-page
        # leading-row reclaim (Qatar 77.0 MTPA spans pages 34-35, etc.).
        for _old, _new in _merge_split_country_runs(liq_rows).items():
            if _old in liq_subtotals:
                liq_subtotals[_new] = liq_subtotals.pop(_old)
        _reassign_country_islands(liq_rows, liq_subtotals)
        _reclaim_cross_page(liq_rows, liq_subtotals)
        all_rows.extend(liq_rows)

    if regas_pages:
        full_text = _pdftotext(pdf_path, regas_pages[0], regas_pages[-1])
        page_texts = full_text.split("\x0c")
        regas_rows: list[dict] = []
        regas_subtotals: dict[str, float] = {}
        for offset, page_num in enumerate(range(regas_pages[0], regas_pages[-1] + 1)):
            if page_num not in regas_pages:
                continue
            if offset >= len(page_texts):
                continue
            page_rows, cap_sum, page_subs = _extract_regasification_page(page_texts[offset], page_num)
            regas_rows.extend(page_rows)
            regas_subtotals.update(page_subs)
            regas_total += cap_sum
            print(f"    page {page_num}: {len(page_rows)} regas rows, {cap_sum:.1f} MTPA")
        for _old, _new in _merge_split_country_runs(regas_rows).items():
            if _old in regas_subtotals:
                regas_subtotals[_new] = regas_subtotals.pop(_old)
        _reassign_country_islands(regas_rows, regas_subtotals)
        _reclaim_cross_page(regas_rows, regas_subtotals)
        all_rows.extend(regas_rows)

    # Final narrow site→country fallbacks for blocks the structural walk can't
    # resolve (EG LNG, PNG LNG, Tortue — see _SITE_COUNTRY_OVERRIDES).
    _apply_site_country_overrides(all_rows)

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
