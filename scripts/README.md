# Scripts

All scripts are standalone (no install step). Each has a `--help` and a
top-of-file docstring.

## Typical invocation order in a batch

```
# 1. Always start with a fresh pull (no cookies needed for the all-fields path)
python gem_all_fields.py -o gem_export.csv
python pull_gem_db.py --map-only --out gem_export.csv   # derive the .colmap.json

# 2. Build the matching indexes
python dedup_index.py

# 3. Run any triage/discovery/update/reconciliation-specific scripts:
python stale_sweep.py                                       # for triage or update
python giignl_extract.py <report.pdf> --output giignl_extracted.csv --year 2026   # recon phase 1
python report_diff.py --report giignl --extracted giignl_extracted.csv \
    --gem-csv gem_export.csv --output report_diff.json      # recon phase 2
python fsru_sync_check.py                                    # if batch touches FSRUs

# 4. Build the xlsx
python build_review_package.py --mode update --output ../batches/...

# 5. Verify no formula errors
python recalc.py ../batches/...
```

## Script-by-script

### Data acquisition

| Script | Purpose |
|---|---|
| `gem_query.py` | Queries the GEM read-only Postgres database directly and exports to CSV. Lowest-level acquisition tool. |
| `gem_all_fields.py` | Reproduces the website's "all-fields" LNG terminal CSV. **No cookies needed** — preferred fresh-pull path. |
| `gem_export_via_web.py` | Downloads the all-fields CSV from the running GEM website. Cookie-based (auth from `.env`). |
| `pull_gem_db.py` | Wraps a data-pull and derives the 115-column index map, writing `.colmap.json` next to the CSV. Use `--map-only` to derive the colmap from an existing CSV without re-pulling. |
| `fetch_timeline.py` | Pulls the full status timeline for a single UnitID from the live DB web UI. Required before any status timeline edit — the CSV export doesn't include timeline data. **Parser is heuristic — verify against the live UI for at least one unit per batch.** |
| `giignl_extract.py` | Parses the GIIGNL annual-report PDF into a flat CSV with GEM-aligned columns. Uses `pdftotext -layout` + column-position row partitioning; per-country capacity subtotals act as block-boundary budgets. (The 2026 edition is a real PDF v1.7 with a clean text layer. The legacy zip-of-JPEGs + OCR vision pipeline lives in git history if a future edition reverts.) |

### Normalization and validation

| Script | Purpose |
|---|---|
| `normalize.py` | Canonical names for countries, entities (owners/operators), capacity units, and terminal names. Also transliterates non-Latin names (e.g. Chinese `LocalNames`) to English via jieba + pypinyin for cross-script alias matching. Import as a library; CLI runs smoke tests. |
| `capacity_normalize.py` | mtpa/bcm/y conversion, range parsing (records max per methodology). |
| `status_timeline.py` | Validates legal state transitions, anchor year invariants, current-status derivation. Used by build_review_package.py. |

### Search and dedup

| Script | Purpose |
|---|---|
| `dedup_index.py` | Builds project/sponsor-country/unit indexes from the GEM CSV. Used by discovery batches to check if a candidate already exists. |
| `entity_lookup.py` | Searches local CSV (and optionally remote entity system) for an entity name. Run before staging any new entity. |
| `url_verifier.py` | HTTP 200 + content check + soft-error detection. Every cited URL must pass before being staged. |
| `imo_tracker.py` | Look up FSRU/FLNG vessel IMO via marinetraffic.org. |

### Workflow-specific

| Script | Purpose |
|---|---|
| `stale_sweep.py` | Flags units exceeding lifecycle dormancy thresholds. Used by triage and stale-driven update batches. |
| `report_diff.py` | Reconciliation diff between an industry report (GIIGNL or IGU) and current GEM data. Parameterized on report type. Three-pass matching (canonical name → alias via `OtherNames`/`LocalNames` + transliterations → fuzzy); project key includes `section_type` so a mixed liquefaction+regasification terminal splits into two projects rather than summing. |
| `fsru_sync_check.py` | Cross-checks FSRU records between the LNG Terminals project and the LNG Carrier Tracker project. Graceful degradation if carrier backend unavailable. |

### Output

| Script | Purpose |
|---|---|
| `build_review_package.py` | Assembles the batch xlsx from staged JSON inputs. Three modes: `update`, `discovery`, `reconciliation`. Respects read-only column list. |
| `recalc.py` | Final formula-error check on generated xlsx before presenting to user. |

## Data-acquisition paths

There are three ways to pull the GEM CSV, in increasing reliance on auth:

- `gem_all_fields.py` — reproduces the website's all-fields export with **no cookies**. Preferred default.
- `gem_query.py` — hits the read-only Postgres DB directly.
- `gem_export_via_web.py` — downloads from the live website using auth cookies from `.env`.

All three are committed to the repo (no longer user-supplied). `pull_gem_db.py`
wraps a pull and derives the column-index map; run it with `--map-only` to derive
the colmap from a CSV you already pulled.

## Inter-script dependencies

```
normalize.py           ← imported by most others
url_verifier.py        ← imported by build_review_package
capacity_normalize.py  ← imported by build_review_package
status_timeline.py     ← imported by build_review_package
dedup_index.py         ← reads pull_gem_db output (.colmap.json)
stale_sweep.py         ← reads pull_gem_db output
report_diff.py         ← reads pull_gem_db output + giignl_extract output
fsru_sync_check.py     ← reads pull_gem_db output + optional carrier CSV
build_review_package.py ← reads all *.json staged outputs
recalc.py              ← reads build_review_package xlsx output
```

The simplest pattern (`sys.path.insert(0, str(Path(__file__).parent))` at the
top of each script) means scripts can import each other without any install
step. Don't refactor into a package unless you have a specific reason.
