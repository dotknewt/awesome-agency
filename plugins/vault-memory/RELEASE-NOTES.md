# vault-memory Release Notes

## v1.1.0 (2026-08-18)

Adds `/vault-init`, the bootstrap step this bundle was missing: on install,
nothing previously created `vault/INDEX.md` or `vault/_templates/*`, even
though `/vault-save` and `vault-conventions` both assume they already exist.
`/vault-init` copies a starter `vault/` (ported from `dotknewt/vault-warden`,
under the new `templates/` directory) into the host project and appends a
Project Memory section to its `AGENTS.md`, idempotently. Also fixes
`hooks/session-start.sh`'s missing-vault detection, which checked only for
the `vault/` directory: `session-capture.mjs`'s `Stop` hook creates
`vault/sessions/` on the very first session end, which was silently masking
an uninitialized vault (no `INDEX.md`) as "present". The check now looks for
`vault/INDEX.md` instead.

## v1.0.0 (2026-08-18)

Initial release. Imports the project-local vault-memory setup (previously
developed directly under this repo's `.claude/`) into the marketplace as a
redistributable bundle: skills, agents, hooks, workflows, and the bundled
`obsidian` MCP server (`@bitbonsai/mcpvault`), with all internal references
switched from `.claude/...` to `${CLAUDE_PLUGIN_ROOT}` so the bundle installs
cleanly into any project.
