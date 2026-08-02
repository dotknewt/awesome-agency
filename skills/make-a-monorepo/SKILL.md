---
name: make-a-monorepo
description: >
  Scaffold a flat monorepo from scratch or audit an existing project against monorepo
  conventions. Use when asked to create a monorepo, set up a multi-package repo,
  or audit/fix monorepo structure. Invoked via /make-a-monorepo init <name> or
  /make-a-monorepo audit [--fix].
---

# /make-a-monorepo — flat monorepo setup and convention audit

You are a project scaffolder and convention auditor. You operate in one of two modes based on the argument passed to this command.

## Usage

```
/make-a-monorepo init <project-name>     — create a new flat monorepo from scratch
/make-a-monorepo audit                   — check current project against conventions
/make-a-monorepo audit --fix             — audit and auto-fix what's safe to fix
```

If no argument is given, ask which mode:
- **init** — scaffold a new project
- **audit** — check the current working directory

---

## Mode: `init`

### Step 1 — Gather inputs

Before scaffolding, collect the minimum viable context. Ask only what can't be inferred:

1. **Project name** (if not passed as argument) — kebab-case, no spaces
2. **MCP servers needed** — optional; names follow `<domain>-mcp` convention (e.g. `splunk-mcp`, `yara-mcp`)
3. **Schemas needed** — optional; names follow `<entity>.schema.json` convention
4. **Resource packs needed** — optional; e.g. `sigma-rules`, `ecs`, `ocsf`, `cim`

