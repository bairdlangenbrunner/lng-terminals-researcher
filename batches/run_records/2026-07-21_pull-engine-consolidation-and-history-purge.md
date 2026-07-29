# 2026-07-21 — pull-engine consolidation + GitHub history purge

## Plan

1. Remove the three pull-engine script copies (`gem_query.py`, `gem_all_fields.py`,
   `gem_export_via_web.py`) from this repo; the engine's single home is the sibling
   private repo `../gem-db-ops`. Repoint every doc/script.
2. Commit via branch → PR → merge (PR #30).
3. Rewrite this public repo's GitHub history to drop the engine scripts everywhere,
   scrub researcher names, and replace the internal project-db host with a
   placeholder; force-push.

## Status / outcome

- **Consolidation: done** (PR #30 merged). `pull_gem_db.py` stays, map-only. The
  canonical pull is now `python ../../gem-db-ops/gem_query.py --all-fields lng -o
  gem_export.csv && python pull_gem_db.py --map-only` from `scripts/`.
  `captive_power_colocation.py` got a local read-only engine helper;
  `entity_lookup.py`'s remote host moved to the `GEM_PROJECT_DB_BASE_URL` env var.
  Smoke-tested end-to-end (1,272 rows + 115-col map).
- **History rewrite: done locally, verified clean** (git-filter-repo on a bare
  clone: engine paths removed from all commits; researcher names and the internal
  host scrubbed from all blobs; only placeholder credentials anywhere). Local
  `main` and the temp ref `purged-country-notes` carry the rewritten history.
  Pre-purge backup bundle: `../lng-terminals-researcher.pre-purge-2026-07-21.bundle`.
- **Force-push: done** (user ran it; both remote heads — `main` and
  `country-notes-from-chatgpt-audit` — now carry only rewritten history; temp refs
  deleted, remote-tracking pruned). Old commits can remain reachable on GitHub via
  merged-PR refs and existing clones — a true purge needs a GitHub Support request.
- gem-db-ops docs updated to single-source-of-truth wording (pushed direct to its
  main). `.env.example` here rewritten around the env-var host.
