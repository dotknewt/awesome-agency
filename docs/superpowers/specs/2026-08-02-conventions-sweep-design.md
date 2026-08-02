# Conventions in the maintenance sweep — design

**Status:** approved
**Date:** 2026-08-02

## Problem

After the steward merge, `conventions` is the only steward skill the `maintain`
orchestrator does not orchestrate. Nothing in a sweep audits a repo against
`skills/conventions/references/docs-layout.md` or `cli-standards.md`, so a repo
drifting from the conventions — planning docs outside `docs/TODO.md` /
`docs/STATE.md`, user docs outside `docs/user/`, a Python CLI with pip-first
install docs or missing completion — goes unflagged.

## Decision

Add a fifth read-only maintainer agent, **`conventions-maintainer`**, to the
steward bundle (v1.0.0 → v1.1.0) and wire it into `maintain`'s dispatch table.

- **New agent, not folded into an existing one.** Conventions span two domains
  (docs layout ~ docs-user, CLI toolchain ~ schema); folding it into either
  blurs both. The name completes the existing family (docs-user-, docs-spec-,
  instructions-, schema-maintainer). Haiku-pinned — a mechanical checklist
  audit like schema-maintainer.
- **Single source of truth.** The agent reads the `conventions` skill's
  reference files via `${CLAUDE_PLUGIN_ROOT}/skills/conventions/references/`
  (precedent: `dockerize-mcp-server`), with a Glob fallback. For the
  micro-install, `agents/conventions-maintainer/skills/conventions` symlinks
  the pool skill so the same relative path resolves. No normative content is
  duplicated into the agent prompt.
- **Remediation mirrors instructions-maintainer.** The agent reports only; its
  closing line recommends the `conventions` skill's scaffold mode as the
  applying mechanism, with `state-keeper` for `docs/STATE.md` creation.
- **Dispatch rule.** Fire on full sweeps, and on changed scope when changes
  touch planning/user docs, the root README, `pyproject.toml`, or Python CLI
  code.
- **Severity cap.** Adopting the conventions is a choice: pure-absence findings
  cap at MED; HIGH is reserved for artifacts that actively contradict the
  conventions (e.g. pip documented as primary in a uv project).

## Consequences

- `plugins/steward/.claude-plugin/plugin.json` lists the new agent explicitly
  (file symlinks are skipped by the default `./agents/` scan) and bumps to
  1.1.0.
- The generator emits a `conventions-maintainer-agent` micro-entry
  automatically; no generator changes.
- Overlap with docs-user-maintainer on `docs/user/` placement is handled by
  maintain Phase 4's existing dedup rule.
