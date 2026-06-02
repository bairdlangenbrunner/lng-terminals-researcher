#!/usr/bin/env python3
"""Parse the GIIGNL Annual Report's "FSRU FLEET AT THE END OF <year>" table.

WHY THIS IS A SEPARATE EXTRACTOR (not part of giignl_extract.py):
The country regasification/liquefaction tables (giignl_extract.py) are organized by
TERMINAL. A handful of FSRUs are deployed at terminals GIIGNL does NOT carry in those
country tables (small / power-barge / non-member sites — e.g. Tema LNG, Ghana, vessel
"Torman"), so they never surface in the three-way terminal diff. GIIGNL DOES list every
deployed FSRU in a dedicated fleet table (2026 edition: PDF p.43, "FSRU FLEET AT THE END
OF 2025", 54 units + a 4-unit orderbook). Ingesting it gives a vessel-level cross-check
against GEM's floating-vessel fields that the terminal diff structurally can't provide.

The fleet table is a clean, fixed-column layout (unlike the vertically-centered country
tables), so this parser is simple column-position slicing + location-wrap merging — it is
NOT the edge-case-hardened machinery in giignl_extract.py.

Columns (2026 edition, character offsets from `pdftotext -layout`):
    Built/Converted[0:16] | Vessel Name[16:72] | Storage m3[72:88] | CCS[88:100] |
    Send-out MTPA[100:120] | Owner[120:145] | Builder[145:168] | Location[168:]

`Location` is the DEPLOYMENT ("Site, Country"), or "LNGC" (laid-up / spot, not at a
terminal), or "TBC / ..." (unassigned). It wraps onto the line(s) above/below the data
line (GIIGNL vertically-centers it), so continuation lines — blank before col 168, text
at/after it — are merged into the nearest data row.

Usage:
    python giignl_fsru_fleet.py <giignl_report.pdf> --output giignl_fsru_fleet.json
    python giignl_fsru_fleet.py <giignl_report.pdf> --page 43   # override page
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# Column start offsets (2026 edition). If a future edition shifts these, re-derive
# from the header line ("Converted ... Vessel Name ... Capacity (m3) ... CCS* ...
# Capacity (MTPA) ... Owner ... Builder ... Location") — see _derive_offsets.
_COLS = {
    "converted": 0,
    "vessel": 16,
    "storage": 72,
    "ccs": 88,
    "sendout": 100,
    "owner": 120,
    "builder": 145,
    "location": 168,
}
_COL_ORDER = ["converted", "vessel", "storage", "ccs", "sendout",
              "owner", "builder", "location"]

# A data row begins with a 4-digit build year, optionally "/converted-year".
_YEAR_RE = re.compile(r"^\s*(\d{4})(?:/(\d{4}))?\s*$")
# Vessel "(ex Name)" former-name parenthetical(s) — pulled out as ex_names.
_EX_RE = re.compile(r"\(ex\s+([^)]+)\)", re.IGNORECASE)
_CCS_VALUES = {"moss", "membrane", "other", "aluminium", "aluminum"}
_FLEET_HEADER_RE = re.compile(r"FSRU\s+FLEET\s+AT\s+THE\s+END\s+OF\s+(\d{4})", re.I)
_ORDERBOOK_RE = re.compile(r"FSRU\s+ORDERBOOK", re.IGNORECASE)


def _pdftotext_page(pdf_path: str, page: int) -> list[str]:
    out = subprocess.run(
        ["pdftotext", "-layout", "-f", str(page), "-l", str(page), pdf_path, "-"],
        capture_output=True, text=True, check=True,
    ).stdout
    return out.split("\n")


def _find_fleet_page(pdf_path: str, hint: int = 43, span: int = 6) -> tuple[int, int]:
    """Locate the fleet page + its edition year by scanning near `hint`. Returns
    (page, year). Falls back to (hint, 0) if the header isn't found."""
    for p in [hint] + [hint + d for d in range(-span, span + 1) if d]:
        if p < 1:
            continue
        try:
            text = "\n".join(_pdftotext_page(pdf_path, p))
        except subprocess.CalledProcessError:
            continue
        m = _FLEET_HEADER_RE.search(text)
        if m:
            return p, int(m.group(1))
    return hint, 0