Proceed with defaults (empty `.gitkeep`'d dirs) for anything not answered.

### Step 2 — Create directory structure

Flat monorepo layout. Every path uses kebab-case. **No `packages/` directory.**

```
<project-name>/
├── CLAUDE.md
├── .mcp.json
├── .env.example
├── .gitignore
├── .claude/
│   ├── settings.json
│   ├── agents/
│   │   └── .gitkeep
│   ├── commands/
│   │   └── .gitkeep
│   └── skills/
│       └── .gitkeep
├── mcp-servers/
│   ├── registry.json
│   └── <domain>-mcp/          (per server, if requested)
│       ├── CLAUDE.md
│       ├── server.py
│       └── pyproject.toml
├── schemas/
│   └── <entity>.schema.json   (per schema, if requested)
├── resources/
│   └── <pack>/                (per pack, if requested)
├── reports/
│   └── .gitkeep
├── docs/
│   └── DECISIONS.md
└── tests/
    └── .gitkeep
```

### Step 3 — Generate template files

Create each file with the content specified below. Replace `{{PROJECT_NAME}}` with the actual project name (kebab-case) and `{{PROJECT_TITLE}}` with the title-cased version.

---

#### `CLAUDE.md` (root)

```markdown
# Project: {{PROJECT_TITLE}}

## Purpose
<!-- one-liner: what this project does and who it serves -->

## Key paths
- `mcp-servers/` — MCP server implementations; each has own CLAUDE.md
- `mcp-servers/registry.json` — canonical server + schema inventory
- `schemas/` — shared JSON schemas across agent/tool boundaries
- `resources/` — shared assets (sigma rules, ECS/OCSF/CIM packs, lookup tables)
- `reports/` — incident, hunt, and triage reports (markdown, dated)
- `.claude/agents/` — agent instruction documents (noun-role names)
- `.claude/skills/` — reusable prompt workflows (verb-noun names)
- `.claude/commands/` — slash commands
- `docs/DECISIONS.md` — architecture decision records
- `tests/` — eval suite and regression prompts

## Env vars required
<!-- populated from .env.example -->

## Active MCP servers
See `mcp-servers/registry.json` for the canonical server + schema inventory. Do not hardcode paths anywhere else.

## Agent roster
<!-- list agents from .claude/agents/ with one-line role descriptions -->

## Naming conventions
- Files/dirs: `kebab-case`
- Agents: noun-role — `dispatcher`, `splunk-subagent`
- Skills: verb-noun — `sigma-lint`, `ioc-extract`
- MCP servers: `<domain>-mcp` — directory name and registry key must match
- Schemas: `<entity>.schema.json` (version inside via `$schema_version`)
- Resources: namespaced by source — `resources/sigma-rules/`, `resources/ecs/`
- Reports: dated kebab-case — `reports/YYYY-MM-DD-<slug>.md`
- Slash commands: short, action-oriented — `/monorepo`, `/hunt`, `/triage`
- Commits: conventional — `feat:`, `fix:`, `docs:`, `refactor:`

## Do
- Start sessions from the relevant subdirectory for focused tasks
- Use git worktrees for parallel agents
- Reference `mcp-servers/registry.json` — never hardcode server/schema paths
- Keep agent docs short; push logic into skills
- Tag stable agent/skill versions: `v-agents-<name>-<semver>`, `v-skills-<name>-<semver>`

## Don't
- Commit `.env` — only `.env.example`
- Put tokens in `.mcp.json` or `.claude/settings.json` — use `${ENV_VAR}` expansion
- Let agents grow fat — if an agent doc exceeds ~80 lines, extract skills
- Hardcode schema paths in agents — use registry lookups
- Introduce a `packages/` layer — this monorepo is flat by design
```

---

#### `.claude/settings.json`

```json
{
  "permissions": {
    "allow": [
      "Bash(git:*)",
      "Bash(python:*)",
      "Bash(uvx:*)"
    ],
    "deny": [
      "Bash(curl:* --upload*)",
      "Bash(rm -rf:*)"
    ]
  }
}
```

---

#### `.mcp.json`

Generate entries only for MCP servers the user listed during input. If none were listed, create the empty structure:

```json
{
  "mcpServers": {}
}
```

If servers were specified, each entry follows this pattern:

```json
{
  "mcpServers": {
    "<domain>-mcp": {
      "command": "uvx",
      "args": ["<domain>-mcp"],
      "env": {
        "<DOMAIN>_TOKEN": "${<DOMAIN>_TOKEN}",
        "<DOMAIN>_HOST": "${<DOMAIN>_HOST}"
      }
    }
  }
}
```

---

#### `.env.example`

One commented entry per env var referenced in `.mcp.json`:

```env
# MCP server credentials — copy to .env and fill in values
# <DOMAIN>_TOKEN=
# <DOMAIN>_HOST=
```

---

#### `.gitignore`

```gitignore
# secrets
.env
.env.local
.env.*.local

# claude code personal overrides
.claude/settings.local.json
.claude/CLAUDE.local.md

# python venvs (MCP servers each carry their own)
.venv/
**/.venv/
__pycache__/
*.pyc

# node / build
node_modules/
dist/
build/
.cache/

# editor / OS
.DS_Store
Thumbs.db
*.swp
*~
.vscode/
.idea/
```

---

#### `mcp-servers/registry.json`

```json
{
  "$schema_version": "1.0",
  "schemas": {},
  "servers": {}
}
```

Populate `schemas` if the user specified schema names, and `servers` if MCP servers were listed.

Schema entry pattern:
```json
"<entity>": "schemas/<entity>.schema.json"
```

Server entry pattern:
```json
"<domain>-mcp": {
  "module": "mcp-servers/<domain>-mcp",
  "version": "0.1.0"
}
```

---

#### `mcp-servers/<domain>-mcp/CLAUDE.md` (per requested server)

```markdown
# MCP Server: <domain>-mcp

## Purpose
<!-- what domain this server exposes and which downstream system it wraps -->

## Tools exposed
<!-- one bullet per tool: name + one-line description -->

## Env vars
<!-- list each <DOMAIN>_* var with one-line description -->

## Local conventions
<!-- anything that overrides or extends root CLAUDE.md -->
```

---

#### `schemas/<entity>.schema.json` (per requested schema)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$schema_version": "0.1.0",
  "$id": "{{PROJECT_NAME}}/schemas/<entity>",
  "title": "<Entity>",
  "description": "",
  "type": "object",
  "properties": {},
  "required": []
}
```

---

#### `docs/DECISIONS.md`

```markdown
# Architecture Decision Records

Format: `YYYY-MM-DD | decision | rationale`

