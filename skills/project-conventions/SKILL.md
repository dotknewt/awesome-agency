---
name: project-conventions
description: dotKnewt's cross-project conventions — planning docs in docs/TODO.md and docs/STATE.md, user docs in docs/user/, and uv + Typer standards for Python CLIs. Use when scaffolding a new project, asked where docs or backlog notes should live, adding a Python CLI command, or checking a project against these conventions.
---

# Project Conventions

Cross-project conventions: where planning and bookmark docs live, where
user-facing docs live, and how Python CLI tools get installed and
documented. Use this to scaffold a fresh project or as a standing
reference during ongoing work in any project that has it installed.

## Scaffold a project

When invoked to set up conventions on a project (fresh or existing):

1. Ensure `docs/` exists.
2. Create `docs/TODO.md` from the template in
   [references/docs-layout.md](references/docs-layout.md) if missing.
3. Create/maintain `docs/STATE.md` by invoking the `state-keeper` agent
   with path `docs/STATE.md`.
4. Note the `docs/user/` pattern — create the directory only if the
   project already has user-facing content to house there; otherwise
   just mention the convention for later.
5. If a Python CLI is detected (`pyproject.toml` with
   `[project.scripts]`), check its install docs, `--help` output, and
   completion setup against
   [references/cli-standards.md](references/cli-standards.md) and
   report gaps.

## Ongoing reference

- "Where should docs / backlog notes go?" →
  [references/docs-layout.md](references/docs-layout.md)
- Adding or changing a CLI command →
  [references/cli-standards.md](references/cli-standards.md)
- Wrapping up a session → invoke `state-keeper` with path
  `docs/STATE.md`; park backlog ideas in `docs/TODO.md`.
