# batches/ — everything a batch produces

Four kinds of things live here. The rule of thumb: **workbooks are regenerable and
gitignored; everything needed to regenerate them (and the record of what happened) is
tracked.**

| Path | What it holds | Tracked? |
|---|---|---|
| `*.xlsx` (this level) | Routine batch workbooks — `lng_terminals_batch_<stamp>_ET[_<scope>]_<mode>.xlsx`. Rebuilt from staging any time; the user prunes old ones. Never overwrite one — every rebuild gets a fresh timestamp. | no (gitignored) |
| `triage_*.md` / `qc_*.md` (this level) | Triage and QC memos — those workflows produce markdown, not workbooks. | yes |
| `staging/` | ALL batch inputs: per-country sweep JSON, per-edition recon staging, ad-hoc `staged_*.json`, the sweep ledger + dispatch briefs. The diffable audit trail — agent-authored research is committed, derived artifacts are not. See `staging/README.md`. | yes (see its README for the derived-file exceptions) |
| `run_records/` | One dated md per major run: trigger → what happened → outcome. The "what was last done" log; index in `run_records/README.md`. | yes |
| `deliverables/` | Workbooks kept long-term because the exact artifact matters (e.g. the missing-year ref-sweep for a data-team decision). See `deliverables/README.md`. | yes (xlsx included — the gitignore rule is deliberately top-level-only) |
| `old/` | Parking for superseded workbooks awaiting pruning. | no (gitignored) |

Naming and color conventions for the workbooks: `docs/reference/workbook_conventions.md`.
