# `.claude/` — Claude Code configuration

This repo intentionally commits **no** `settings.json` permission baseline.
Permissions inherit from the user-global Claude Code settings
(`~/.claude*/settings.json`), the same as the sibling researcher repos
(lng-carriers, pipelines, refineries) — kept identical on purpose so no repo
prompts differently from the others (settled 2026-07-16; a committed `ask`
rule here used to make only this repo prompt on `git push`).

Personal per-machine overrides go in `.claude/settings.local.json`
(gitignored, never committed). Settings layer as: enterprise policy → CLI
flags → `settings.local.json` → this repo's `settings.json` (absent) →
user-global.

The guardrails that matter for this project are not permission rules: the
"never write to the live GEM database" rule and the staging-xlsx workflow
live in `CLAUDE.md`. Secrets (GEM auth cookies) live in `.env`, which is
gitignored and denied to Claude's Read tool at the user-global layer.
