# GitHub Toolkit Release Notes

## v1.1.5 (2026-08-06)

### Fixes

- **Instruction files are scoped to this bundle instead of the whole shared pool.**
  `plugins/github-toolkit/instructions` and the `issue-filer` agent both symlinked
  the entire repo-level `instructions/` pool. When that pool was repurposed for
  generic Copilot instruction files, the bundle silently started shipping ten
  unrelated documents and lost the three its own content actually reads —
  `branch-hygiene.md`, `commit-vs-pr.md`, and `issue-instruction.md`. Those are
  restored under `instructions/github-toolkit/`, mirroring the per-bundle
  `commands/<bundle>/` convention, and the symlinks now point there.
- **`github-workflow` references resolve in both install modes.** The skill pointed
  at repo-absolute `plugins/github-toolkit/instructions/...` paths, which resolve on
  a checkout of this repository and nowhere else. They now use
  `${CLAUDE_PLUGIN_ROOT}/instructions/...`, and the same directory is symlinked into
  the skill so its standalone micro-install resolves too.

## v1.1.4 (2026-08-06)

Initial release notes, reconstructed from git history. Earlier versions shipped
without notes.

### Agents

- **`branch-warden` and `issue-filer` load from the symlink bundle.** Both are
  listed explicitly in `plugin.json`; Claude Code's default `./agents/` scan skips
  file-level symlinks, so neither agent loaded before.
- **`issue-filer`'s solo install carries its own taxonomy guidance.** Installed on
  its own, `${CLAUDE_PLUGIN_ROOT}` resolves to the agent's directory, so the label
  taxonomy instruction is symlinked alongside it.

### Commands

- **The commands pool is a per-bundle directory.** `commands` is symlinked as a
  whole directory (`commands → ../../commands/github-toolkit`) so Claude Code's
  default scan walks real files; per-file symlinks were skipped.

### Skills

- **Issue labels are read from a checked-in default set.** `create-issue-template`
  previously invented labels, producing inconsistent taxonomies across repos. It now
  reads the canonical nine from `references/label-defaults.yml` and only creates
  labels that are missing.
