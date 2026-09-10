# Improvement plan — Codex audit, evaluation, and re-plan (2026-09-09)

Living plan. Supersedes nothing; it sits alongside `docs/repo_audit_2026-07-16.md`
(the earlier workflow/redundancy audit) and takes a different cut: the repo as a
*system* — enforcement, reproducibility, state, packaging, and the public/private
boundary.

**Note on names — decided 2026-09-09:** this repo is **public**
(`bairdlangenbrunner/lng-terminals-researcher`), and colleague first names **are
allowed here**, in paths, filenames, run records and docs. The user considered the
exposure and accepted it deliberately; the general "no full names in public repos"
default does not apply to this repo. Nothing is to be scrubbed, renamed, or
history-rewritten, and no name scan belongs in CI. Part 3's finding 1 and the
original Phase 0.1 are retained below as the record of what was weighed.

---

## Provenance and status

A Codex (ChatGPT, `gpt-5.6-luna`) session on 2026-09-09 11:43–12:00 ET audited the
repo, then began implementing its own recommendations. It was **killed mid-step-1 of 6
by workspace credit exhaustion** (`usage_limit_exceeded`), immediately before running
its verification command. Nothing it wrote was ever verified by it, and nothing was
committed.

- Session log: `~/.codex/sessions/2026/09/09/rollout-2026-09-09T11-43-41-01a086d6-….jsonl`
- Prompts: *"review this repo (largely created by claude) and give me critical feedback"*,
  then *"ok, let's implement all of this"*.

Every factual claim below carries a verdict from an independent re-check on
2026-09-09 afternoon: **CONFIRMED**, **PARTLY**, or **NOT CONFIRMED**.

---

## Part 1 — The Codex audit, as delivered

### Overall verdict (its words)

> This is a thoughtful, domain-rich repository with much better research discipline
> than most LLM-generated systems. Its strongest features are the read-only database
> stance, explicit source rules, retained research trail, regression tests built from
> real failures, and separation between detection and human-applied edits.
>
> The central weakness is that its safety model remains procedural. The documentation
> repeatedly says "mandatory," "never," and "hard gate," while the implementation often
> prints a warning, continues, and writes a deliverable.

Its one-line design principle: *preserve the domain knowledge, but move every rule that
can affect correctness out of prose and into validated data, executable gates, or both.*

### P0-1 — The mandatory QC gate is not a gate — **CONFIRMED**

`staging_qc.py` never exited nonzero on findings; its final branch printed
`GATE NOT CLEAN` and returned success. Codex reproduced it live: the gate on the
LAC sweep reported **59 findings, `GATE NOT CLEAN`, exit 0**.

Same pattern elsewhere:
- Invalid JSON → empty input (`build_review_package.py:516`)
- Record-schema problems "warn, never fail" (`:673`)
- Workbook saved regardless (`:3903`)
- Assembler coerces malformed/non-list JSON to `[]` and continues (`batches/staging/_assemble.py:35`)
- `_build_region.py:104` escalations displayed but do not stop the build

**Its recommendation:** strict by default; exit nonzero for invalid JSON, unknown
required keys, invalid IDs, undeclared ref drops, incomplete shards, unresolved
escalations; `--allow-warnings` escape hatch; write to a temp path and publish only
after gates pass; emit machine-readable `validation.json`.

### P0-2 — Historical batches are not reproducible — **CONFIRMED**

`batches/README.md:3` calls routine workbooks regenerable at any time, but rebuilding
depends on the current, overwritten `gem_export.csv`. Batch metadata records no export
hash, schema hash, DB snapshot time, or sibling-repo revision. A historical rebuild can
pull different unedited cells, produce different ref-drop findings, match different IDs,
silently omit records — and be indistinguishable from the original artifact.

Evidence it cited: a batch recorded as guard-clean in its run record now reports many
baseline mismatches against the 2026-08-26 export.

