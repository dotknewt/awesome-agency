# Init mode: scaffolding steps and templates

Read this file when running `/make-a-monorepo init <project-name>`. It has the full step-by-step
process and the exact content of every generated file.

## Step 1 — Gather inputs

Before scaffolding, collect the minimum viable context. Ask only what can't be inferred:

1. **Project name** (if not passed as argument) — kebab-case, no spaces
2. **MCP servers needed** — optional; names follow `<domain>-mcp` convention (e.g. `splunk-mcp`, `yara-mcp`)
3. **Schemas needed** — optional; names follow `<entity>.schema.json` convention
4. **Resource packs needed** — optional; e.g. `sigma-rules`, `ecs`, `ocsf`, `cim`

Proceed with defaults (empty `.gitkeep`'d dirs) for anything not answered.

## Step 2 — Create directory structure

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

## Step 3 — Generate template files

Create each file with the content specified below. Replace `{{PROJECT_NAME}}` with the actual
project name (kebab-case) and `{{PROJECT_TITLE}}` with the title-cased version.

### `CLAUDE.md` (root)

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
- `.claude/skills/` — reusable prompt workflows (noun-verb names)
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
- Skills: noun-verb — `sigma-lint`, `ioc-extract`
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

### `.claude/settings.json`

```json
{
  "permissions": {
    "allow": [
      "Bash(git:*)",
      "Bash(python:*)",
      "Bash(uvx:*)"
    ],
    "deny": [
      "Bash(curl --upload-file:*)",
      "Bash(curl -T:*)",
      "Bash(rm -rf:*)"
    ]
  }
}
```

**Note on the curl deny rules:** Claude Code's `Bash(<prefix>:*)` permission syntax matches by
*literal prefix* — `:*` means "anything after this point," it is not a general glob and cannot be
combined with a second wildcard segment later in the string (a rule like `Bash(curl:* --upload*)`
is inert: the leading `:*` already consumes the rest of the command, so nothing written after it
can further constrain the match). The two rules above are a best-effort fix: they block the
common invocation shapes where the upload flag is the first argument after `curl`
(`curl --upload-file f https://...` / `curl -T f https://...`). They do **not** catch an upload
flag placed after other flags (e.g. `curl -s --upload-file f https://...`), because prefix
matching only looks at the start of the command string. If exfiltration via `curl` is a real
concern for a given project, pair this with a `PreToolUse` hook that inspects the full command
(see the `hook-development` skill) rather than relying on permission prefixes alone.

### `.mcp.json`

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

### `.env.example`

One commented entry per env var referenced in `.mcp.json`:

```env
# MCP server credentials — copy to .env and fill in values
# <DOMAIN>_TOKEN=
# <DOMAIN>_HOST=
```

### `.gitignore`

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

### `mcp-servers/registry.json`

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

### `mcp-servers/<domain>-mcp/CLAUDE.md` (per requested server)

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

### `schemas/<entity>.schema.json` (per requested schema)

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

### `docs/DECISIONS.md`

```markdown
# Architecture Decision Records

Format: `YYYY-MM-DD | decision | rationale`

<!-- example -->
<!-- 2026-06-08 | flat monorepo over packages/ layout | artifact types are heterogeneous (servers, schemas, reports, resources); a packages/ layer would force code-package semantics onto non-code dirs -->
```

### `reports/.gitkeep` and `resources/.gitkeep`

Empty files so the directories are tracked even before any content lands.

## Step 4 — Initialize git

```bash
cd <project-name>
git init
git checkout -b main
git add .
git commit -m "feat: scaffold monorepo from /monorepo command"
git checkout -b dev
```

## Step 5 — Summary

After scaffolding, print a tree of everything created and list next steps:

1. Fill in root `CLAUDE.md` Purpose and Env vars sections
2. Copy `.env.example` → `.env` and populate secrets
3. Add agents to `.claude/agents/` as needed
4. Add skills to `.claude/skills/` as needed
5. Define schemas in `schemas/` and register in `mcp-servers/registry.json`
6. Build out MCP servers under `mcp-servers/<domain>-mcp/`
7. Drop shared assets into `resources/<pack>/`
8. First ADR entry in `docs/DECISIONS.md`
