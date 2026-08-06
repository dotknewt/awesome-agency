# Agent Doublecheck Release Notes

## v1.0.3 (2026-08-06)

### Agents

- **The `doublecheck` agent now carries its own copy of the `doublecheck` skill.**
  The agent's whole pipeline is defined in that skill, but only the bundle linked
  it — so installing the agent on its own (`doublecheck-agent`) produced an agent
  instructed to follow a procedure it could not read. The skill is now linked into
  the agent's source directory, and the agent references it through
  `${CLAUDE_PLUGIN_ROOT}` so the path resolves for both install shapes.

## v1.0.2 (2026-08-06)

Initial release notes, reconstructed from git history. Earlier versions shipped
without notes.

### Agents

- **The `doublecheck` agent loads reliably from the symlink bundle.** This bundle
  ships its agent as a symlink into the shared `agents/` pool, and Claude Code's
  default `./agents/` directory scan skips file-level symlinks — so the agent
  silently failed to load. It is now listed explicitly in `plugin.json`, which uses
  the custom-file loading path that does follow symlinks.
- **Model tier retuned.** The verification pipeline is a read-and-extract workload,
  so the agent was moved off the default tier to keep routine claim-extraction runs
  cheap.
