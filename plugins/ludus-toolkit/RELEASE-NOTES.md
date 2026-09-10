# Ludus Toolkit Release Notes

## v0.4.2 (2026-09-10)

### Template Naming

- **Canonical template names now satisfy DNS naming constraints.** Underscores
  in compound releases and qualifiers could produce unusable DNS names; the
  naming, OS-update, and locale-change skills now use `11-22h2` and
  `no-security-updates`, while retaining dotted numeric releases. The validator
  enforces label boundaries, 63-character labels, and the 253-character total
  limit on supplied basenames and built names including `-template`. Regression
  coverage preserves FLARE identities and excluded Windows metadata while
  exercising the new parser and DNS limits.

## v0.4.1 (2026-09-10)

### Windows Naming

- **Windows template naming now preserves identity while filtering incidental metadata.** The naming, locale-change, and OS-update skills keep the FLARE identity, suppress incidental Windows metadata fields, and retain genuine TPM distinctions. The validator regressions cover naming syntax; corpus review remains a model dry run rather than workflow coverage.

## v0.4.0 (2026-09-10)

### Skills

- **Ludus OS templates now have one canonical, machine-checkable naming
  grammar.** Legacy names used the same short tokens for locale and feature
  meaning and varied field order by OS family, making maintenance workflows
  prone to silent misclassification. The new `ludus-template-naming` skill and
  dependency-free validator require explicit final locales, semantic field
  ordering, and unambiguous separators; the locale-change and OS-update skills
  now reconstruct that form instead of preserving legacy positions.

## v0.3.0 (2026-09-09)

### OpenCode

- **The full toolkit can now be installed into OpenCode projects without
  retaining this repository or relying on Claude Code's plugin loader.** The
  project-local installer dereferences all six pooled skill directories,
  preserves their supporting references, and safely merges a direct Docker
  stdio MCP definition while refusing conflicting or comment-bearing configs.
  The setup guide covers credentials, container networking, authenticated
  verification, and uploads, and CI validates both installation behavior and
  generated configuration against OpenCode's published schema.

## v0.2.0 (2026-09-09)

### Skills

- **OS template maintenance now has focused workflows for release updates and
  keyboard-layout changes.** These operations require different validation and
  rename rules than general Ludus range management, so
  `update-os-template` and `change-template-input-language` provide targeted
  guidance without expanding the broader CLI and configuration skills.

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
