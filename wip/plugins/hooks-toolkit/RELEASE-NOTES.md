# Hooks Toolkit Release Notes

## v1.0.1 (2026-08-06)

Initial release notes, reconstructed from git history. Earlier versions shipped
without notes.

### Hooks

- **Hook scripts are reached through `${CLAUDE_PLUGIN_ROOT}/scripts/`.** Hook
  commands run with the user's working directory, not the plugin's, so any
  relative path in `hooks.json` broke on install. Every command now resolves through
  `${CLAUDE_PLUGIN_ROOT}`, and `scripts` is symlinked as a whole directory so the
  real files are present after install.
- **The composable set covers the mistakes that are expensive to undo:** force-push
  to `main` (blocked at `PreToolUse`), secrets written into files (scanned on
  `Write`/`Edit`), malformed `plugin.json` and `SKILL.md` (validated on
  `PostToolUse`), and finishing a turn on a dirty tree or the wrong branch
  (`Stop` and `SessionStart` nudges).

### Commands

- **`commands` is symlinked as a directory, not per file.** Claude Code's default
  command scan skips file-level symlinks, so `/install-hook` did not appear.