**Its recommendation:** an immutable per-batch manifest carrying batch UUID, workflow
version, repo commit + dirty-tree hash, `gem-db-ops` SHA, export fetch time / SHA-256 /
header-schema hash / row count, report hashes, exact commands, input+output artifact
hashes, URL-verification evidence IDs, validation result, per-country/per-lane state.
The xlsx should be *a rendered view of a canonical change set*, not the only faithful
artifact. If the full export cannot be committed (public repo), keep a private or
encrypted snapshot, or a minimized baseline of all touched rows/columns.

### P0-3 — The operational state model is unreliable — **CONFIRMED**

Re-check: **1 of 47 `meta.json` files carries an `applied` date**; statuses are
`built` 33, `superseded` 11, `abandoned` 1, `in_progress` 1, `applied` 1.
`batches/staging/README.md:13` already admits `applied` cannot be trusted.

Also cited: the declared enum omitted `complete` while two files used it; two newer
files lacked `scope_slug`/`started`; a QC dir marked `built` while its own metadata says
one pass is in flight and another was never run; `coverage_status.py:223` always exits 0
with no schema validation; superseded/abandoned batches can win the freshness
calculation because the "retired" rank only breaks same-day ties (`:114–130`); the LAC
sweep metadata says discovery was incomplete for ten countries while acknowledging the
ledger will report them as swept.

**Its recommendation:** formal batch schema, validated everywhere; lane-specific states
(`update.complete`, `discovery.partial`, `qc.citation.pending`); per-country results
rather than one status per region; separate `researched` / `built` / `reviewed` /
`applied` / `verified_after_apply` / `superseded` / `abandoned`; never credit partial,
abandoned or superseded work as freshness; generate the coverage ledger and run-record
index from manifests.

### P1 — A clean setup does not install the current workflows — **CONFIRMED**

`requirements.txt` at HEAD listed only `openpyxl`, `jieba`, `pypinyin`, `pytest`
(plus a poppler note). Scripts also need SQLAlchemy + a Postgres driver; NumPy /
Pillow / SciPy; GeoPandas / Shapely / Cartopy; `curl`, `unzip`, `tesseract`,
`pdftotext`, `pdftoppm`; and the sibling `gem-db-ops` repo.
`georeference_figure.py:42` claims its deps are "already used by this repo" — they
were not declared. `README.md:36` tells users to put values in `.env`; **no code
loads `.env`** (re-checked: zero `dotenv` references repo-wide).

**Its recommendation:** `pyproject.toml`, declared Python version, dependency groups
(`core`/`db`/`geo`/`ocr`/`dev`), a lockfile, and an `lng doctor` that checks packages,
binaries, env vars, sibling repos, DB read-only access, and reference-data caches.
Either load `.env` or stop implying it is loaded. Pin the compatible `gem-db-ops` revision.

### P1 — Paths and commands are not portable — **PARTLY**

`paths.py` is the right direction, but many scripts still default to CWD-relative
`./gem_export.csv`, and the workflows mix "run from repo root" with "run from
`scripts/`". Committed briefs contain the author's absolute `/Users/baird/...` path
(e.g. `batches/staging/_country_agent_brief.md:8`); some scripts hard-code the retired
Heroku host.

**Recommendation:** repo-root-relative or config-driven paths everywhere; one root-level
command (`lng update|validate|build|close`); no CWD-dependent instructions; replace
embedded URLs with `GEM_PROJECT_DB_BASE_URL`; CI guard rejecting `/Users/`,
`/home/claude`, Dropbox paths, and obsolete hosts.

### P1 — Too many representations of the same truth — **CONFIRMED**

Truth is spread across `meta.json`, `SWEEP_PROGRESS.md`, run records, the run-record
index, workbook filenames, the deliverables README, the monitor store, URL logs, TODO,
and SOP prose. `batches/run_records/README.md:14` says the index must be updated
manually — re-check: **the index table stops at 2026-07-02 while 51 records exist**.

**Recommendation:** make the manifest authoritative; generate indexes, coverage reports
and deliverable tables from it; keep run records as narrative only; add a `close` command
that validates, builds, hashes, updates metadata, writes the run-record stub and
regenerates indexes atomically.

