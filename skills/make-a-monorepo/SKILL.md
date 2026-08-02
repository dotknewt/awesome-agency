---
name: make-a-monorepo
description: >
  Use when the user wants to scaffold a brand-new flat monorepo (no packages/
  layer) for security/threat-hunting tooling — combining MCP servers, shared
  JSON schemas, sigma-rules/ECS/OCSF/CIM resource packs, reports, and Claude
  Code agents/skills/commands under one root CLAUDE.md — or wants to audit an
  existing repo against those flat-monorepo conventions (directory structure,
  naming, secrets hygiene, CLAUDE.md quality) and optionally auto-fix what's
  safely fixable. Trigger even when the user doesn't say "monorepo" explicitly
  — e.g. requests to organize MCP servers, shared schemas, and reports into one
  repo, or to check whether a project's layout still matches its CLAUDE.md
  conventions. Not for generic multi-package tooling asks like adding npm/yarn
  workspaces, wiring up Nx or Turborepo, or scaffolding a single-package src
  layout — this skill is specifically for the flat, no-packages/ monorepo
  shape described above.
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

Scaffolds a new flat monorepo: gathers the project name, MCP servers, schemas, and resource packs to include; creates the directory structure; generates every template file (root `CLAUDE.md`, `.claude/settings.json`, `.mcp.json`, `.env.example`, `.gitignore`, `mcp-servers/registry.json`, per-server `CLAUDE.md`, schema files, `docs/DECISIONS.md`); initializes git with `main`/`dev` branches; and prints a summary with next steps.

Full step-by-step instructions and every template's exact content live in **[references/init-templates.md](references/init-templates.md)** — read it before scaffolding anything.

## Mode: `audit`

Scans the current working directory against the monorepo conventions (directory structure, naming, secrets hygiene, `CLAUDE.md` quality, registry/schema consistency, agent/skill hygiene, version control, extensibility anchors), reports findings bucketed by severity (🔴/🟡/🟢/⚪), and — with `--fix` — auto-applies the subset of fixes that are safe to make without human judgment.

The full checklist, severity rules, output format, and `--fix` behavior live in **[references/audit-checklist.md](references/audit-checklist.md)** — read it before auditing anything. It also documents `scripts/audit.py`, which mechanically runs the checkable portion of the checklist for you.

---

## Rules for this command

1. Never create `.env` — only `.env.example`. If `.env` already exists, do not read or print its contents.
2. All generated file/directory names must be kebab-case.
3. Don't add servers, schemas, or resource packs the user didn't ask for.
4. Keep generated files minimal — templates with clear `<!-- comment -->` placeholders, not walls of boilerplate.
5. If auditing a project that predates these conventions, be pragmatic: report what matters, don't nitpick paths that are clearly intentional deviations.
6. For `init`, always initialize git and make the first commit on `main` before creating `dev`.
7. This layout is flat by design. If an audited repo has a `packages/` directory, flag it as drift but do not auto-move its contents.
