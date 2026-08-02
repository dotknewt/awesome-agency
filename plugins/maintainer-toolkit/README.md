# maintainer-toolkit

Keep a repo's secondary artifacts — documentation, agent instructions, structured
schemas/manifests — from drifting out of sync with the code.

Everything is **report-and-propose**: maintainer agents are read-only; they detect
drift and return proposed fixes. Nothing is applied without your approval.

## Install

    /plugin marketplace add dotknewt/agency
    /plugin install maintainer-toolkit@agency

Each agent is also installable standalone (e.g. `schema-maintainer-agent@agency`).

## Usage

- `/maintain` — audit what changed since the merge-base with the default branch
- `/maintain full` — whole-repo sweep
- `/maintain since <ref>` — audit changes since a specific ref

The orchestrator deploys only the maintainers relevant to the change, in parallel,
and merges their reports into one prioritized list (HIGH/MED/LOW). You pick which
fixes to apply; the main session applies them.

## Components

| Component | Role |
|---|---|
| `maintain` (skill) | Orchestrator: scopes, routes, dispatches, merges, applies approved fixes |
| `docs-user-maintainer` | Audits user-facing docs (READMEs, guides) against actual behavior |
| `docs-spec-maintainer` | Audits specs/architecture/API docs against the code they describe |
| `instructions-maintainer` | Audits AGENTS.md / legacy CLAUDE.md for stale or missing guidance |
| `schema-maintainer` | Audits manifests, configs, frontmatter, generated files; runs repo validators (Haiku) |

Pairs well with the `instruction-management` plugin: the instructions maintainer
recommends it for *applying* instruction-file fixes.
