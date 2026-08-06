# Python MCP Development Release Notes

## v1.0.0 (2026-08-06)

Initial release. Notes reconstructed from git history.

### Skills

- **`python-mcp-server-generator` scaffolds a whole working server, not a snippet.**
  The common failure when starting an MCP server is not the tool definitions but the
  surrounding wiring — transport, lifespan, packaging. The skill generates the
  project so the first run succeeds.

### Agents

- **`python-mcp-expert` ships alongside the generator.** Generated projects raise
  follow-up questions the skill cannot answer inline, and the agent carries the SDK
  and FastMCP knowledge needed to answer them without re-reading the docs each time.

### Instructions

- **`python-mcp-server.instructions.md` is symlinked from the shared pool.** The
  same guidance applies outside this plugin, so it lives in the repo-level pool and
  is scoped into the bundle by a single-file symlink rather than copied.
