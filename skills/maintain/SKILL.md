---
name: maintain
description: >
  Orchestrate a repo maintenance sweep: detect what changed, deploy the applicable
  read-only maintainer agents (user docs, spec docs, instructions, schemas) in
  parallel, and merge their drift reports into one prioritized list of proposed
  fixes. Use when the user asks to "run maintenance", "check for drift", "audit the
  repo", "are the docs/instructions/schemas up to date", or after landing a batch of
  changes. Arguments: none (changed scope since merge-base with the default branch),
  "full" (whole-repo sweep), or "since <ref>". Nothing is applied without the user's
  approval.
allowed-tools: Read Grep Glob Bash Agent Edit
---

# Maintain — drift-audit orchestrator

Run a maintenance sweep over this repository using specialized read-only maintainer
agents. You (the main session) do the scoping, routing, merging, and — only after
user approval — the applying. The agents only report.

## Phase 1 — Scope

Parse the argument:

- *(none)* → changed scope. Determine the default branch
  (`git remote show origin 2>/dev/null | sed -n 's/.*HEAD branch: //p'`, falling
  back to `main`), then `BASE=$(git merge-base HEAD origin/<default> 2>/dev/null || git merge-base HEAD <default>)`.
- `since <ref>` → `BASE=<ref>`.
- `full` → whole-repo sweep; skip diffing.

For changed scope, collect `git diff --name-status $BASE...HEAD` plus uncommitted
changes (`git status --porcelain`). If the combined list is empty, tell the user
there is nothing in scope and offer `full` or `since <ref>` — do not silently fall
back to a full sweep.

## Phase 2 — Route

Decide which maintainers apply. Dispatch a maintainer when ANY of its triggers hit
(for `full`, dispatch all four):

| Maintainer | Dispatch when |
|---|---|
| schema-maintainer | Changed files include `*.json`/`*.yaml`/`*.yml`/`*.toml`, markdown with structured frontmatter, generated files, or code that a generator/validator reads |
| docs-user-maintainer | Changed files include user-facing docs (README, usage/install guides), OR changed code alters user-visible behavior (commands, flags, features) |
| docs-spec-maintainer | Changed files include spec/architecture docs, OR changed code alters structure a spec describes (modules, formats, interfaces) |
| instructions-maintainer | Changed files include AGENTS.md/CLAUDE.md, OR changes touch project structure, tooling, scripts, or conventions instructions typically state |

When in doubt for a maintainer, dispatch it — a clean report is cheap; missed drift
is not. Tell the user which maintainers you are dispatching and why, one line each.

## Phase 3 — Dispatch in parallel

Invoke all selected agents in a single message (parallel Agent calls). Each prompt
must be self-contained — agents see nothing of this conversation. Include:

- The repo root path and default branch.
- The changed-file list with statuses (or "full sweep — discover your own scope").
- A one-paragraph summary of what the changes did (write it from the diff).
- The instruction: "Audit per your role. Report only — never edit files. Return
  your drift report in your standard format."

## Phase 4 — Merge and present

Combine the returned reports:

1. Drop duplicate findings (same file + same issue reported by two agents); keep the
   higher-severity copy and note both reporters.
2. Sort HIGH → MED → LOW, grouping by file within a severity.
3. Present one merged report: counts per severity, then the findings verbatim
   (file:line, issue, evidence, proposed fix, reporting agent), then the combined
   Clean list collapsed to one line per artifact.

Ask the user which fixes to apply (all / by severity / cherry-pick / none). Apply
approved fixes yourself with Edit — the maintainer agents never write. For
instruction-file fixes, if the instruction-management plugin is installed, offer its
skills as the applying mechanism instead of raw edits.

## Boundaries

- Never apply a fix that was not approved.
- Never dispatch an agent for a scope with zero relevant artifacts — report "not
  applicable" for it instead.
- If an agent returns malformed output, present what it returned under a "raw"
  heading rather than discarding it.