### P1 — The working tree is acting as a database — **CONFIRMED**

At review time: 32 modified tracked files, 58 untracked entries expanding to ~664 files,
1,399 added / 810 removed lines, operational work through 2026-08-26 against a last
commit of 2026-07-29.

**Recommendation:** branch or worktree per batch; immutable checkpoints after dispatch,
validation, build, review, closeout; keep reusable code changes separate from research
output; an "unfinished runs" report in `lng doctor`.

### P1 — Batch-specific code is proliferating — **PARTLY**

Codex counted ~2,641 lines across 18 regional `_assemble_*` / `_build_dispatch.py` /
`_compute_neighbors.py` variants under captive-power staging, "with several
byte-identical copies". Re-check: **23 `.py` files, 3,082 lines** under
`batches/staging/captive_power/` — larger than claimed, but a spot md5 pass found **no
byte-identical `_assemble_*` pairs**, so "several byte-identical copies" is unproven.
The substance (one-off scripts accumulating in a data directory, canonical-vs-historical
ambiguity) stands.

### P1 — Global mutable files are unsafe under concurrency — **CONFIRMED**

`work/apply_check.json` overwrites previous runs (`apply_check.py:205`);
`work/citation_qc.json` likewise; `monitor_list/current.json` is an unlocked
read-modify-write (`monitor_store.py:160`); per-region `_build/` dirs collide;
`_build_region.py:73` **temporarily moved live staging inputs out of the tree** to
filter them.

**Recommendation:** an isolated workspace per run —
`runs/<batch-id>/{manifest.json,inputs,research,derived,validation,outputs,run.md}` —
atomic writes and locks for genuinely shared stores, and in-memory input selection
instead of moving files.

### P1 — Staged JSON needs a real schema — **CONFIRMED**

The record vocabulary is embedded in the (now) 4,003-line workbook builder
(`build_review_package.py:527`), coupling validation, policy and presentation.

**Recommendation:** versioned JSON Schema / typed models per record type, validated at
shard write, at assembly, and before build; semantic validation for field/ref pairing,
status and timeline transitions, project-level propagation, confidence values, deletion
declarations, read-only fields, ID ownership, required evidence, captive-power
unit-level annotations. Longer term: a canonical `ChangeSet`, with the workbook as one
renderer.

### P1 — URL verification is not tied to edits — **CONFIRMED (sharpest finding)**

`url_verifier.py` makes its audit log **optional** (`URL_VERIFIER_LOG`) and continues if
logging fails. Re-check: **`build_review_package.py` never imports or calls
`url_verifier`** — all 5 matches are docstring prose. So the repo's strongest documented
invariant ("Every URL passes `url_verifier.py` before going in the xlsx — no exceptions")
has **zero mechanical enforcement**. An agent can assert "verified" with no evidence, or
verify against the wrong token.

**Recommendation:** every staged citation references an evidence record — canonical URL,
claimed token, fetch time, HTTP/fallback result, content hash or snapshot id, tool
version, pass/fail, publisher identity for independence counting — and the build rejects
any cited URL without a matching passing record.

### P2 — Entity lookup exposes credentials — **CONFIRMED, low severity**

`entity_lookup.py:284` passes session cookies on the `curl` command line (visible to
other local processes) and writes to a fixed temp filename
(`$TMPDIR/entity_lookup.html`), so concurrent invocations collide.
**Recommendation:** a Python HTTP session or curl config on stdin, unique temp file,
reliable cleanup — or remove the remote path entirely, since Postgres is authoritative.

### P1 — Tests do not cover the operational failure surface — **CONFIRMED**

81 tests passed at HEAD, grounded in real historical regressions (GIIGNL extraction,
owner parsing, normalization, workbook guards) — genuinely valuable. But there is no CI,
packaging, linting, type checking, schema validation, or end-to-end fixture. Nothing
proves a failed gate exits nonzero, invalid staging cannot produce a workbook, required
inputs cannot vanish, rebuilds are deterministic, monitor updates are concurrency-safe,
a lifecycle updates metadata correctly, build→`apply_check` preserves values, or all
archived report editions still parse.

