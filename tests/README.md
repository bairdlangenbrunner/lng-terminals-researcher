# tests/

Minimal pytest suite pinning the edge-case-hardened parsers and the build-time
guards. Run from the repo root:

```bash
pytest tests/
```

No install step: `conftest.py` puts `scripts/` on `sys.path` (the same pattern
the scripts themselves use).

| File | What it pins |
|---|---|
| `test_capacity_normalize.py` | Unit conversions (mtpa/bcm/bcf-d) + capacity range parsing — the single conversion table in `normalize.py` that `capacity_normalize.py` delegates to. |
| `test_normalize.py` | Name/country normalization (diacritics, Roman↔Arabic numerals, region-tag stripping with the unbalanced-paren guard), `effective_status` substatus=planned→proposed rule, entity-list parsing. |
| `test_report_diff.py` | Owner parsing (spaced-slash split, Owner:/Charterer: roles, shareholder expansion) + expansion-row name folds (Train E / GL1Z / Stage III, with the Senboku-II single-letter guard). |
| `test_giignl_extract.py` | Integration snapshot against the committed `data/GIIGNL-2026-Annual-Report-0526b.pdf` — 348 rows, section totals, and the specific rows that regressed historically (Niigata/Niihama owner bleed, Sodegaura co-owner, Bontang mothballed hint, LNG Canada site tag). Skips if `pdftotext` is missing. Takes a few seconds. |
| `test_build_guard.py` | `build_review_package.py`'s URL-routing guard: a URL aimed at a data/enum column is refused, URLs land only in `[ref]` columns, read-only columns are never written, and same-edition GIIGNL mirror URLs are flagged as one source. |
| `test_validate_records.py` | `build_review_package.py`'s `_validate_records` GUARD pass: unknown staged-JSON keys warn (the silently-blank-cell class), missing required identity keys warn, clean records are silent, non-list input is a no-op. |
| `test_monitor_store.py` | `monitor_store.py` round-trip: seed/merge/dedup of the cross-batch monitor list. |
| `test_colmap.py` | Shared `colmap.load_colmap`: happy path, missing colmap → RuntimeError, BOM-safe header re-derivation when `_header_columns` is absent. |
| `test_schema_constants.py` | `schema_constants.py` column sets: non-empty, computed/out-of-scope disjoint, READ_ONLY_COLUMNS is exactly their union. |

When an extractor/parser edit changes one of these numbers, treat the test as
the spec: the pinned values come from the deep-dives in `scripts/README.md`
and the run records — don't just update the assertion, check which defended
edge case broke.