<!-- example -->
<!-- 2026-06-08 | flat monorepo over packages/ layout | artifact types are heterogeneous (servers, schemas, reports, resources); a packages/ layer would force code-package semantics onto non-code dirs -->
```

---

#### `reports/.gitkeep` and `resources/.gitkeep`

Empty files so the directories are tracked even before any content lands.

---

### Step 4 — Initialize git

```bash
cd <project-name>
git init
git checkout -b main
git add .
git commit -m "feat: scaffold monorepo from /monorepo command"
git checkout -b dev
```

### Step 5 — Summary

After scaffolding, print a tree of everything created and list next steps:

1. Fill in root `CLAUDE.md` Purpose and Env vars sections
2. Copy `.env.example` → `.env` and populate secrets
3. Add agents to `.claude/agents/` as needed
4. Add skills to `.claude/skills/` as needed
5. Define schemas in `schemas/` and register in `mcp-servers/registry.json`
6. Build out MCP servers under `mcp-servers/<domain>-mcp/`
7. Drop shared assets into `resources/<pack>/`
8. First ADR entry in `docs/DECISIONS.md`

---

## Mode: `audit`

Scan the current working directory and check every convention. Report findings as a checklist grouped by category. Use these severity levels:

- 🔴 **violation** — breaks a hard rule (secrets exposed, missing gitignore entry, tokens in config)
- 🟡 **drift** — structure exists but doesn't match convention (wrong naming, missing CLAUDE.md sections, `packages/` present)
- 🟢 **pass** — matches convention
- ⚪ **skip** — not applicable or not yet populated

### Audit checklist

#### 1. Directory structure
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

#### 2. Naming conventions
- [ ] All file and directory names are kebab-case
- [ ] Agent files use noun-role pattern
- [ ] Skill files use verb-noun pattern
- [ ] MCP server dirs use `<domain>-mcp` pattern
- [ ] Schema files use `<entity>.schema.json` pattern
- [ ] Report files match `YYYY-MM-DD-<slug>.md`

#### 3. Secrets and tokens
- [ ] `.gitignore` exists and contains `.env`
- [ ] `.gitignore` contains `.claude/settings.local.json`
- [ ] `.gitignore` contains `.claude/CLAUDE.local.md`
- [ ] `.env.example` exists (if `.env` exists or `.mcp.json` references env vars)
- [ ] `.env` is NOT tracked by git (`git ls-files .env` returns empty)
- [ ] `.mcp.json` contains no literal tokens — only `${ENV_VAR}` references
- [ ] `.claude/settings.json` contains no literal tokens

#### 4. CLAUDE.md quality
- [ ] Root `CLAUDE.md` has all required sections: Purpose, Key paths, Env vars required, Active MCP servers, Agent roster, Naming conventions, Do/Don't
- [ ] Root `CLAUDE.md` references `mcp-servers/registry.json` rather than hardcoding server info
- [ ] Each `mcp-servers/<name>/CLAUDE.md` has Purpose, Tools exposed, Env vars, Local conventions sections

#### 5. Registry and schemas
- [ ] `mcp-servers/registry.json` exists and is valid JSON
- [ ] `mcp-servers/registry.json` has `$schema_version` field
- [ ] Every schema file in `schemas/` is registered in the registry
- [ ] Every server directory in `mcp-servers/` is registered in the registry
- [ ] Schema files have `$schema_version` field

#### 6. Agent and skill hygiene
- [ ] Agent docs are under 80 lines (warn if over)
- [ ] No skill file references a specific agent (skills stay agent-agnostic)
- [ ] No name-pattern crossover (agents aren't verb-noun, skills aren't noun-role)

#### 7. Version control
- [ ] Git is initialized
- [ ] Branch `main` exists
- [ ] Branch `dev` exists
- [ ] Recent commits follow conventional commit format (sample last 10)
- [ ] MCP servers track a `CHANGELOG.md` if they live in the repo

#### 8. Extensibility anchors
- [ ] `mcp-servers/registry.json` is the single source of truth (no hardcoded paths in agent docs)
- [ ] `docs/DECISIONS.md` has at least one entry
- [ ] `tests/` is non-empty or has `.gitkeep`

### Audit output format

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

### `--fix` behavior

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

---

## Rules for this command

1. Never create `.env` — only `.env.example`. If `.env` already exists, do not read or print its contents.
2. All generated file/directory names must be kebab-case.
3. Don't add servers, schemas, or resource packs the user didn't ask for.
4. Keep generated files minimal — templates with clear `<!-- comment -->` placeholders, not walls of boilerplate.
5. If auditing a project that predates these conventions, be pragmatic: report what matters, don't nitpick paths that are clearly intentional deviations.
6. For `init`, always initialize git and make the first commit on `main` before creating `dev`.
7. This layout is flat by design. If an audited repo has a `packages/` directory, flag it as drift but do not auto-move its contents.
