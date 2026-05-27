# Scripts

All scripts are standalone (no install step). Each has a `--help` and a
top-of-file docstring.

## Typical invocation order in a batch

```
# 1. Always start with a fresh pull
python pull_gem_db.py

# 2. Build the matching indexes
python dedup_index.py

# 3. Run any triage/discovery/update/reconciliation-specific scripts:
python stale_sweep.py                          # for triage or update
python giignl_extract.py --stage-dir ...       # reconciliation phase 1
python report_diff.py --extracted ...          # reconciliation phase 2
python fsru_sync_check.py                      # if batch touches FSRUs

# 4. Build the xlsx
python build_review_package.py --mode update --output ../batches/...

# 5. Verify no formula errors
python recalc.py ../batches/...
```

## Script-by-script

### Data acquisition

| Script | Purpose |
|---|---|
| `pull_gem_db.py` | Wraps `gem_export_via_web.py` to pull the all-fields CSV. Derives the 115-column index map and writes `.colmap.json` next to the CSV. |
| `fetch_timeline.py` | Pulls the full status timeline for a single UnitID from the live DB web UI. Required before any status timeline edit — the CSV export doesn't include timeline data. **Parser is heuristic — verify against the live UI for at least one unit per batch.** |
| `giignl_extract.py` | Two-phase GIIGNL extraction. Phase 1 stages page JPEGs + per-page prompts; phase 2 aggregates per-page extractions into a flat CSV. |

### Normalization and validation

| Script | Purpose |
|---|---|
| `normalize.py` | Canonical names for countries, entities (owners/operators), capacity units, and terminal names. Import as a library; CLI runs smoke tests. |
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
| `report_diff.py` | Reconciliation diff between an industry report (GIIGNL or IGU) and current GEM data. Parameterized on report type. |
| `fsru_sync_check.py` | Cross-checks FSRU records between the LNG Terminals project and the LNG Carrier Tracker project. Graceful degradation if carrier backend unavailable. |

### Output

| Script | Purpose |
|---|---|
| `build_review_package.py` | Assembles the batch xlsx from staged JSON inputs. Three modes: `update`, `discovery`, `reconciliation`. Respects read-only column list. |
| `recalc.py` | Final formula-error check on generated xlsx before presenting to user. |

## User-supplied script

`gem_export_via_web.py` (not committed; gitignored) is the auth wrapper that
`pull_gem_db.py` invokes. Drop it into this directory before running. Auth
cookies come from `.env`.

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
