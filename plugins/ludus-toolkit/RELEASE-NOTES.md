# Ludus Toolkit Release Notes

## v0.1.0 (2026-08-06)

Initial release notes, reconstructed from git history. Earlier versions shipped
without notes.

### MCP

- **The Ludus MCP server runs through the Docker MCP Gateway.** Earlier docs
  described a direct node invocation, which made every user responsible for
  installing and pinning the server's toolchain. `.mcp.json` now launches
  `docker mcp gateway run` against the bundled catalog at
  `${CLAUDE_PLUGIN_ROOT}/mcp/ludus/ludus-catalog.yaml`, so the server ships with
  the plugin and its dependencies stay contained.

### Skills

- **Four skills split by task rather than by API surface.** `ludus-cli`,
  `ludus-range-config`, `ludus-environment-guide`, and `ludus-troubleshoot` are
  separated so a config question does not load CLI reference material and vice
  versa — the combined document was large enough to crowd out the actual task.
