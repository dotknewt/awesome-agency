# steward

Keep a repo's secondary artifacts — documentation, agent instructions, structured
schemas/manifests — from drifting out of sync with the code, and apply the fixes
with purpose-built instruction skills.

Two halves, one plugin:

- **Audit** — read-only maintainer agents detect drift and return proposed fixes.
  Everything is **report-and-propose**: nothing is applied without your approval.
- **Apply** — skills that audit, revise, and restructure `AGENTS.md` (and legacy
  `CLAUDE.md`), scaffold project conventions, and keep `docs/STATE.md` current.

## Install

    /plugin marketplace add dotknewt/agency
    /plugin install steward@agency

Each agent and skill is also installable standalone (e.g.
`schema-maintainer-agent@agency`, `instructions-revise@agency`).

## Maintenance sweeps

- `/maintain` — audit what changed since the merge-base with the default branch
- `/maintain full` — whole-repo sweep
- `/maintain since <ref>` — audit changes since a specific ref

The orchestrator deploys only the maintainers relevant to the change, in parallel,
and merges their reports into one prioritized list (HIGH/MED/LOW). You pick which
fixes to apply; the main session applies them — for instruction files, via the
bundled instruction skills below.

## Instruction skills

| | instructions-audit | instructions-revise | instructions-restructure |
|---|---|---|---|
| **Purpose** | Audit instruction quality | Capture session learnings | Move content to the right depth |
| **Triggered by** | Codebase changes | End of session | Root instruction file getting bloated |
| **Use when** | Periodic maintenance | Session revealed missing context | Detail is too high up in the tree |

`instructions-audit` is the entry point: it audits, then by default orchestrates
`instructions-revise` and `instructions-restructure` as sub-steps before applying
any remaining edits inline. Ask to skip either (or both) to run a narrower audit.
Each skill can also fire on its own if you ask for just that behavior directly.

```
"audit my AGENTS.md"
"capture what we learned this session in AGENTS.md"
"restructure AGENTS.md — this section only applies under packages/api"
```

A Stop hook nudges you to run `instructions-revise` when a session has touched
many files (tunable via `INSTRUCTIONS_NUDGE_THRESHOLD` / `INSTRUCTIONS_NUDGE_DELTA`).

## Conventions & state

- `conventions` (skill) — dotKnewt's cross-project conventions: planning docs in
  `docs/TODO.md` / `docs/STATE.md`, user docs in `docs/user/`, uv + Typer standards
  for Python CLIs. Scaffolds fresh projects and answers "where does this go?".
- `conventions-maintainer` (agent) — the sweep-side auditor for the same
  conventions: flags docs-layout and CLI-standards drift during `/maintain` runs;
  the `conventions` skill's scaffold mode applies approved fixes. Runs on Haiku.
- `state-keeper` (agent) — maintains `docs/STATE.md`: rolls completed WIP/ToDo items
  into a timestamped Completed section and surfaces durable decisions as AGENTS.md
  candidates. Runs on Haiku.

## Components

| Component | Role |
|---|---|
| `maintain` (skill) | Orchestrator: scopes, routes, dispatches, merges, applies approved fixes |
| `docs-user-maintainer` | Audits user-facing docs (READMEs, guides) against actual behavior (Haiku) |
| `docs-spec-maintainer` | Audits specs/architecture/API docs against the code they describe |
| `instructions-maintainer` | Audits AGENTS.md / legacy CLAUDE.md for stale or missing guidance |
| `schema-maintainer` | Audits manifests, configs, frontmatter, generated files; runs repo validators (Haiku) |
| `conventions-maintainer` | Audits docs layout and Python CLI standards against the cross-project conventions (Haiku) |
| `instructions-audit` (skill) | Audits instruction quality against a rubric; proposes and applies edits |
| `instructions-revise` (skill) | Captures session learnings into AGENTS.md |
| `instructions-restructure` (skill) | Moves instruction content to the depth where it applies |
| `conventions` (skill) | Cross-project docs/CLI conventions and project scaffolding |
| `state-keeper` (agent) | Maintains docs/STATE.md session bookmarks (Haiku) |

## AGENTS.md vs CLAUDE.md

`AGENTS.md` (agents.md) is the portable, cross-agent convention — Claude Code,
Codex, Cursor, and others read it. `CLAUDE.md` is Claude Code's legacy filename and
is currently the only file Claude Code auto-loads.

When a skill finds a `CLAUDE.md` and no `AGENTS.md`, it offers:

- **Rename** — `git mv CLAUDE.md AGENTS.md`. Single file. Use if Claude Code is no
  longer in the loop.
- **Migrate + stub** *(recommended when Claude Code is still in use)* — move content
  to `AGENTS.md`; leave a two-line `CLAUDE.md` that `@`-references `AGENTS.md`.
  Claude Code auto-loads `CLAUDE.md` → inlines `AGENTS.md`. Other agents read
  `AGENTS.md` directly. One source of truth.

See `skills/instructions-audit/references/migration.md` for details.
