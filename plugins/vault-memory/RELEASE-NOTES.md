# vault-memory Release Notes

## v1.2.0 (2026-08-18)

### Fixes

- **`/vault-init` now actually ships the `vault/` scaffold it copies.** v1.1.0's
  note says the starter vault was ported "under the new `templates/` directory",
  but the repo's `.gitignore` had an unanchored `vault/` rule (meant for a
  root-level vault of this repo), so `plugins/vault-memory/templates/vault/` was
  never committed and the installed 1.1.0 bundle contained only
  `templates/AGENTS-section.md`. `/vault-init` therefore produced a `vault/`
  with no `INDEX.md`, `_templates/` or `.obsidian/` — observed in two consumer
  projects (`photo-pipeline`, `vault-warden`), where `vault/` held only the
  `sessions/` folder the Stop hook creates. The ignore rules are now anchored to
  `/vault/` and the 17 scaffold files (`INDEX.md`, `README.md`, `_templates/*`,
  `_bases/review-due.base`, the three shared `.obsidian/*.json`, and the empty
  folder markers) are tracked.

### Note taxonomy

- **New `reference/` note class for pipeline-generated corpora.** A project that
  ingests an external corpus (spec: an agent-oriented knowledge base built from
  Microsoft's Defender XDR advanced-hunting docs — 1,643 per-column notes at
  `reference/defender-xdr/<table>/<ColumnName>.md`) cannot live under the
  existing rules: the PreToolUse guard denied a top-level folder outside the
  taxonomy, more than two folder levels, non-kebab filenames (`AccountUpn.md`)
  and duplicate basenames (`Timestamp.md` exists in 48 tables), and `--all`
  reported every duplicate as an error. Flattening paths or renaming columns was
  rejected because the corpus's IDs are semantic and must map to deterministic
  paths. `vault-lint.mjs` now accepts `reference/` (`type: reference`,
  required `source_url`, `license`, `commit`, `retrieved`, `modified`; `status`
  ∈ `active|deprecated|archived`), exempts that subtree from the depth,
  kebab-case and unique-basename checks (filenames must still match
  `[A-Za-z0-9_][A-Za-z0-9_-]*.md`), keeps its notes out of the vault-wide
  basename map, and resolves `[[reference/…/Name]]` links by path — because
  basenames repeat there by design, corpus notes are addressed by path only,
  never by `[[basename]]`. `kb|docs|sources|archive` rules are unchanged, and
  the `delete_note` guard still applies everywhere. `vault-conventions` §1a
  documents the class (pipeline-owned, never hand-edited, never in default
  search); `"reference"` was added to every documented `excludePaths` default
  (conventions, `vault-save`, `vault-librarian`, `vault-audit`, the AGENTS
  section) so an ad-hoc `search_notes` does not surface thousands of generated
  notes.

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
