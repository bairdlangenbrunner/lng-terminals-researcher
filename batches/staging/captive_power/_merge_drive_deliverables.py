"""Merge the regional captive-power Drive deliverables into two combined workbooks.

Usage: python _merge_drive_deliverables.py <captive_out.xlsx> <batch_out.xlsx>
from a working dir holding a src/ with the downloaded regional files (names in
CAPTIVE_FILES / BATCH_FILES below). Download the CURRENT Drive copies first —
Natalia edits the "Captive PPs_*" files in place (e.g. the 2026-08-03 Toscana
move to EU-Excluded), so local repo copies are stale by definition. Shared-drive
download/upload needs raw `gws drive files get/create` with
`"supportsAllDrives": true` (the `+upload` helper 404s on shared drives).

A) Captive PPs (Natalia-format): copy every tab verbatim (tabs already carry
   region prefixes) from the newest file per region.
B) lng_terminals_batch: concatenate same-named sheets across regions, rebuild
   the README with aggregated stats.

Cell styles (confidence fills), hyperlinks, column widths, freeze panes and
merged cells are preserved. First run 2026-08-03: `Captive PPs_All
Regions_08.03.2026.xlsx` (14 tabs) +
`lng_terminals_batch_20260803_0929_ET_all-regions-captive_update.xlsx`.
"""
import re
import sys
from copy import copy

import openpyxl
from openpyxl.utils import get_column_letter

SRC = "src"
OUT_CAPTIVE = sys.argv[1]
OUT_BATCH = sys.argv[2]

CAPTIVE_FILES = [
    "captive_europe_americas_updated_0803.xlsx",  # EU / Russia / Americas (Natalia's consolidated 08.03)
    "captive_asia.xlsx",
    "captive_middle_east_gulf.xlsx",
    "captive_africa.xlsx",
    "captive_oceania.xlsx",
]

BATCH_FILES = [  # (file, region label for logging)
    ("batch_americas.xlsx", "Americas"),
    ("batch_europe.xlsx", "Europe"),
    ("batch_asia.xlsx", "Asia"),
    ("batch_middle_east_gulf.xlsx", "Middle East-Gulf"),
    ("batch_africa.xlsx", "Africa"),
    ("batch_oceania.xlsx", "Oceania"),
]


def copy_cell(src_cell, dst_cell):
    dst_cell.value = src_cell.value
    if src_cell.has_style:
        dst_cell.font = copy(src_cell.font)
        dst_cell.fill = copy(src_cell.fill)
        dst_cell.border = copy(src_cell.border)
        dst_cell.alignment = copy(src_cell.alignment)
        dst_cell.protection = copy(src_cell.protection)
        dst_cell.number_format = src_cell.number_format
    if src_cell.hyperlink is not None:
        dst_cell.hyperlink = copy(src_cell.hyperlink)


def copy_sheet_verbatim(src_ws, dst_wb):
    dst_ws = dst_wb.create_sheet(title=src_ws.title)
    for row in src_ws.iter_rows():
        for c in row:
            copy_cell(c, dst_ws.cell(row=c.row, column=c.column))
    for col, dim in src_ws.column_dimensions.items():
        dst_ws.column_dimensions[col].width = dim.width
    for rng in src_ws.merged_cells.ranges:
        dst_ws.merge_cells(str(rng))
    dst_ws.freeze_panes = src_ws.freeze_panes
    if src_ws.auto_filter.ref:
        dst_ws.auto_filter.ref = src_ws.auto_filter.ref
    return dst_ws


# ---------- A) Captive PPs merge ----------
cap_out = openpyxl.Workbook()
cap_out.remove(cap_out.active)
for f in CAPTIVE_FILES:
    wb = openpyxl.load_workbook(f"{SRC}/{f}")
    for ws in wb.worksheets:
        copy_sheet_verbatim(ws, cap_out)
        print(f"captive: [{ws.title}] <- {f} ({ws.max_row - 1} data rows)")
    wb.close()
cap_out.save(OUT_CAPTIVE)
print(f"saved {OUT_CAPTIVE} ({len(cap_out.sheetnames)} tabs)\n")

