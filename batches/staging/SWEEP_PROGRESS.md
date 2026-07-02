# LNG sweep — progress ledger

**No sweep is currently in flight.** This file is the live checkpoint ONLY while a
multi-country sweep is running; when a sweep completes, its ledger is archived to
`batches/run_records/` and this file returns to this stub.

- Last completed sweep: full-tracker re-sweep + re-verify pass, finished 2026-06-04 —
  archived ledger: `batches/run_records/2026-06-04_full-tracker-resweep_ledger.md`
  (includes the resume recipes, done-marker conventions, rate-limit lessons, and
  auto-resume cron pattern; reuse them for the next sweep).
- All past runs: `batches/run_records/README.md`.

## Starting a new sweep

Replace everything below this line with the live ledger. Keep the shape the archived
ledger used — it is what makes a cold resume deterministic:

1. **Header per pass** — scope, tier (standard/exhaustive), user decisions, fresh-export
   stamp, conventions that differ from the briefs.
2. **Region status table** — one row per region; flip to DONE only after build +
   `recalc.py`; record the exact workbook filenames.
3. **Run log** — timestamped entries for anything a resumer must know (limits hit,
   partial waves, re-dispatches, tooling fixes made mid-run).
4. **Resume recipe** — the exact commands for a fresh session to continue
   (done-markers in `batches/staging/<region>/` are authoritative, not workflow return
   values).

Checkpoint this file after every region. When the sweep completes: archive the ledger to
`batches/run_records/<date>_<slug>_ledger.md`, restore this stub, and delete the
per-country `*.done.json` markers (see `batches/staging/README.md`, done-marker
lifecycle).
