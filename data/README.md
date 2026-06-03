# `data/` — GIIGNL Annual Report archive

This directory holds the **committed archive of GIIGNL Annual Reports, 2020–2026** (added
in commit `e4c34a9`). Unlike the GEM database export — which is volatile and pulled fresh
every batch (gitignored) — these published annual reports are stable historical artifacts,
so they live in the repo. This is the canonical location for the GIIGNL PDFs the
reconciliation workflow consumes.

## Manifest

Edition year **N** covers calendar-year **N−1** trade data (e.g. the 2026 edition reports
on 2025; its FSRU fleet table is "FSRU FLEET AT THE END OF 2025").

| File | Edition | Covers CY | Pages | PDF ver. | Liquefaction section | Regas section | FSRU fleet table |
|---|---|---|---|---|---|---|---|
| `GIIGNL-2020-Annual-Report.pdf` | 2020 | 2019 | 64 | 1.6 | ~38–43 | ~44–54 | p.20 |
| `GIIGNL-2021-Annual-Report.pdf` | 2021 | 2020 | 35 | 1.4 | ~20–31 † | ~23–31 † | p.11 |
| `GIIGNL-2022-Annual-Report.pdf` | 2022 | 2021 | 76 | 1.5 | ~44–51 | ~52–64 | p.23 |
| `GIIGNL-2023-Annual-Report.pdf` | 2023 | 2022 | 76 | 1.5 | ~46–53 | ~54–66 | p.33 |
| `GIIGNL Annual Report 2024.pdf` | 2024 | 2023 | 64 | 1.7 | ~32–39 | ~40–52 | p.29 |
| `GIIGNL - Livre 2025-20250610-Simple.pdf` | 2025 | 2024 | 76 | 1.7 | ~28–37 | ~46–62 | p.43 |
| `GIIGNL-2026-Annual-Report-0526b.pdf` | 2026 | 2025 | 80 | 1.7 | 28–37 ‡ | 48–63 ‡ | p.43 |

† **2021 is a condensed (COVID-era) edition** — 35 pages vs the usual 64–80, with abbreviated
and fragmented tables. Expect the parsers to need the most adjustment here.

‡ The 2026 edition is the one the current pipeline is tuned to. The section spans above bundle
the narrative + the tables; the Reconciliation SOP Appendix A.2 carries the finer 2026 split
(liquefaction **narrative** pp.28–31 / **tables** pp.32–37; regas **narrative** pp.48–52 /
**tables** pp.53–62). The fleet page (p.43) is verified by the `FSRU FLEET AT THE END OF 2025`
header. The filename varies because the user receives interim/dated cuts (`-0526b` = a
2026-05-26 revision).

Section page ranges above are **approximate and edition-specific** — they were derived by
header-pattern detection and a couple include adjacent key-figures/TOC pages. **Always
re-derive section boundaries per edition** (from the TOC or by content-pattern detection)
before pointing an extractor at an older report.

## Format — all genuine PDFs with text layers

`file` reports every one of these as `PDF document, version 1.4`–`1.7`. (Several show
`(zip deflate encoded)` — that is just normal Flate stream compression inside a real PDF,
**not** the legacy "zip-of-JPEGs" distribution form, which would report `Zip archive data`
as the top-level type.) `pdftotext -layout` extracts a clean, column-positioned text layer
from all seven, so the `giignl_extract.py` / `giignl_fsru_fleet.py` `pdftotext` pipeline is
the right tool for every edition here — **none** of these need the vision-LLM pipeline.

This corrects an earlier blanket assumption in the project docs that "earlier editions
shipped as zip-of-JPEGs+OCR." The zip-of-JPEGs form was a one-off distribution of *some*
copy encountered early in the project, **not** a property of pre-2026 editions. The
vision-LLM fallback still lives in git history, and the standing rule remains: **`file
<path>` before assuming the format** — a future download could still arrive as a zip.

## What this archive is for

- **Back-checking a GEM `capacity_ref` against the edition it cites.** Many GEM unit-rows
  cite a specific GIIGNL edition for capacity (e.g. `GIIGNL2022_Annual_Report`). With every
  edition on disk, the GEM-vs-GIIGNL verdict work can read what that *cited* edition actually
  said — rather than only comparing against the current year — and confirm a real change vs a
  superseded figure.
- **Year-over-year reconciliation / trend checks** — when a 2026 value looks off, the prior
  editions show whether a capacity, owner, or status genuinely moved or is a one-edition blip.
- **Back-testing the extractors** — running `giignl_extract.py` / `giignl_fsru_fleet.py` on
  older editions to validate (or harden) the parsing logic against layouts it wasn't tuned on.

## Caveat — the extractors are tuned to the 2026 layout

`giignl_extract.py` (country tables) and `giignl_fsru_fleet.py` (fleet table) derive or hard-code
**column character-offsets and page numbers from the 2026 edition**. Older editions move the
tables to different pages, shift the column positions, and in some years carry different columns
(e.g. the 2020 vessel fleet listing has a `Manager` column the 2026 fleet table doesn't). So a
back-extraction on a pre-2026 edition is **not** turn-key — it needs per-edition page selection
(`--page` for the fleet parser) and offset re-derivation from that edition's header row. Treat
the table page-ranges above as a starting hint, not a guarantee.

See `docs/sops/reconciliation.md` (Appendix A) for the extraction rules and the 2026 page map.
