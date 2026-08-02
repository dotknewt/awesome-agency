# hooks-toolkit

Composable safety and hygiene hooks for Claude Code. Each hook is a self-contained bash script; install only what you need.

## Hooks

| Script | Event | What it does |
|---|---|---|
| `block-force-push-main.sh` | PreToolUse(Bash) | Blocks `git push --force[--with-lease]` targeting `main`/`master` |
| `secret-scan-on-write.sh` | PreToolUse(Write\|Edit) | Blocks writes containing AWS keys, GitHub tokens, or PEM private keys |
| `validate-manifest-hook.sh` | PostToolUse(Write\|Edit) | Validates `plugin.json`/`marketplace.json` via `validate-plugin-json.sh` |
| `validate-skill-hook.sh` | PostToolUse(Write\|Edit) | Validates `SKILL.md` frontmatter via `validate-skill-frontmatter.sh` |
| `branch-check-session-start.sh` | SessionStart | Warns if the current branch's PR has already merged |
| `inject-branch-rules.sh` | UserPromptSubmit | Injects branch hygiene rules when prompt mentions PRs or branching |
| `commit-checklist.sh` | Stop | Nudges to commit/push if working tree is dirty |

## Shared validators

Two scripts under `scripts/` work standalone (no hook context needed):

```bash
./scripts/validate-plugin-json.sh plugins/my-plugin/.claude-plugin/plugin.json
./scripts/validate-skill-frontmatter.sh skills/my-skill/SKILL.md
```

These are also called from the CI workflow (`.github/workflows/validate.yml`).

## Installation

### Option A: Enable the full plugin

Add `hooks-toolkit@agency` to `enabledPlugins` in your `settings.json`. All hooks activate automatically.

### Option B: Pick individual hooks

Run `/install-hook <hook-name>` (or `/install-hook <hook-name> --global`) to wire a single hook into your settings file. See the command for the full list.

### Option C: Manual wiring

Copy the relevant entry from `hooks/hooks.json` into the `hooks` object in your `.claude/settings.json`. Replace `${CLAUDE_PLUGIN_ROOT}` with the absolute path to this directory.

## Testing a hook manually

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"git push --force origin main"}}' \
  | bash scripts/block-force-push-main.sh
echo "exit: $?"
```

Exit 0 = allowed, Exit 2 = blocked (stderr fed back to Claude).
