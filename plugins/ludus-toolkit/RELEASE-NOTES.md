# Ludus Toolkit Release Notes

## v0.1.1 (2026-08-06)

### Packaging

- **The MCP server now lives inside the bundle instead of the shared `mcp/`
  pool.** The pool held exactly one server, so the indirection bought nothing
  and made the bundle's `.mcp.json` a symlink that broke the moment the pool
  moved. `mcp/ludus/` is now real files under `plugins/ludus-toolkit/mcp/ludus/`.
  No behaviour changes — `${CLAUDE_PLUGIN_ROOT}/mcp/ludus/ludus-catalog.yaml`
  resolves exactly as before — but installed marketplaces fetch different files,
  so this needs a version of its own.

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
