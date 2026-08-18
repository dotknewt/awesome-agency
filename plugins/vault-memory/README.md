# vault-memory

Durable project memory in a git-native vault, so knowledge survives across
sessions and compaction instead of being rediscovered every time.

Bundles a note taxonomy and lifecycle (`kb/` atomic knowledge + ADRs, `docs/`
Diátaxis docs, `sources/` provenance notes, plus `plans/` and `sessions/`
history), a structural linter enforced on every write, retrieval/curation/
research subagents, and the [`mcpvault`](https://github.com/bitbonsai/mcpvault)
MCP server so notes are addressable both as files and via MCP tools.

Components:
- Skills: `vault-conventions` (authoritative schema/lifecycle rules, loaded
  automatically for vault writes), `vault-find`, `vault-save`, `vault-session`,
  `vault-review`
- Agents: `vault-librarian` (read-only retrieval), `vault-curator` (review and
  curation), `vault-researcher` (web research → provenance-bearing source notes)
- Workflows: `vault-audit` (bulk review sweep), `vault-research` (multi-source
  research → kb)
- Hooks: `SessionStart` briefing, `Stop`/`PostCompact`/`SessionEnd` session
  capture, `PreToolUse`/`PostToolUse` vault linting
- MCP server: `obsidian` (`@bitbonsai/mcpvault`, rooted at `vault/` in the
  host project)

## Usage

Install: `claude plugin install vault-memory@awesome-agency`

This bundle is Claude Code-only: its hooks use the Claude-only `PostCompact`
event (to capture a session note after compaction), and GitHub Copilot CLI
does not auto-start a plugin-bundled `.mcp.json`. Copilot users can still add
the server manually: `claude mcp add obsidian -- npx -y @bitbonsai/mcpvault@0.16.0 ./vault`
(or the Copilot CLI equivalent), run from the project root.

Run `/vault-init` once per project to scaffold `vault/` (INDEX, note
templates, empty folders) and append a Project Memory section to
`AGENTS.md` — it's idempotent, safe to re-run. After that, use `/vault-find
<topic>` before non-trivial work, `/vault-save` to persist a decision or
gotcha, `/vault-session` before compacting or ending a session, and
`/vault-review` (or the `vault-audit` workflow for >40 candidates) to curate
stale or duplicate notes. See the `vault-conventions` skill for the full
schema.

## Manual settings

`/vault-init` does not touch `.claude/settings.json` — merge these in yourself
if desired:
- `permissions.allow`: `"mcp__obsidian__*"` (and a Bash allow-entry for
  `vault-lint.mjs` if you want to run the linter manually).
- `plansDirectory: "vault/plans"` so plan-mode output lands in the vault.
- `autoMemoryEnabled: false` so nothing about the project is duplicated into
  user-global memory (project memory lives in `vault/` instead).
