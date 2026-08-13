# Memory MCP Release Notes

## v0.1.0 (2026-08-13)

Initial release.

### MCP

- **Vendors the official MCP reference "Knowledge Graph Memory Server"**
  (`@modelcontextprotocol/server-memory` 0.6.3, pinned to upstream commit
  `fd8248e56b822cc16a74b6610a88141fdfa09bd6`) **as a Docker image run through
  the Docker MCP Gateway** — same pattern as `ludus-toolkit`'s bundled server.
  No secrets or connection config needed; the server is fully local and makes
  no network calls. The knowledge graph persists to a named Docker volume
  (`memory-mcp-data:/data`, `MEMORY_FILE_PATH=/data/memory.jsonl`) so it
  survives container restarts and image rebuilds.
- **On Docker MCP Toolkit v0.43.3+, the bundled `.mcp.json` cannot
  auto-launch.** The CLI now refuses any `file://` catalog reference that
  doesn't resolve inside `~/.docker/mcp/catalogs/`, and `${CLAUDE_PLUGIN_ROOT}`
  can never point there — the same restriction affects `ludus-toolkit`'s
  bundled server on this CLI version. `mcp/memory/README.md` documents a
  verified manual workaround (copy the catalog once, register with
  `claude mcp add` directly).
