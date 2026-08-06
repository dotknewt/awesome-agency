# Agent Ember Release Notes

## v1.0.3 (2026-08-06)

Initial release notes, reconstructed from git history. Earlier versions shipped
without notes.

### Agents

- **The `ember` agent loads reliably from the symlink bundle.** The bundle ships its
  agent as a symlink into the shared `agents/` pool, and Claude Code's default
  `./agents/` scan skips file-level symlinks, so the agent never loaded. It is now
  listed explicitly in `plugin.json`, which follows symlinks.

### Skills

- **The four `from-the-other-side-*` perspective skills ship with the agent.**
  Ember's value is in the perspective shift, which needs the companion narratives
  present at install time rather than fetched on demand.
