---
description: >
  Pin selected active plugins from user settings into project settings so they install on clone.
  Use when the user wants to make plugins follow the repository, sync plugin config to the repo,
  pin plugins to project settings, or ensure plugins install automatically for all contributors.
  Triggers on phrases like "add plugins to project settings", "make plugins follow the repo",
  "sync my plugins to this project", "pin plugin config", or "update project settings with plugins".
argument-hint: "[--prune]"
allowed-tools: ["Read", "Write", "Bash", "AskUserQuestion"]
---

# /pin-plugins

Sync selected user-enabled plugins into this project's `.claude/settings.json` so they install
automatically on clone.

**Arguments:** `$ARGUMENTS`

## Overview

Claude Code tracks plugin enablement in two places:
- **User scope**: `~/.claude/settings.json` — what YOU have enabled globally.
- **Project scope**: `.claude/settings.json` — what the repo declares, committed and shared with cloners.

This command reads both, lets you pick which user-enabled plugins to pin to the project, and writes
the result to `.claude/settings.json`. Third-party marketplace registrations are copied along with
their plugins automatically.

If `--prune` is passed, also offer to remove project-pinned entries that are no longer enabled at
user scope.

---

## Steps

### 1. Parse arguments

Check `$ARGUMENTS` for `--prune`. If present, set prune_mode = true.

### 2. Read settings

Run these two reads in parallel:

```bash
cat ~/.claude/settings.json
```

```bash
cat .claude/settings.json 2>/dev/null || echo '{}'
```

From **user settings**, extract:
- `enabledPlugins` — object of `"plugin@marketplace": bool`; filter to entries with value `true`.
- `extraKnownMarketplaces` — object of marketplace entries (may be absent; treat as `{}`).

From **project settings**, extract the same two keys (may be absent; treat as `{}`).

### 3. Compute candidates

**To pin** (new to project):
- User-enabled plugins (`value === true`) that are NOT already present with `true` in project `enabledPlugins`.

**Already pinned** (for information):
- Plugins present in both user and project with `true`. List them briefly — no action needed.

**Stale in project** (only if `--prune`):
- Plugins present in project `enabledPlugins` with `true` that are NOT present in user `enabledPlugins`
  with `true` (either absent or set to `false`).

If there are no candidates to pin (and no stale entries in prune mode), report:
> "Nothing to pin — all user-enabled plugins are already in project settings."
and stop.

### 4. Ask the user which to pin

Build the options list for `AskUserQuestion`. For each candidate plugin `plugin@marketplace`:
- Label: `plugin@marketplace`
- Description: indicate whether the marketplace is `claude-plugins-official` (no extra config needed)
  or a third-party one from `extraKnownMarketplaces` (will be copied automatically).

Use **multiSelect: true**. Include an option "None — cancel" if you want to allow bailing out without
changes.

If `--prune` and there are stale project entries, ask a **second question** (separate `AskUserQuestion`
call) listing the stale entries and asking which to remove, also multiSelect.

### 5. Merge into project settings

Read the full project settings JSON (preserve all existing keys). Then:

**For each selected plugin to pin:**
- Set `projectSettings.enabledPlugins["plugin@marketplace"] = true`.
- Determine the marketplace name (the part after `@`).
- If the marketplace is NOT `claude-plugins-official` AND the marketplace key exists in user
  `extraKnownMarketplaces` AND it is NOT already in project `extraKnownMarketplaces`:
  - Copy `userSettings.extraKnownMarketplaces[marketplace]` into
    `projectSettings.extraKnownMarketplaces[marketplace]`.

**If pruning** (for each stale entry the user selected to remove):
- Delete `projectSettings.enabledPlugins["plugin@marketplace"]`.
- If no remaining project plugin references that marketplace, remove its entry from
  `projectSettings.extraKnownMarketplaces` too (to keep the file clean).

Write the updated settings back to `.claude/settings.json`. Preserve key ordering of unchanged fields;
add `enabledPlugins` and `extraKnownMarketplaces` near the end if they are new keys.

### 6. Report and remind

Show a compact diff summary:
```
Pinned to .claude/settings.json:
  + steward@awesome-agency
  + github-toolkit@awesome-agency
  (marketplace awesome-agency added to extraKnownMarketplaces)

Removed (--prune):
  - old-plugin@claude-plugins-official

Next: git add .claude/settings.json && git commit -m "chore: pin plugins to project"
```

If nothing was selected (user chose "None"), report that no changes were made.

---

## Notes

- Only `true`-valued user entries are considered for pinning; `false` entries mean explicitly disabled.
- The `claude-plugins-official` marketplace is implicit in Claude Code — never write it to
  `extraKnownMarketplaces`.
- This command only operates at the **plugin** level. Individual agents, skills, or commands within a
  plugin cannot be selectively enabled via settings — that is controlled by the plugin author.
- `.claude/settings.json` is committed; `.claude/settings.local.json` is gitignored and is not
  touched by this command.
