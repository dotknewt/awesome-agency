---
description: Wire a hooks-toolkit hook into the user's Claude Code settings.json
argument-hint: "<hook-name> [--global]"
allowed-tools: ["Read", "Edit", "Write", "Bash", "AskUserQuestion"]
---

# /install-hook

Wire a named hook from `hooks-toolkit` into the user's Claude Code `settings.json`.

## Available hooks

| Hook name | Event | What it does |
|---|---|---|
| `block-force-push-main` | PreToolUse | Blocks `git push --force` to main/master |
| `secret-scan` | PreToolUse | Blocks writes containing likely secrets (AWS keys, GitHub tokens, private keys) |
| `validate-manifest` | PostToolUse | Validates `plugin.json`/`marketplace.json` after edits |
| `validate-skill` | PostToolUse | Validates `SKILL.md` frontmatter after edits |
| `branch-check` | SessionStart | Warns if current branch's PR has already merged |
| `inject-branch-rules` | UserPromptSubmit | Injects branch hygiene rules when user mentions PRs/branching |
| `commit-checklist` | Stop | Nudges to commit if working tree is dirty |

## Instructions

**Arguments:** `$ARGUMENTS`

1. Parse `$ARGUMENTS`:
   - First token is the hook name (required).
   - `--global` flag means write to `~/.claude/settings.json`; otherwise use `.claude/settings.json` in `$CLAUDE_PROJECT_DIR`.

2. If no argument, ask the user which hook to install using AskUserQuestion with the table above as options.

3. Determine the settings file path:
   - `--global`: `~/.claude/settings.json`
   - project: `$CLAUDE_PROJECT_DIR/.claude/settings.json` (create if missing)

4. Read the current settings.json (or start from `{}`).

5. Look up the hook's event and command from this map:

   ```
   block-force-push-main  → PreToolUse / Bash matcher     / block-force-push-main.sh
   secret-scan            → PreToolUse / Write|Edit matcher / secret-scan-on-write.sh
   validate-manifest      → PostToolUse / Write|Edit matcher / validate-manifest-hook.sh
   validate-skill         → PostToolUse / Write|Edit matcher / validate-skill-hook.sh
   branch-check           → SessionStart / (no matcher)   / branch-check-session-start.sh
   inject-branch-rules    → UserPromptSubmit / (no matcher) / inject-branch-rules.sh
   commit-checklist       → Stop / (no matcher)           / commit-checklist.sh
   ```

   The command to insert is:
   ```
   bash <PLUGIN_ROOT>/scripts/<script-name>
   ```
   Where `<PLUGIN_ROOT>` is the resolved path to `plugins/hooks-toolkit` in this repo.
   Use `${CLAUDE_PLUGIN_ROOT}` if the user is enabling the plugin system-wide; use the absolute path to the script if wiring into a standalone settings file.

6. Merge the new hook entry into the existing `hooks` object in settings.json. Do not remove existing entries. Append to the event's array if it already exists.

7. Write the updated settings.json.

8. Confirm: "Installed `<hook-name>` hook into `<settings-file>`. Restart Claude Code for the hook to take effect."

9. Remind the user: hooks are loaded at session start — a restart is required.
