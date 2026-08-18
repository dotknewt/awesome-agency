# vault-memory Release Notes

## v1.0.0 (2026-08-18)

Initial release. Imports the project-local vault-memory setup (previously
developed directly under this repo's `.claude/`) into the marketplace as a
redistributable bundle: skills, agents, hooks, workflows, and the bundled
`obsidian` MCP server (`@bitbonsai/mcpvault`), with all internal references
switched from `.claude/...` to `${CLAUDE_PLUGIN_ROOT}` so the bundle installs
cleanly into any project.