**Recommendation:** GitHub Actions (tests, schema validation, Ruff, type check,
markdown-link check, forbidden-path check, secret scan); one small end-to-end fixture per
workflow; negative tests; determinism tests on output hashes; back-test each report
edition or label older ones archive-only.

### P2 — Monoliths and documentation carry too much history — **CONFIRMED as fact**

`build_review_package.py` 4,003 lines; `report_diff.py` 2,691; `giignl_extract.py`
1,549; `scripts/README.md` ~11,900 words including a **13,802-character single line**;
operational docs ~76,000 words total.

**Recommendation:** `CLAUDE.md` as a short router plus universal invariants; machine-
readable field/status/source rules in config or schemas; incident histories moved to ADRs
or postmortems; split workbook rendering by sheet and reconciliation into
extraction/matching/classification/verdicts/rendering; generate script and workflow
indexes.

*(See Part 3 — I disagree with the documentation half of this.)*

### Documentation contradictions — **CONFIRMED**

- `README.md:10` says **nine** workflows; `CLAUDE.md` frontmatter says **five**; the
  2026-07-16 audit says **eight**; `docs/workflows.md` has **ten** numbered sections
  (some are wrappers/sub-recipes). CLAUDE.md's own router table lists nine.
- `README.md:43–44` still frames `fetch_timeline.py` as needing cookies + base URL;
  the implementation is Postgres-only.
- **`docs/reference/sop_pointers.md:48` and `:86` still say entity lookup runs
  bare + `--remote`, while the hard requirement is bare + `--pg`.**
- QC SOP describes committed structured findings (`qc.md:31–39`), then its
  quick-reference says tool JSON belongs in ignored `work/` (`:146`).
- "Never overwrite a workbook" was not enforced; the builder saved to the given path.

**Recommendation:** define the workflows once in a machine-readable catalog and generate
the README/router tables from it.

### Public-repository and artifact concerns — **CONFIRMED, and understated**

The remote is public. The tree contains an internal methodology link, internal
project-edit URLs and record IDs, researcher names and assignments, a raw
design-conversation transcript (596 KB, tracked), external report PDFs
(**53 MB**, 7 tracked), and untracked assignment data with an external spreadsheet ID.
No `LICENSE`, `SECURITY.md`, data-classification policy, or PDF provenance/licensing.

**Recommendation:** decide deliberately what belongs in a public code repo vs a private
research-artifact repo; add `LICENSE`, `SECURITY.md`, classification guidance; check PDF
redistribution rights; add source URLs, checksums, retrieval dates and licensing to the
data manifest; consider LFS or release storage for large immutable artifacts; automated
secret and personal-path scanning; drop the raw design transcript unless it earns its keep.

### Its suggested target organization

```text
pyproject.toml / uv.lock
src/lng_terminals/{cli,config}.py
  models/{batch,changes,evidence}.py
  workflows/{update,discovery,reconciliation,qc,captive_power,georeference}.py
  services/{gem_export,entity_lookup,url_verification}.py
  validators/  renderers/xlsx.py
config/{workflows,fields,reports}.yaml
schemas/  docs/{handbook,adr,postmortems}/  runs/<batch-id>/
tests/{unit,integration,fixtures}/
CLAUDE.md  AGENTS.md
```

### Its recommended order

1. Protect uncommitted work by separating and checkpointing completed batches
2. Make validation and staging QC fail closed
3. Batch manifests, snapshot hashes, per-lane/per-country state
4. Reproducible environment, dependency groups, `doctor`
5. One root-level CLI and run-isolated workspaces
6. Schemas; bind citation evidence to staged claims
7. CI and end-to-end lifecycle tests
8. Parameterize duplicated regional scripts
9. Refactor large modules incrementally behind existing tests
10. Consolidate documentation; define the public/private artifact boundary

---

## Part 2 — What Codex actually landed before it died

