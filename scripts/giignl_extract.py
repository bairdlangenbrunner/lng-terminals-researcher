"""
Extract liquefaction and regasification tables from the GIIGNL Annual Report.

CONTEXT: GIIGNL ships the annual report as a ZIP archive of page JPEGs plus
per-page OCR text files plus a manifest.json — NOT as a normal PDF. The OCR
text loses table column structure (it linearizes rows into runs of tokens),
so this extractor needs vision-LLM reading of the page JPEGs to recover the
column-aligned data correctly.

THE WORKFLOW THIS SCRIPT IS PART OF:
  1. Identify page ranges by section (this script handles that automatically
     by parsing manifest.json + scanning OCR for headers like "EXISTING
     LIQUEFACTION PLANTS").
  2. For each page, the script does NOT call a vision LLM itself — it stages
     the page JPEGs in a known location and writes a per-page extraction
     prompt template. The agent (Claude in this case, running this workflow)
     reads each JPEG with the view tool and fills in the extracted rows.
  3. The agent writes its extracted rows to a structured JSON per-page.
  4. This script then aggregates the per-page JSONs into a single flat CSV
     ready for consumption by report_diff.py.

WHY THIS DESIGN:
  - Pure OCR-based extraction loses too much structure (verified empirically
    on GIIGNL 2026 pages 32-37 + 54-62).
  - Calling a vision LLM via API would require a separate API harness; not
    necessary since the agent doing the workflow IS a vision-capable LLM.
  - Splitting "page identification + JPEG staging" (this script) from
    "vision extraction" (the agent's loop) keeps the deterministic parts
    deterministic and the LLM-shaped parts explicit.

Usage:
    # Phase 1: identify pages and stage JPEGs + prompts
    python giignl_extract.py --report ./GIIGNL2026AnnualReport0526b.pdf \\
        --stage-dir ./giignl_pages
    
    # Then the agent loops over staged pages, viewing each JPEG and writing
    # ./giignl_pages/page_NNN_extracted.json files
    
    # Phase 2: aggregate the per-page extractions
    python giignl_extract.py --aggregate ./giignl_pages \\
        --output ./giignl_extracted.csv
"""
import argparse
import csv
import json
import re
import sys
import zipfile
from pathlib import Path


# Section identifiers — these phrases (or close variants) typically mark the
# start of the relevant tables in the GIIGNL report. Verified against 2026 edition.
LIQ_HEADERS = [
    r"existing liquefaction plants",
    r"liquefaction plants in operation",
    r"liquefaction.*export.*operating",
]
REGAS_HEADERS = [
    r"existing regasification terminals",
    r"regasification terminals in operation",
    r"regasification.*import.*operating",
]
# Headers for sections we deliberately SKIP (under-construction, by-country
# summaries, etc.). Their content is interesting but the diff workflow focuses
# on the operating snapshot per Reconciliation SOP Appendix A.
SKIP_HEADERS = [
    r"under construction",
    r"by country",
    r"by company",
    r"contracts",
    r"shipping",
    r"floating storage",  # FSRU-specific narrative section (not the table)
]


# The schemas the agent is asked to fill (per Reconciliation SOP Appendix A)
LIQ_SCHEMA = [
    "country",
    "site_name",
    "owner",
    "capacity_mtpa",
    "start_year",
    "trains",
    "report_page",
    "notes",
]
REGAS_SCHEMA = [
    "country",
    "site_name",
    "type",  # onshore / FSRU
    "owner",
    "capacity_mtpa",
    "capacity_bcm",
    "start_year",
    "vessel_name",  # for FSRU rows
    "report_page",
    "notes",
]


def _extract_zip(zip_path, target_dir):
    """Extract the GIIGNL zip into target_dir. Returns the manifest."""
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(target_dir)
    manifest_path = target_dir / "manifest.json"
    if not manifest_path.exists():
        # The PDF is a ZIP-disguised-as-PDF per project files convention
        return None
    return json.loads(manifest_path.read_text())


def _identify_sections(stage_dir):
    """Scan OCR text files for section headers; return list of section dicts."""
    stage_dir = Path(stage_dir)
    txt_files = sorted(stage_dir.glob("page_*.txt"))
    if not txt_files:
        # Try alternate naming
        txt_files = sorted(stage_dir.glob("*.txt"))

    sections = []
    current = None
    for txt in txt_files:
        page_num = _extract_page_num(txt.name)
        text = txt.read_text(errors="replace").lower()

        # Check if this page starts a section we care about
        section_type = None
        for pattern in LIQ_HEADERS:
            if re.search(pattern, text):
                section_type = "liquefaction"
                break
        if not section_type:
            for pattern in REGAS_HEADERS:
                if re.search(pattern, text):
                    section_type = "regasification"
                    break

        # Check for skip headers (section break)
        skip_marker = any(re.search(p, text) for p in SKIP_HEADERS)

        if section_type:
            if current and current["type"] != section_type:
                current["end_page"] = page_num - 1
                sections.append(current)
                current = None
            if current is None:
                current = {"type": section_type, "start_page": page_num, "end_page": page_num}
            else:
                current["end_page"] = page_num
        elif skip_marker and current is not None:
            current["end_page"] = page_num - 1
            sections.append(current)
            current = None
        elif current is not None:
            # Continue section as long as no skip marker
            current["end_page"] = page_num

    if current is not None:
        sections.append(current)
    return sections


