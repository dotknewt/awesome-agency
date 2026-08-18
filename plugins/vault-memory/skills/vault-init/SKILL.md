---
name: vault-init
description: Set up the vault/ memory scaffold and wire it into this project's AGENTS.md. Run once when adopting the vault-memory plugin in a project. Idempotent — safe to re-run.
user-invocable: true
---
# /vault-init — bootstrap the vault (runs in the main context)

Set up the project vault for the vault-memory plugin. Follow these steps exactly, in order, and report a short summary at the end.
Everything below operates relative to `${CLAUDE_PROJECT_DIR:-.}` (the project you're running in), never `${CLAUDE_PLUGIN_ROOT}` (the plugin's own install directory) — the vault must live in the project, not inside the plugin.

1. **Copy the scaffold (idempotent — never overwrite existing files).**
   If `${CLAUDE_PROJECT_DIR:-.}/vault/INDEX.md` already exists, treat the vault as already initialized: skip straight to step 3 and
   report "vault/ already present — skipped scaffold copy, checked AGENTS.md only."
   Otherwise run: `mkdir -p "${CLAUDE_PROJECT_DIR:-.}/vault"`, then copy every file from `${CLAUDE_PLUGIN_ROOT}/templates/vault/` into
   `${CLAUDE_PROJECT_DIR:-.}/vault/` without overwriting anything that already exists there — use
   `cp -Rn "${CLAUDE_PLUGIN_ROOT}/templates/vault/." "${CLAUDE_PROJECT_DIR:-.}/vault/"` (or `rsync -a --ignore-existing` if available).

2. **Verify the copy.** Confirm `vault/INDEX.md`, `vault/_templates/`, `vault/_bases/`, `vault/.obsidian/` and the six empty
   subfolders (`archive/`, `docs/`, `kb/decisions/`, `plans/`, `sessions/`, `sources/`) now exist under `${CLAUDE_PROJECT_DIR:-.}/vault/`.

3. **Append to AGENTS.md, idempotently.** Read `${CLAUDE_PROJECT_DIR:-.}/AGENTS.md` if it exists (create it with just a top-level
   `# AGENTS.md` heading if absent). Check whether it already contains a `## Project Memory` heading — if so, STOP and report
   "AGENTS.md already has a Project Memory section — left untouched" (never duplicate or overwrite). Otherwise, read
   `${CLAUDE_PLUGIN_ROOT}/templates/AGENTS-section.md` and append its exact content verbatim at the end of the target `AGENTS.md`,
   preserving everything already there above it.

4. **Remind the user of manual steps this command does NOT perform** (print this verbatim):
   - The `obsidian` MCP server is auto-registered by this plugin's `.mcp.json` — approve it when Claude Code prompts on next
     launch/trust, then confirm `/mcp` shows `obsidian` connected.
   - `.claude/settings.json` fields (`plansDirectory: "vault/plans"`, `autoMemoryEnabled: false`, permission entries for
     `mcp__obsidian__*` and, if you want to run the linter manually, a Bash allow-entry for `vault-lint.mjs`) are NOT set
     automatically — see this plugin's README "Manual settings" section and merge them into your project's own
     `.claude/settings.json` if desired.
   - Launch `claude` from the project root so `${CLAUDE_PROJECT_DIR}` and the MCP server root agree.

Report: what was copied/skipped, whether AGENTS.md was updated or already had the section, and the reminder list above.
