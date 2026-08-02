# Project-Conventions Skill Design

Approved 2026-08-02. Source: personal TODO note — recurring conventions the
author kept re-explaining project to project (planning docs, user docs, CLI
tooling standards).

## Purpose

A distributable skill that captures dotKnewt's cross-project conventions —
where planning/bookmark docs live, where user-facing docs live, how Python CLI
tools get installed and documented — so they stop being re-explained per
project. Used both to scaffold a fresh project and as a standing reference
during ongoing work in any project that has it installed.

## Placement

New skill: `skills/project-conventions/SKILL.md`. Added to the
`instruction-management` bundle (symlinked into
`plugins/instruction-management/skills/project-conventions`) — the closest
existing home, since that bundle already owns the AGENTS.md/STATE.md "Memory
vs. State" pattern and ships the `state-keeper` agent this skill reuses. Also
individually installable as its own marketplace micro-entry, matching every
other skill in this repo. Regenerate `.claude-plugin/marketplace.json` via
`.github/scripts/generate-marketplace.py` after adding the skill and its bundle
symlink, per existing repo convention.

## Structure

- `SKILL.md` — trigger description plus the top-level workflow: scaffold a
  missing convention, or answer/check against one when asked mid-project.
- `references/docs-layout.md` — the `docs/TODO.md` / `docs/STATE.md` /
  `docs/user/*.md` convention.
- `references/cli-standards.md` — the uv + CLI framework convention for
  Python CLI tools.

## docs-layout.md

- **`docs/TODO.md`** — backlog notes, grouped by topic heading, bullet list
  per topic. Same style this repo's existing `TODO.md` already uses, just
  relocated under `docs/`.
- **`docs/STATE.md`** — session bookmarks. Schema stays owned by the existing
  `state-keeper` agent (What/How/WIP/ToDo/Completed/Decisions) — this skill
  does not duplicate the schema, it invokes `state-keeper` with path
  `docs/STATE.md` instead of the old default `./STATE.md`.
- **`docs/user/*.md`** — user-facing docs (install, usage, tutorials, FAQ).
  Open-ended file set — the convention establishes the location, not a fixed
  list of filenames. Distinguished from `docs/specs/` (architecture/contributor
  docs, owned by `docs-spec-maintainer`) and the root `README.md` (short
  overview + pointer into `docs/user/`).
- Follow-on edit: update `agents/docs-user-maintainer/docs-user-maintainer.md`'s
  scope note to name `docs/user/*.md` as its canonical audit target, alongside
  its existing generic `docs/` scan.

## cli-standards.md (Python-specific)

- **Dev loop:** `uv sync` / `uv run` inside the repo during development.
- **End-user install:** `uv tool install <pkg>` for persistent installs, or
  `uvx <pkg>` for ephemeral runs. pip/pipx are not documented as the primary
  path.
- **Framework:** recommend **Typer** — type-hint-driven command definitions,
  auto-generated `--help`, built-in `--install-completion` /
  `--show-completion` (no separate `argcomplete` registration step, pairs
  cleanly with a `uv tool install`-first story). Click/argparse noted as
  acceptable fallbacks for constrained cases, not the default recommendation.
- **`--help` standard:** every command/subcommand has a one-line summary and
  help text on every option; top-level `--help` lists subcommands; the app's
  docstring includes a usage example (Typer renders it in help output).
- **Completion standard:** the README's install section documents
  `<tool> --install-completion` as a one-time per-shell setup step.

## Scaffolding behavior

When invoked to set up conventions on a project (fresh or existing):

1. Ensure `docs/` exists.
2. Create `docs/TODO.md` from template if missing.
3. Create/maintain `docs/STATE.md` by invoking the `state-keeper` agent with
   path `docs/STATE.md`.
4. Note the `docs/user/` pattern — create the directory only if the project
   already has user-facing content to house there; otherwise just document
   the convention for later.
5. If a Python CLI is detected (`pyproject.toml` with `[project.scripts]`),
   check its install docs, `--help` output, and completion setup against
   `cli-standards.md` and report gaps.

## Ongoing use

Same `SKILL.md`, no fresh-scaffold path taken: when asked "where should docs
go" it points at `docs-layout.md`; when adding a CLI command it points at
`cli-standards.md`; when wrapping up a session it nudges toward
`state-keeper`/`docs/TODO.md`.

## Migrating `agency` itself

Since this repo currently has root-level `TODO.md`/`STATE.md`, it migrates to
the new convention as part of this effort:

- `git mv TODO.md docs/TODO.md`
- `git mv STATE.md docs/STATE.md`
- Update path references in: `AGENTS.md` (layout line), `README.md` (layout
  table), `agents/state-keeper/state-keeper.md` (example path + description
  text), `skills/instruction-management/SKILL.md` (Memory vs. State callout),
  `skills/instruction-management/references/templates.md` (three template
  mentions), `skills/instruction-management/references/update-guidelines.md`,
  `docs/EXTENSIONS.md`.
- Regenerate `marketplace.json` via
  `.github/scripts/generate-marketplace.py` afterward, since `state-keeper`'s
  description text changes propagate there.

## Out of scope

- No fixed `docs/user/*.md` file list — location convention only.
- No non-Python CLI tooling coverage.
- No new agents — reuses `state-keeper` as-is (only its example path text
  changes).
- No retroactive migration of `docs/user` content in other, unrelated repos —
  this design covers `agency` itself plus the shipped convention for future
  projects.