def _slice(line: str, col: str) -> str:
    start = _COLS[col]
    idx = _COL_ORDER.index(col)
    end = _COLS[_COL_ORDER[idx + 1]] if idx + 1 < len(_COL_ORDER) else len(line)
    return line[start:end].strip() if start < len(line) else ""


def _is_data_row(line: str) -> bool:
    return bool(_YEAR_RE.match(line[:_COLS["vessel"]])) and bool(
        line[_COLS["vessel"]:_COLS["storage"]].strip())


def _is_location_continuation(line: str) -> bool:
    """A line carrying ONLY location-column text (blank everywhere left of col 168)
    — a wrapped second line of a 'Site, Country' deployment."""
    return bool(line[_COLS["location"]:].strip()) and not line[:_COLS["location"]].strip()


def _parse_location(loc: str) -> dict:
    """Split a deployment string into site + country + status.
    'Tema LNG, Ghana' -> site='Tema LNG', country='Ghana', status='deployed'.
    'LNGC' -> spot/laid-up (no terminal). 'TBC / ...' -> unassigned."""
    loc = re.sub(r"\s+", " ", (loc or "").strip())
    if not loc:
        return {"site": "", "country": "", "status": "unknown", "raw": loc}
    if loc.upper() == "LNGC":
        return {"site": "", "country": "", "status": "spot_or_laidup", "raw": loc}
    if loc.upper().startswith("TBC"):
        return {"site": "", "country": "", "status": "unassigned", "raw": loc}
    # "Site, Country" — country is the last comma-separated piece.
    parts = [p.strip() for p in loc.split(",") if p.strip()]
    if len(parts) >= 2:
        return {"site": ", ".join(parts[:-1]), "country": parts[-1],
                "status": "deployed", "raw": loc}
    return {"site": parts[0], "country": "", "status": "deployed", "raw": loc}


def _clean_vessel(raw: str) -> tuple[str, list[str]]:
    """Return (primary_name, [ex_names]) from a vessel cell like
    'Nusantara Regas Satu (ex Khannur)'."""
    ex_names = [e.strip() for e in _EX_RE.findall(raw)]
    primary = _EX_RE.sub("", raw).strip()
    primary = re.sub(r"\s+", " ", primary)
    return primary, ex_names


