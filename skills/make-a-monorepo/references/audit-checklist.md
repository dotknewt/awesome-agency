# Audit mode: checklist, severity rules, and `--fix` behavior

Read this file when running `/make-a-monorepo audit` or `/make-a-monorepo audit --fix`. It has
the full checklist, how to bucket findings by severity, the report format, and exactly what
`--fix` is and isn't allowed to touch.

## Severity levels

Scan the current working directory and check every convention below. Report findings as a
checklist grouped by category, using these severity levels:

- 🔴 **violation** — breaks a hard rule (secrets exposed, missing gitignore entry, tokens in config)
- 🟡 **drift** — structure exists but doesn't match convention (wrong naming, missing CLAUDE.md sections, `packages/` present)
- 🟢 **pass** — matches convention
- ⚪ **skip** — not applicable or not yet populated

## Audit checklist

### 1. Directory structure
- [ ] Root has `CLAUDE.md`
- [ ] `.claude/settings.json` exists
- [ ] `.claude/agents/`, `.claude/commands/`, `.claude/skills/` exist
- [ ] `mcp-servers/` exists with `registry.json`
- [ ] Each `mcp-servers/<name>/` has its own `CLAUDE.md`
- [ ] `schemas/` directory exists
- [ ] `resources/` directory exists
- [ ] `reports/` directory exists
- [ ] `docs/DECISIONS.md` exists
- [ ] `tests/` directory exists
- [ ] No `packages/` directory present (drift if found)

### 2. Naming conventions
- [ ] All file and directory names are kebab-case
- [ ] Agent files use noun-role pattern
- [ ] Skill files use noun-verb pattern
- [ ] MCP server dirs use `<domain>-mcp` pattern
- [ ] Schema files use `<entity>.schema.json` pattern
- [ ] Report files match `YYYY-MM-DD-<slug>.md`

### 3. Secrets and tokens
- [ ] `.gitignore` exists and contains `.env`
- [ ] `.gitignore` contains `.claude/settings.local.json`
- [ ] `.gitignore` contains `.claude/CLAUDE.local.md`
- [ ] `.env.example` exists (if `.env` exists or `.mcp.json` references env vars)
- [ ] `.env` is NOT tracked by git (`git ls-files .env` returns empty)
- [ ] `.mcp.json` contains no literal tokens — only `${ENV_VAR}` references
- [ ] `.claude/settings.json` contains no literal tokens

### 4. CLAUDE.md quality
- [ ] Root `CLAUDE.md` has all required sections: Purpose, Key paths, Env vars required, Active MCP servers, Agent roster, Naming conventions, Do/Don't
- [ ] Root `CLAUDE.md` references `mcp-servers/registry.json` rather than hardcoding server info
- [ ] Each `mcp-servers/<name>/CLAUDE.md` has Purpose, Tools exposed, Env vars, Local conventions sections

### 5. Registry and schemas
- [ ] `mcp-servers/registry.json` exists and is valid JSON
- [ ] `mcp-servers/registry.json` has `$schema_version` field
- [ ] Every schema file in `schemas/` is registered in the registry
- [ ] Every server directory in `mcp-servers/` is registered in the registry
- [ ] Schema files have `$schema_version` field

### 6. Agent and skill hygiene
- [ ] Agent docs are under 80 lines (warn if over)
- [ ] No skill file references a specific agent (skills stay agent-agnostic)
- [ ] No name-pattern crossover (agents aren't noun-verb, skills aren't noun-role)

### 7. Version control
- [ ] Git is initialized
- [ ] Branch `main` exists
- [ ] Branch `dev` exists
- [ ] Recent commits follow conventional commit format (sample last 10)
- [ ] MCP servers track a `CHANGELOG.md` if they live in the repo

### 8. Extensibility anchors
- [ ] `mcp-servers/registry.json` is the single source of truth (no hardcoded paths in agent docs)
- [ ] `docs/DECISIONS.md` has at least one entry
- [ ] `tests/` is non-empty or has `.gitkeep`

## Mechanical checks: `scripts/audit.py`

Sections 3 (secrets/tokens' `.gitignore` and `.env` tracking pieces), 5 (JSON validity), part of
2 (kebab-case naming), and part of 7 (conventional commit format) are mechanically checkable —
they don't require judgment. Run `scripts/audit.py` before doing the rest of the audit by hand:

```bash
python3 scripts/audit.py --path .
```

It prints a structured JSON report to stdout (one object per check group, plus a `summary` and
top-level `passed` boolean) and writes progress/diagnostics to stderr. Exit codes:

- `0` — ran successfully, all mechanical checks passed
- `1` — couldn't run (bad `--path`, not a directory, etc.)
- `2` — CLI usage error (reserved by argparse)
- `3` — ran successfully, at least one mechanical check failed

Fold its `checks` output into the relevant sections above rather than re-deriving those findings
by hand — use it as ground truth for the mechanical portion, and reserve your own judgment for
the parts of the checklist that need it (CLAUDE.md quality, agent/skill hygiene, extensibility
anchors, and anything the script explicitly skipped, e.g. because the directory isn't a git repo).

## Audit output format

```
## Audit: <project-name>
### 🔴 Violations (fix immediately)
- <finding + fix instruction>

### 🟡 Drift (align when convenient)
- <finding + suggested change>

### 🟢 Passing (N/M checks)

### Summary
<total pass/drift/violation/skip counts>
```

## `--fix` behavior

When `--fix` is passed, auto-apply safe fixes after showing the audit. "Safe" means:

**Will auto-fix:**
- Create missing directories (with `.gitkeep`)
- Add missing `.gitignore` entries
- Create stub `CLAUDE.md` files with section headers (only if absent)
- Create missing `mcp-servers/registry.json` with empty structure
- Create missing `docs/DECISIONS.md` with template
- Create missing `.env.example` from `.mcp.json` env var references

**Will NOT auto-fix (report only):**
- Rename files (naming convention violations) — too risky without context
- Remove exposed secrets — needs human review
- Modify existing `CLAUDE.md` content — only creates missing ones
- Move content out of a `packages/` directory — needs human decisions on each path
- Change git branch structure
- Alter `.claude/settings.json` permissions

After auto-fix, re-run the audit silently and print the updated summary showing what was resolved.
