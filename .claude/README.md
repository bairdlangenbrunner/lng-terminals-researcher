# `.claude/` — Claude Code configuration

This directory holds the [Claude Code](https://docs.claude.com/en/docs/claude-code)
configuration for this project. The only file committed here is `settings.json`,
the **shared team baseline** for tool permissions.

## `settings.json` — what it does

```json
{
  "permissions": {
    "defaultMode": "acceptEdits",
    "allow": [ "Bash", "Read", "Write", "Edit", ... ]
  }
}
```

- **`defaultMode: "acceptEdits"`** — Claude auto-accepts file edits and writes in
  the project without prompting. This is the most permissive *standard* mode; it
  is **not** the "dangerously bypass" mode (`bypassPermissions`), so a `deny` list
  is still honored if one is ever added.
- **`allow` list** — tools/commands that run without a confirmation prompt. A bare
  tool name with no parentheses (e.g. `"Bash"`) matches **every** use of that tool,
  so `"Bash"` means *any* shell command runs unprompted. Entries like
  `"Bash(python3 *)"` would instead allow only matching commands.

In short: with this config Claude will edit files and run shell commands during a
batch without stopping to ask. That speed is the point — the whole workflow is
"produce a staging xlsx," and the hard rule that Claude **never writes to the live
GEM database** lives in `CLAUDE.md`, not in this permission layer.

## How settings layer (precedence, highest wins)

1. Enterprise managed policy (`managed-settings.json`) — if your org pushes one
2. Command-line flags
3. `.claude/settings.local.json` — **personal, gitignored, never committed**
4. `.claude/settings.json` — **this file, shared/committed**
5. `~/.claude/settings.json` — your user-global settings

Settings are **merged**, not replaced: a higher layer wins on conflicting scalar
keys (like `defaultMode`), while permission `allow`/`deny`/`ask` lists
**accumulate** across all layers. `deny` always beats `allow` at any level.

## Making it less (or more) permissive for yourself

Don't edit `settings.json` for a personal preference — that changes the shared
baseline for everyone. Instead create your own `.claude/settings.local.json`
(gitignored), which overrides this file for you only. For example, to require a
prompt before shell commands while keeping auto-edits:

```json
{
  "permissions": {
    "defaultMode": "acceptEdits",
    "deny": [ "Bash" ]
  }
}
```

## What is / isn't committed in `.claude/`

| Path | Committed? | Purpose |
|---|---|---|
| `settings.json` | yes | Shared team permission baseline |
| `README.md` | yes | This file |
| `settings.local.json` | no (gitignored) | Your personal overrides |

Secrets are never stored here — GEM auth cookies live in `.env`, which is
separately gitignored.
