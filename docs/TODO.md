# copy/add skill,agent,instruction,plugin etc from source
- When instructed to add/copy an extension and given a source (github repo, marketplace etc), do not install it, but rather add it as if project root was the custom configs directory (like .claude/, .github/ etc)

# conventions
- default branch name when creating repositories is "main"
- default to delegating todo writing to small, fast, cheap model subagent

# steward
- Extend the steward plugin to also maintain tests

# contract ownership
- Should we have a contract owner; something(skill,agent) that owns contracts where contracts are needed (schema, tests .. ?)

# docker-toolkit
- Evaluate gains if modifying docker-toolkit to smaller components
  - an agent specialized in mcp conversion
  - a skill for converting a non-docker mcp server to docker mcp

## deferred
- scripts/build-and-register.sh
  - automate build + catalog registration + secret set for the `dockerize-mcp-server` skill (roadmapped for v2)
- Copilot model-selection
  - GitHub Copilot CLI has no equivalent to Claude Code's agent `model:` frontmatter — it
    always runs on the calling session's model and silently ignores any pinned full model
    ID. There is currently no way to express a Claude-Code-only model-routing hint that
    Copilot also honors. Revisit if/when Copilot adds model-selection support; see
    `.github/host-compat.json`'s `agent-model-alias` capability and AGENTS.md's Host
    portability section.
  - Copilot Chat in VS Code's `runSubagent` tool is a *different* surface from Copilot
    CLI and is not tracked in `.github/host-compat.json` at all. Unlike Copilot CLI's
    silent session-model fallback, `runSubagent` requires an exact `"Model Name (Vendor)"`
    string and hard-errors ("model not found") on an unrecognized value — observed
    2026-08-13. There is no `models.list`-style API or CLI flag exposed to an
    agent/skill at runtime on either Copilot surface to resolve a valid value in
    advance. As a stopgap, `plugins/superpowers/skills/subagent-driven-development/`
    (a `.vendored` bundle) was patched to tell the dispatching agent to omit `model`
    rather than guess a value when the dispatch tool's accepted format isn't known,
    and to retry without `model` if a dispatch is rejected for its model value. That
    patch lives in vendored files and can be lost on the next upstream sync of
    superpowers — it should ideally be contributed upstream, and/or Copilot Chat
    should get its own `host-compat.json` entry once its behavior is verified more
    broadly than this one observation.
  - The same Model Selection section points at
    `plugins/superpowers/skills/subagent-driven-development/references/copilot-model-ids.md`,
    a hand-maintained snapshot of Copilot CLI's `--model` short-id catalog
    (anthropic/openai ids, dated 2026-08-13), so a dispatching agent can try a real
    value instead of only omitting one. This is a static list, not a live query — it
    needs periodic refresh as models are added/retired, applies only to Copilot CLI's
    short-id format (not Copilot Chat's `"Model Name (Vendor)"` format), and still
    falls back to the omit-and-retry behavior above if a listed id is rejected.
- `${CLAUDE_PLUGIN_ROOT}` verification in Copilot
  - Support for `${CLAUDE_PLUGIN_ROOT}` resolution in GitHub Copilot CLI is unverified —
    the vendored `superpowers` `SessionStart` hook suggests it may work despite docs saying
    otherwise. Confirm against a real Copilot install and update AGENTS.md's Host
    portability section with a definitive answer.

