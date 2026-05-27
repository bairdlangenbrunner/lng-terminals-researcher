"""
Final pass over the batch xlsx to catch formula errors before present_files.

Ported from the carrier project. The xlsx we build doesn't intentionally use
formulas, but openpyxl handles formula evaluation differently than Excel, and
malformed cell values can surface as #VALUE! / #REF! / #NAME? errors when the
file is opened. Catching these here saves the user from opening a broken xlsx.

The check:
  - Walks every cell in every sheet
  - Reports cells whose value starts with "#" and looks like an Excel error
    ("#VALUE!", "#REF!", "#NAME?", "#DIV/0!", "#NULL!", "#N/A", "#NUM!")
  - Also reports cells whose value starts with "=" (formula leaked through)
    since we don't intentionally write formulas

Usage:
    python recalc.py ../batches/batch_<date>.xlsx
    # Exits 0 if clean, 1 if errors found
"""
import argparse
import sys
from pathlib import Path

try:
    import openpyxl
except ImportError:
    sys.exit("ERROR: openpyxl not installed. Run: pip install --break-system-packages openpyxl")


EXCEL_ERRORS = ("#VALUE!", "#REF!", "#NAME?", "#DIV/0!", "#NULL!", "#N/A", "#NUM!")


def check(xlsx_path):
    """Walk xlsx; return (errors, formula_leaks) lists of (sheet, cell, value) tuples."""
    wb = openpyxl.load_workbook(xlsx_path, data_only=False)
    errors = []
    formula_leaks = []
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                v = cell.value
                if v is None:
                    continue
                if isinstance(v, str):
                    if v in EXCEL_ERRORS:
                        errors.append((ws.title, cell.coordinate, v))
                    elif v.startswith("=") and len(v) > 1:
                        formula_leaks.append((ws.title, cell.coordinate, v))
    return errors, formula_leaks


def main():
    p = argparse.ArgumentParser()
    p.add_argument("xlsx_path")
    args = p.parse_args()

    if not Path(args.xlsx_path).exists():
        sys.exit(f"ERROR: {args.xlsx_path} not found")

    errors, formula_leaks = check(args.xlsx_path)

    if not errors and not formula_leaks:
        print(f"  OK: no formula errors found in {args.xlsx_path}")
        sys.exit(0)

    if errors:
        print(f"\n  FORMULA ERRORS ({len(errors)}):")
        for sheet, cell, val in errors[:50]:
            print(f"    {sheet}!{cell}: {val}")
        if len(errors) > 50:
            print(f"    ... and {len(errors) - 50} more")
    if formula_leaks:
        print(f"\n  FORMULA LEAKS ({len(formula_leaks)}) — cells starting with '=':")
        for sheet, cell, val in formula_leaks[:50]:
            preview = val[:60] + ("..." if len(val) > 60 else "")
            print(f"    {sheet}!{cell}: {preview}")
        if len(formula_leaks) > 50:
            print(f"    ... and {len(formula_leaks) - 50} more")

    sys.exit(1)


if __name__ == "__main__":
    main()