# ---------- B) lng_terminals_batch merge ----------
wbs = [(openpyxl.load_workbook(f"{SRC}/{f}"), region) for f, region in BATCH_FILES]
first_wb = wbs[0][0]
sheet_names = [s for s in first_wb.sheetnames if s != "README"]

out = openpyxl.Workbook()
out.remove(out.active)

# README: use the first file's as template, aggregate the region-specific rows.
readme_src = first_wb["README"]
readme = copy_sheet_verbatim(readme_src, out)

count_rows = {}  # label -> summed count, for rows like "  updates | 148"
region_scope = {"checked": 0, "changes": [], "verified": []}
for wb, region in wbs:
    ws = wb["README"]
    for r in range(1, ws.max_row + 1):
        a, b = ws.cell(r, 1).value, ws.cell(r, 2).value
        if a is None:
            continue
        a_str = str(a)
        if isinstance(b, (int, float)) and a_str.startswith("  "):
            count_rows.setdefault(r, 0)
            count_rows[r] += int(b)
        m = re.match(r"Countries checked in this region \((\d+)\)", a_str)
        if m:
            region_scope["checked"] += int(m.group(1))
        m = re.match(r"Changes found \((\d+)\)", a_str)
        if m and b:
            region_scope["changes"] += [c.strip() for c in str(b).split(",") if c.strip()]
        m = re.match(r"Verified, no changes \((\d+)\)", a_str)
        if m and b:
            region_scope["verified"] += [c.strip() for c in str(b).split(",") if c.strip()]

for r, total in count_rows.items():
    readme.cell(r, 2).value = total
for r in range(1, readme.max_row + 1):
    a = readme.cell(r, 1).value
    if a is None:
        continue
    a_str = str(a)
    if re.match(r"Countries checked in this region", a_str):
        readme.cell(r, 1).value = (
            f"Countries checked, all regions ({region_scope['checked']})"
        )
    elif re.match(r"Changes found", a_str):
        # a country can appear once per region; keep order, drop dups
        seen = list(dict.fromkeys(region_scope["changes"]))
        readme.cell(r, 1).value = f"Changes found ({len(seen)})"
        readme.cell(r, 2).value = ", ".join(seen)
    elif re.match(r"Verified, no changes", a_str):
        # a "verified" country that has changes in another region stays in changes only
        changed = set(region_scope["changes"])
        seen = [c for c in dict.fromkeys(region_scope["verified"]) if c not in changed]
        readme.cell(r, 1).value = f"Verified, no changes ({len(seen)})"
        readme.cell(r, 2).value = ", ".join(seen)

# Data sheets: header from first file, then all regions' data rows.
for name in sheet_names:
    src0 = first_wb[name]
    hdr = [c.value for c in src0[1]]
    ncols = max(i + 1 for i, v in enumerate(hdr) if v is not None)
    dst = out.create_sheet(title=name)
    for c in src0[1][:ncols]:
        copy_cell(c, dst.cell(row=1, column=c.column))
    out_r = 1
    for wb, region in wbs:
        ws = wb[name]
        this_hdr = [c.value for c in ws[1]][:ncols]
        assert this_hdr == hdr[:ncols], f"{name} header mismatch in {region}"
        n = 0
        for row in ws.iter_rows(min_row=2, max_col=ncols):
            if all(c.value is None for c in row):
                continue
            out_r += 1
            n += 1
            for c in row:
                copy_cell(c, dst.cell(row=out_r, column=c.column))
        print(f"batch: [{name}] += {n} rows from {region}")
    for col_idx in range(1, ncols + 1):
        letter = get_column_letter(col_idx)
        dim = src0.column_dimensions.get(letter)
        if dim is not None and dim.width:
            dst.column_dimensions[letter].width = dim.width
    dst.freeze_panes = src0.freeze_panes
    if src0.auto_filter.ref:
        dst.auto_filter.ref = f"A1:{get_column_letter(ncols)}{out_r}"

out.save(OUT_BATCH)
print(f"saved {OUT_BATCH} ({len(out.sheetnames)} tabs)")
for wb, _ in wbs:
    wb.close()
