# Maintainer-Toolkit Design

Approved 2026-08-02. Source: TODO.md `# maintainer-agents`.

## Purpose
A shippable plugin bundle that keeps a repo's secondary artifacts — documentation,
agent instructions, structured schemas/manifests — from drifting out of sync with the
code. Everything is report-and-propose: maintainers detect drift and return proposed
edits; nothing is applied without the user.

## Architecture
One orchestration skill + four read-only maintainer agents, following the
`engineering-toolkit:code-review` parallel-dispatch pattern and the `state-keeper`
boundary pattern.

1. **`maintain` skill** (`/maintain`) — runs in the main session. Scopes the work
   (git diff since merge-base with the default branch by default; `full` for a
   whole-repo sweep; `since <ref>` to override), classifies which artifact types are
   affected, dispatches only the applicable maintainer agents in parallel via the
   Agent tool, merges their findings into one prioritized drift report. The user
   picks what to apply; the main session applies it.
2. **`docs-user-maintainer`** — audits user-facing docs (READMEs, install/usage
   guides) against current behavior. Inherits session model.
3. **`docs-spec-maintainer`** — audits spec/architecture docs (docs/, ADRs, API
   references) against the code they describe. Inherits session model.
4. **`instructions-maintainer`** — audits AGENTS.md/CLAUDE.md for stale guidance.
   Does not duplicate the instruction-management plugin; recommends it for applying
   fixes. Inherits session model.
5. **`schema-maintainer`** — checks structured artifacts (JSON/YAML/TOML manifests,
   config files, markdown frontmatter, generated files) for parse errors, internal
   inconsistency, and generator/validator drift. Pinned to Haiku.

## Boundaries
All four agents: `tools: Read, Grep, Glob, Bash` (read-only commands only), never
edit files, shared severity-tagged report format. Each is independently installable
as a marketplace micro-entry.

## Packaging
New `plugins/maintainer-toolkit/` bundle: agents in the `agents/` pool symlinked into
the bundle and listed explicitly in `plugin.json`; skill in the `skills/` pool;
marketplace regenerated via `.github/scripts/generate-marketplace.py`.