def _extract_page_num(filename):
    m = re.search(r"(\d+)", filename)
    return int(m.group(1)) if m else None


def _write_prompts(sections, stage_dir):
    """For each page in a section, write a per-page prompt template the agent
    will fill in (by viewing the corresponding JPEG)."""
    stage_dir = Path(stage_dir)
    prompts_written = 0
    for section in sections:
        schema = LIQ_SCHEMA if section["type"] == "liquefaction" else REGAS_SCHEMA
        for page in range(section["start_page"], section["end_page"] + 1):
            prompt_path = stage_dir / f"page_{page:03d}_prompt.md"
            content = (
                f"# GIIGNL extraction prompt — page {page} ({section['type']})\n\n"
                f"View the corresponding page JPEG (page_{page:03d}.jpg or similar) and extract "
                f"the table contents to `page_{page:03d}_extracted.json`.\n\n"
                f"## Output format\n\n"
                f"JSON object with `rows` list of objects, each with these fields:\n\n"
                + "\n".join(f"- `{f}`" for f in schema) +
                f"\n\n## Extraction rules\n\n"
                f"- One row per row in the table, even if the row is a country subtotal "
                f"(mark country subtotals with `notes: 'country subtotal'`).\n"
                f"- Leave fields blank if not shown in the table (don't infer from other pages).\n"
                f"- For OCR artifacts (e.g. \\u0002 characters, garbled cells), use the JPEG, not the OCR text.\n"
                f"- For FSRU rows, capture the vessel name in `vessel_name` if shown.\n"
                f"- Capacities: extract as shown; report_diff.py will normalize.\n"
                f"- For continuation pages where the table runs over from a previous page, "
                f"include only the rows visible on THIS page.\n"
            )
            prompt_path.write_text(content)
            prompts_written += 1
    return prompts_written


def stage(report_path, stage_dir):
    """Phase 1: extract the zip, identify sections, write per-page prompts."""
    manifest = _extract_zip(report_path, stage_dir)
    sections = _identify_sections(stage_dir)
    prompts = _write_prompts(sections, stage_dir)

    print(f"  Extracted {report_path} to {stage_dir}")
    print(f"  Identified sections:")
    for s in sections:
        print(f"    {s['type']}: pages {s['start_page']}-{s['end_page']}")
    print(f"  Wrote {prompts} per-page prompt templates")
    print(f"\n  Next step: the agent should now loop over the staged JPEGs,")
    print(f"  view each, and write page_NNN_extracted.json with the row data.")
    print(f"  Then run with --aggregate to produce the flat CSV.")

    # Stash section index for the aggregate step
    section_idx_path = Path(stage_dir) / "_sections.json"
    section_idx_path.write_text(json.dumps(sections, indent=2))


def aggregate(stage_dir, output_csv):
    """Phase 2: aggregate per-page extractions into a single flat CSV."""
    stage_dir = Path(stage_dir)
    section_idx_path = stage_dir / "_sections.json"
    if not section_idx_path.exists():
        sys.exit(f"ERROR: {section_idx_path} not found. Run with --stage-dir first.")
    sections = json.loads(section_idx_path.read_text())

    # All possible columns across both schemas (union, ordered)
    all_columns = ["section_type", "report_page", "country", "site_name", "type",
                   "owner", "capacity_mtpa", "capacity_bcm", "start_year",
                   "trains", "vessel_name", "notes"]

    all_rows = []
    missing_pages = []
    parse_failures = []
    for section in sections:
        for page in range(section["start_page"], section["end_page"] + 1):
            extracted_path = stage_dir / f"page_{page:03d}_extracted.json"
            if not extracted_path.exists():
                missing_pages.append(page)
                continue
            try:
                data = json.loads(extracted_path.read_text())
            except json.JSONDecodeError as e:
                parse_failures.append((page, str(e)))
                continue
            for row in data.get("rows", []):
                row_full = {c: "" for c in all_columns}
                row_full["section_type"] = section["type"]
                row_full["report_page"] = page
                for k, v in row.items():
                    if k in row_full:
                        row_full[k] = v
                all_rows.append(row_full)

    # Write CSV
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=all_columns)
        w.writeheader()
        for r in all_rows:
            w.writerow(r)

    print(f"  Aggregated {len(all_rows)} rows from {len(sections)} sections")
    print(f"  Wrote {output_csv}")
    if missing_pages:
        print(f"\n  WARNING: {len(missing_pages)} pages have no extracted JSON:")
        print(f"    {missing_pages}")
        print(f"  The agent didn't complete those pages — extract manually before diffing.")
    if parse_failures:
        print(f"\n  WARNING: {len(parse_failures)} pages had JSON parse errors:")
        for page, err in parse_failures:
            print(f"    page {page}: {err}")


def main():
    p = argparse.ArgumentParser()
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--stage-dir", help="Phase 1: stage zip + write prompts here")
    g.add_argument("--aggregate", metavar="STAGE_DIR",
                   help="Phase 2: aggregate per-page extractions from this dir")
    p.add_argument("--report", help="Path to GIIGNL report (.pdf, actually a zip)")
    p.add_argument("--output", help="(For --aggregate) output CSV path")
    args = p.parse_args()

    if args.stage_dir:
        if not args.report:
            sys.exit("--stage-dir requires --report")
        stage(args.report, args.stage_dir)
    elif args.aggregate:
        if not args.output:
            sys.exit("--aggregate requires --output")
        aggregate(args.aggregate, args.output)


if __name__ == "__main__":
    main()
