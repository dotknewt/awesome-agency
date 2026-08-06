## Commit directly to main

Use a direct commit when the change is:

- **Self-contained and low-risk** — a single file change or a tightly coupled set of changes with an obvious correct outcome (typo fix, label update, adding a `workflow_dispatch` trigger).
- **Configuration or housekeeping** — settings, `.claudeignore`, workflow tweaks, adding an `@file` reference to `CLAUDE.md`.
- **Instruction or documentation only** — adding or editing files under `instructions/`, updating `CLAUDE.md` / `AGENTS.md` with no behaviour change to agents or skills.
- **Mechanical agent/skill/plugin tweaks** — model field swaps, color changes, tool list adjustments, minor description edits where behavior is obviously unchanged. The "affects agent or skill behaviour" trigger below only applies when the change could plausibly alter how a session runs.
- **Unambiguous implementation of a prior decision** — the approach was already agreed in an issue or conversation; the commit is execution, not deliberation.

## Open a pull request

Open a PR when:

- **Multiple logical changes are bundled** — even if individually simple, grouping them for review makes intent clear and revert easier.
- **The change affects agent or skill behaviour in a non-obvious way** — new agents, rewritten system prompts, new skills, hook logic changes, or any edit where a reviewer's second look could catch a regression. Mechanical field-level edits do *not* qualify (see direct-commit list above).
- **The correct approach is uncertain** — if the implementation required non-obvious choices, a PR surfaces those choices for inspection.
- **The change touches shared infrastructure** — workflow files that affect CI/CD for the whole repo, `marketplace.json`, global settings.

## Local-only commits (no push)

A local commit without a push is acceptable **only as a checkpoint** — i.e., the work is intentionally incomplete and the next step is running tests or continuing implementation before the result is ready to share.

In all other cases, a local commit is not a finished state:

- **Working on a tracked issue** — push the branch and open a PR. The issue isn't closed until the work is visible and merged.
- **Standalone improvement (no issue)** — push to main if the change is small and low-risk; open a PR if review is warranted. Either way, push.
- **End of a work session** — push. A commit that exists only locally is invisible to collaborators and lost if the machine is wiped.

## Default rule

When in doubt: **commit directly** for instructions and config; **open a PR** for anything that changes how an agent, skill, plugin, or MCP server behaves.