Roughly five minutes of implementation, all **uncommitted**, none verified by it.

**New (untracked):**

| File | What it does |
|---|---|
| `scripts/atomic_io.py` | atomic JSON write, exclusive file lock |
| `scripts/batch_contract.py` | `validate_meta`, `build_manifest`, `RETIRED_STATUSES` |
| `scripts/lng.py` | root CLI: `doctor`, `validate`, plus passthroughs |
| `schemas/meta.schema.json`, `schemas/manifest.schema.json` | batch metadata + manifest contracts |
| `pyproject.toml` | deps, `geo`/`figures`/`dev` extras, ruff + pytest config |

**Modified:** `build_review_package.py` (fail-closed gates, atomic write + manifest,
**output-exists guard at `:3624` — this finally enforces the "never overwrite a batch
file" rule**), `staging_qc.py` (fail-closed, `--allow-warnings`), `_assemble.py`
(merges without moving source files), `_build_region.py`, `coverage_status.py`
(validates, exits nonzero), `monitor_store.py` (atomic + locked), `requirements.txt`,
and `scope_slug`/`started` backfilled into 5 staging `meta.json`.

**Verification it never ran (run afterwards):**

- `python -m compileall` — clean
- `python scripts/lng.py validate` — passes, 47 contract files
- `python -m pytest -q` — **80 passed, 1 failed**. `tests/test_validate_records.py::test_non_list_input_is_a_no_op`
  asserts silence on malformed input; the fail-closed change now prints
  `GUARD: staged_updates: expected a JSON list, got NoneType`. HEAD is clean at 81 passed.
  The test is stale relative to intended behavior — but it was left failing and unnoticed.

**Hazard:** six of the files Codex edited were *already dirty* with prior uncommitted
work. Its changes are interleaved, so a blanket `git checkout` to back Codex out would
also destroy that work. It stated it would not disturb the working tree and then edited
into it anyway.

---

## Part 3 — Critical evaluation

### Where it is right, and it matters

1. **Enforcement gap is the correct diagnosis.** The url_verifier finding is the single
   best thing in the audit: the most absolute rule in `CLAUDE.md` is enforced by nothing
   but agent good behavior. Every other correctness rule inherits that weakness.
2. **`applied` state is fiction** — 1 of 47, exactly as claimed. The coverage ledger is
   the mechanism that prevents duplicate research, and it is built on a field nobody sets.
3. **`sop_pointers.md` still says `--remote`** while the hard requirement says `--pg`.
   This is not cosmetic drift: `--remote` false-negatives are a *recorded* cause of a
   duplicate entity. An agent doing a quick rule lookup gets the wrong answer today.
4. **Dependencies are undeclared.** A clean clone cannot run the Postgres timeline path.
5. **Reproducibility.** Overwriting `gem_export.csv` in place means no historical batch
   can be re-derived or defended. For a dataset whose edits are reviewed by GEM staff,
   that is a real liability, not a purist concern.

### Where it is wrong or overstated

- **"The 'fresh export is never committed' rule is violated by tracked export/state
  files" — NOT CONFIRMED.** No `.csv` is tracked at all; no `gem_export`, no `.colmap.json`.
  The only matches are `scripts/colmap.py` and `work/.gitkeep`. This was listed among the
  P0-tier "concrete contradictions" and it does not hold.
- **"Several byte-identical copies"** of the regional assemblers — unproven on spot check.
- **It claimed both trees pass 81 tests, then broke one and never re-ran** the suite. The
  audit's own evidence standard was not applied to its implementation.
- **`requirements.txt` was less naked than implied** — it already documented poppler as a
  non-pip system dependency, which the audit's list of missing deps did not acknowledge.

### Where I disagree on principle

**The documentation-compression recommendation is aimed at the wrong reader.** Codex
treats ~76,000 words of operational prose and "incident histories, worked examples, old
failure narratives" as debt to be moved into ADRs. But the primary consumer of these docs
is an LLM agent that loads `CLAUDE.md` and one SOP per batch. Those incident histories are
the enforcement mechanism — the router notes are literally a list of named regressions
(the wiki-coverage miss, the power-plant-vs-terminal miss, the standby-duty reversal, the
FSRU-onboard convention). Relocating them to `docs/adr/` moves them *out of the context
path* and converts a working guardrail into an archive nobody loads. Compressing prose is
a human-ergonomics fix applied to an agent-ergonomics artifact.

The correct version of this recommendation is narrower and I do endorse it: move the rules
that are **machine-checkable** (field/status enums, read-only columns, banned domains,
confidence thresholds) into config the code reads, and *leave the narrative rationale in
prose*. That removes the drift risk without removing the teaching.

**The `src/lng_terminals/` package rewrite is not worth it.** It would break every SOP
command line, every recipe in `docs/workflows.md`, and every CLAUDE.md invocation, in
exchange for import hygiene. This repo's scripts are invoked by an agent reading a recipe,
not imported by an application. Steps 8–10 of its order are the least valuable and the
most disruptive; they are listed last, which is right, but they should be listed as
optional, which they are not.

**`runs/<batch-id>/` restructure: right diagnosis, disproportionate cure.** The concurrency
and isolation problems are real, but ~90% of the benefit comes from manifests + atomic
writes + locks (already scaffolded) applied to the *existing* layout. A full relayout also
invalidates the coverage ledger and every path in the SOPs.

### What it missed

1. **The names problem is live and imminent, not abstract.** The repo is public. Committed
   history is nearly clean — a re-check found the tracked hits are almost all false
   positives (a Texas place name), with **one genuine committed instance** in a run record
   quoting a colleague's name. But the **uncommitted tree contains eleven paths whose slugs
   or filenames embed colleague first names** — staging directories, run records, and a
   deliverable xlsx — plus an untracked, non-ignored `docs/reference/researcher_assignments.json`.
   A single `git add -A` publishes all of it. Codex listed "researcher names and assignments"
   as one bullet in a P-unranked section. It is the most time-sensitive item in the audit.
   *(Superseded 2026-09-09 — see the header note. The tree landed as-is in PR #32 with the
   names intact, by decision; only the assignments cache was ignored, and for its sheet id
   rather than its names. This paragraph is kept as the record of what was weighed.)*
2. **The uncommitted backlog deserves P0, not P1.** ~664 files of research output spanning
   2026-07-29 → 2026-09-09 live only in a **Dropbox-synced working tree** — no git object,
   exposed to sync conflicts. Every other fix has to be applied on top of it, and Codex's
   own half-finished refactor is now interleaved with it, which made the entanglement worse.
3. **The interleaving hazard it created.** Reverting Codex now costs prior work.
4. **The failing test.** Its own change; never run.
5. **The simplest fix to half of its "public repository concerns" is one command:**
   `gh repo edit --visibility private`. Nothing in this repo needs to be public — it is
   operational scaffolding for one researcher plus GEM staff. Codex framed this as a
   long-term classification project rather than a switch.

---

## Part 4 — Re-planned roadmap

Ordered by *risk retired per hour*, not by architectural tidiness.

### Phase 0 — Stabilize (do before anything else)

- **0.1 ~~Resolve the public/private question~~ — DECIDED 2026-09-09: stay public,
  names allowed, nothing scrubbed.** No renames, no history rewrite, no CI name scan.
  The one exception is `docs/reference/researcher_assignments.json`, now gitignored —
  not for the names but because it is a regenerable cache of an internal sheet and
  carries that sheet's id; `coverage_audit_researcher.py` re-fetches it over the
  read-only `gws-gem` profile. This closes the finding rather than fixing it.
- **0.2 Land the backlog in reviewable commits**, separated into three trains:
  (a) research outputs/staging/deliverables, (b) pre-existing code+doc changes,
  (c) Codex's infrastructure work. Never mixed — (c) is the only one that can be
  cleanly reverted later.
- **0.3 Fix `tests/test_validate_records.py`** to assert the new fail-closed behavior.
- **0.4 Decide Codex's changes** (see Part 5). Default recommendation: **keep**. The
  output-exists guard and fail-closed gates enforce rules `CLAUDE.md` already declares;
  they are the audit's best work and they are already written.

### Phase 1 — Make the top invariants executable

- **1.1 Bind citations to verification evidence.** Highest-value change in the whole plan.
  Make `URL_VERIFIER_LOG` mandatory during a batch; have `build_review_package.py` require,
  for every URL in a `[ref]` lane, a passing log record whose token matches the asserted
  value; fail the build otherwise. This converts the repo's most important rule from an
  honour system into a gate.
- **1.2 Keep and test the fail-closed gates — DONE 2026-09-09.**
  `tests/test_build_gates.py` (11 tests) drives `build_review_package.py` end to end as a
  subprocess against a synthetic mini-CSV and asserts, for each gate, both the exit code
  and that no workbook was written; `tests/test_staging_qc_gate.py` (6 tests) asserts
  `staging_qc.main()`'s *return value*, since the exit code is the only part a caller can
  act on. Suite: 81 → 98.

  Writing them found two real defects, both now fixed:

  1. **Malformed staging crashed instead of gating.** A `staged_*.json` holding an object
     (or a list of non-objects) was counted as a finding and then handed to the sheet
     builders anyway, which call `.get()` on each record — the build died with an
     `AttributeError` traceback at exit 1, partway through, instead of stopping cleanly at
     `BUILD BLOCKED`. `main()`'s `validate()` helper now returns a *sanitised* list, so a
     malformed input is counted and neutralised; it also counts structural damage itself
     for labels with no `STAGED_KEYS` entry, which `_validate_records` skips.
  2. **`staging_qc.py`'s headline key-schema check was a silent no-op.** It called
     `brp._validate_records(f"{label}({tag})", recs)` — decorating the label with the shard
     name so the offender is attributable — but `_validate_records` resolves its spec by
     `STAGED_KEYS.get(label)`, and a decorated label matches nothing, so it returned 0 for
     **every shard of every region**. This is the 2026-08-11 `argentina.qa.json` failure
     repeated one layer up: the gate that was added to catch a check that counted nothing
     itself counted nothing. It now passes `spec=brp.STAGED_KEYS.get(label)` explicitly.

  Turning that check back on surfaced previously invisible vocabulary drift in six regions
  (africa, americas, europe, middleeast, oceania, vietnam). A sweep of the committed
  staging tree confirmed it is **annotation-only, not data loss**: extra URL lists
  (`corroborating_urls`, `source_urls`, `supporting_urls`) on 14 `monitor_list` records
  that all still carry a `best_lead_url` — **zero monitor rows shipped without a lead URL**
  — plus 15 `wiki_updates` records carrying `source_notes`/`confidence` prose no sheet
  reads. Those are delivered historical batches and their staged JSON is the audit trail,
  so **none of it was rewritten.** One open question left by the scan, deliberately not
  changed here: `new_units` marks `terminal_id` **required**, but a new unit on a
  *newly discovered* terminal has no terminal id yet (`middleeast/oman.disc.newunits.json`).
  That spec will false-positive on every future discovery batch of that shape — decide
  whether the linkage may fall back to `TerminalName` before the next discovery run.
- **1.3 Fix `sop_pointers.md` `--remote` → `--pg` — DONE 2026-09-09**, and the sweep found
  the drift was wider than the audit recorded. Also corrected: `docs/sops/update.md` step 3
  (logged "both the local and `--remote` checks ran"), `scripts/entity_lookup.py`'s own
  module docstring ("run this BARE and with `--remote`" — the script's usage block already
  said `--pg` was authoritative, so it contradicted itself), and the reusable
  `batches/staging/_discovery_brief.md`, which was still instructing every dispatched
  discovery subagent to use `--remote`. Left alone deliberately: `README.md`'s env-var
  table (those cookies really are for the remote endpoint), the per-batch briefs, and the
  run records — frozen artifacts of what was actually run.
- **1.4 Reconcile the workflow count — DONE 2026-09-09.** The drift was narrower than the
  audit recorded: `README.md` ("Nine workflows") and the `CLAUDE.md` router table (nine
  rows) already agreed. The single wrong count was the **`CLAUDE.md` skill frontmatter**,
  which said "five workflows" and enumerated only five — omitting regional sweep,
  ref-sweep, captive-power and georeference, so four of nine were invisible to skill
  routing. Now nine, enumerated, with their trigger phrases. `docs/workflows.md` has ten
  `##` sections but nine workflows — §7 is the cross-project FSRU sync *rule*; its "how the
  workflows fit together" paragraph now says so, and places the three off-spine workflows.

### Phase 2 — State model

- **2.1 Wire the manifest** (`batch_contract.build_manifest` exists) to record export
  SHA-256, header/schema hash, row count, repo commit, and `gem-db-ops` SHA at build time.
- **2.2 Per-lane, per-country state** in `meta.json` — `update`/`discovery`/`qc` each with
  their own completion, never one status for a region. Retire `applied` as a hand-set
  field: derive it from an `apply_check` run, or drop it and stop pretending.
- **2.3 Generate the coverage ledger and run-record index** from metadata. The index is
  two months stale; a generated one cannot be.

### Phase 3 — Environment and CI (cheap, one-time)

- **3.1 Verify `lng doctor`** actually checks what it claims; add the sibling-repo and
  binary checks.
- **3.2 GitHub Actions:** pytest, ruff, `lng validate`, markdown-link check, forbidden-path
  scan (`/Users/`, `/home/claude`, Dropbox paths, retired Heroku host), and a secret scan.
  **No personal-name scan** — names are allowed here by decision (see the header note);
  adding one would fail the build on intended content.
- **3.3 Settle `.env`:** either load it explicitly or change the README to say `source .env`.

### Phase 4 — Selective refactor, evidence-driven only

Do these **only when a concrete failure points at them**:

- ~~Parameterize the captive-power one-off assemblers~~ — **DECIDED 2026-09-09: the
  workflow is finished; the scripts are frozen, not parameterized.** The freeze marker is
  `batches/staging/captive_power/README.md`, which declares all 23 files run artifacts
  rather than tooling and names `batches/staging/_assemble.py` as the canonical assembler.
  This retires Codex's "batch-specific code is proliferating" P1 by scope, not by refactor.
- Split `build_review_package.py` by sheet — *if* a bug is ever traced to its size.
- Move machine-checkable rules (enums, read-only columns, banned domains, confidence
  thresholds) into config the code reads. Leave the rationale prose in place.

### Explicitly not doing

| Recommendation | Why not |
|---|---|
| `src/lng_terminals/` package rewrite | Breaks every SOP command line and recipe; benefit is import hygiene the agent does not need |
| Compressing incident histories into ADRs | Moves working guardrails out of the agent's context path (Part 3) |
| Full `runs/<batch-id>/` relayout | Manifests + atomic writes + locks capture ~90% of the benefit without invalidating every documented path |
| Removing `docs/design_history/` | 596 KB, harmless, and it is the only record of why the scaffolding is shaped this way |
| Git LFS for the GIIGNL PDFs | 53 MB total; LFS adds a failure mode for a non-problem |

---

## Part 5 — Decisions (resolved 2026-09-09)

1. **Public or private?** Going private retires the names finding, the internal-links
   finding, and most of the artifact-classification work in one command. Nothing here
   appears to need public visibility.
2. **If it stays public — fix-forward or rewrite history** for the one committed name?
   A rewrite on a public repo with an existing clone is invasive; fix-forward leaves it
   in history but is honest and cheap.
3. **Codex's half-landed changes: keep, revert, or cherry-pick?** Recommendation: keep,
   fix the test, and commit them as their own train so they stay revertible.
4. **Is the captive-power workflow finished?** It determines whether Phase 4's assembler
   work is worth doing at all, or whether those 23 files should simply be frozen.
