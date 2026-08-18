# project-workflow

Close the spec gaps before any code is written. An idea gets interviewed into a
goal, a definition of done, and a check that the repo can actually support it —
each layer signed off by a human before the next one starts.

`project-manager` detects real commitment to build something ("I want to add
OAuth login"), not speculation ("what if we supported dark mode someday?"),
confirms a `specs/<slug>/` folder with the user, then runs three layers in
order. Every claim along the way is pushed through an itemized-claim test, so
"make it fast" never survives as a requirement.

Components:
- `project-manager` — orchestrator: intent detection, confirm gate, sequencing,
  wrap-up. Drafts no spec content itself.
- `project-spec` — Goal, Scope, Non-goals, Constraints → `specs/<slug>/spec.md`
- `project-verify` — measurable evaluation criteria plus any external success
  signal (a health check, a log line, a metric) → `specs/<slug>/verify.md`
- `project-environment` — AGENTS.md, knowledge-base, skill, and guardrail gaps
  in severity order, with hook configs drafted for risky actions →
  `specs/<slug>/environment.md`

Each layer is self-contained and can be invoked directly by name; the later two
check their dependencies and ask before running ungrounded.

## Usage

Install: `claude plugin install project-workflow@awesome-agency`

Then just describe what you want to build — `project-manager` triggers on real
build intent and asks before starting. To run a single layer, invoke it by
name ("run project-spec on this", "define done for X", "audit the environment
before we build this").

The four skills are also installable individually from this marketplace if you
only want one layer.

## Optional integrations

`project-environment` prefers to dispatch to the [`steward`](../steward) bundle's
maintainer agents (`instructions-maintainer`, `conventions-maintainer`,
`schema-maintainer`) rather than re-implementing repo auditing. If steward is
not installed, it asks before falling back to a built-in scan.

Portable across Claude Code and GitHub Copilot CLI: skills only, no commands,
hooks, agents, or MCP servers.
