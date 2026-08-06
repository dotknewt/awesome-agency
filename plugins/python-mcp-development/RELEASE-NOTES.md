# Python MCP Development Release Notes

## v1.0.1 (2026-08-06)

### Agents

- **Pinned `python-mcp-expert`'s `model` to a full ID instead of `inherit`.**
  The shared `agent-model-assignment` convention no longer treats `inherit` as
  a valid value — an agent whose model silently tracked the calling session
  couldn't be reasoned about from the file alone. Since the agent's job is
  generating whole MCP server artifacts from an ambiguous brief, it now pins
  `claude-opus-5`.

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
