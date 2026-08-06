# Agent Doublecheck Release Notes

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