def parse_fleet(pdf_path: str, page: int | None = None) -> dict:
    """Parse the FSRU fleet table. Returns {edition_year, page, vessels:[...],
    orderbook:[...]}."""
    if page is None:
        page, year = _find_fleet_page(pdf_path)
    else:
        text = "\n".join(_pdftotext_page(pdf_path, page))
        m = _FLEET_HEADER_RE.search(text)
        year = int(m.group(1)) if m else 0

    # The table can spill onto the next page; read this page + the next.
    lines = _pdftotext_page(pdf_path, page) + _pdftotext_page(pdf_path, page + 1)

    # Split at the orderbook boundary — orderbook rows have a different column
    # meaning (no deployment Location) and are future vessels, kept separately.
    ob_idx = next((i for i, l in enumerate(lines) if _ORDERBOOK_RE.search(l)), len(lines))
    fleet_lines, ob_lines = lines[:ob_idx], lines[ob_idx:]

    data_idxs = [i for i, l in enumerate(fleet_lines) if _is_data_row(l)]
    data_idx_set = set(data_idxs)

    # Location wrap: GIIGNL vertically-centers a "Site, Country" so a long one
    # (e.g. "Manzanillo, Dominican Republic") splits onto the line ABOVE and BELOW
    # the value line, leaving the data line's own location cell EMPTY. Only such
    # empty-cell rows need wrap-gathering; assign each continuation line to exactly
    # ONE nearest empty-cell row so a neighbor's own location isn't fused in.
    own_loc = {di: fleet_lines[di][_COLS["location"]:].strip() for di in data_idxs}
    need_wrap = [di for di in data_idxs if not own_loc[di]]
    wrap_parts = {di: [] for di in need_wrap}
    if need_wrap:
        for j, lj in enumerate(fleet_lines):
            if j in data_idx_set or not _is_location_continuation(lj):
                continue
            seg = lj[_COLS["location"]:].strip()
            if not seg:
                continue
            nearest = min(need_wrap, key=lambda di: abs(j - di))
            # A real location wrap sits immediately above/below its value line; a
            # far-away far-right fragment is the running page header ("LNG
            # Shipping") bleeding in, not a location — require adjacency.
            if abs(j - nearest) <= 2:
                wrap_parts[nearest].append((j, seg))

    vessels = []
    for n, di in enumerate(data_idxs):
        line = fleet_lines[di]
        ym = _YEAR_RE.match(line[:_COLS["vessel"]])
        built = int(ym.group(1)) if ym else None
        converted = int(ym.group(2)) if ym and ym.group(2) else None
        vessel_raw = _slice(line, "vessel")
        primary, ex_names = _clean_vessel(vessel_raw)

        if own_loc[di]:
            location_raw = own_loc[di]
        else:
            location_raw = " ".join(seg for _, seg in sorted(wrap_parts.get(di, [])))

        ccs = _slice(line, "ccs")
        sendout = _slice(line, "sendout").replace(",", "")
        try:
            sendout_mtpa = float(sendout) if sendout else None
        except ValueError:
            sendout_mtpa = None
        storage = _slice(line, "storage").replace(",", "")
        try:
            storage_m3 = int(storage) if storage else None
        except ValueError:
            storage_m3 = None

        vessels.append({
            "built_year": built,
            "converted_year": converted,
            "vessel_name": primary,
            "ex_names": ex_names,
            "storage_m3": storage_m3,
            "ccs": ccs if ccs.lower() in _CCS_VALUES else ccs,
            "sendout_mtpa": sendout_mtpa,
            "vessel_owner": _slice(line, "owner"),
            "builder": _slice(line, "builder"),
            **{f"location_{k}": v for k, v in _parse_location(location_raw).items()},
        })

    # Orderbook (future deliveries) — lighter parse; no deployment location.
    orderbook = []
    for l in ob_lines:
        if not _is_data_row(l):
            continue
        ym = _YEAR_RE.match(l[:_COLS["vessel"]])
        primary, ex_names = _clean_vessel(_slice(l, "vessel"))
        orderbook.append({
            "expected_year": int(ym.group(1)) if ym else None,
            "vessel_name": primary,
            "storage_m3": (lambda s: int(s) if s.isdigit() else None)(
                _slice(l, "storage").replace(",", "")),
            "ccs": _slice(l, "ccs"),
            "vessel_owner": _slice(l, "sendout"),  # orderbook shifts owner left a col
            "builder": _slice(l, "owner"),
        })

    return {
        "edition_year": year,
        "page": page,
        "fleet_count": len(vessels),
        "vessels": vessels,
        "orderbook": orderbook,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Parse the GIIGNL FSRU fleet table.")
    ap.add_argument("pdf", help="Path to the GIIGNL annual report PDF.")
    ap.add_argument("--output", default="giignl_fsru_fleet.json")
    ap.add_argument("--page", type=int, default=None,
                    help="Override the fleet-table page (auto-detected near p.43).")
    args = ap.parse_args(argv)

    if not Path(args.pdf).exists():
        print(f"ERROR: {args.pdf} not found", file=sys.stderr)
        return 2
    result = parse_fleet(args.pdf, page=args.page)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"  Parsed {result['fleet_count']} deployed FSRUs + "
          f"{len(result['orderbook'])} orderbook units "
          f"(edition {result['edition_year']}, PDF p.{result['page']})")
    print(f"  Saved fleet to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
