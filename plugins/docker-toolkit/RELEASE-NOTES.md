# Docker Toolkit Release Notes

## v0.1.3 (2026-08-06)

Initial release notes, reconstructed from git history. Earlier versions shipped
without notes.

### Agents

- **`dockerize-mcp-server` resolves its references through `${CLAUDE_PLUGIN_ROOT}`.**
  The agent pointed at repo-relative paths for its skill and reference docs, which
  only existed on a checkout of this repository — an installed copy could not read
  them. All references now go through `${CLAUDE_PLUGIN_ROOT}`.
- **The agent's solo install is self-contained.** `dockerize-mcp-server` is also
  installable on its own, where `${CLAUDE_PLUGIN_ROOT}` resolves to the agent's own
  directory rather than the bundle root. Its `dockerize-mcp-server` and
  `multi-stage-dockerfile` skills are symlinked alongside it so the same paths
  resolve in both install modes.
- **The agent loads from the symlink bundle.** Listed explicitly in `plugin.json`
  because Claude Code's default `./agents/` scan skips file-level symlinks.

### Skills

- **`multi-stage-dockerfile` split out from the MCP packaging skill.** Multi-stage
  builds are useful well beyond MCP servers, and bundling the two forced anyone
  wanting build guidance to load the packaging workflow too.
