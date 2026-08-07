# Tighten superpower instructions so that the subagents don't return their full report into orchestrators context.
- The skill's own guidance is that subagents hand artifacts over as files and return a short contract.
- Tighten instructions so its enforced for implementers *AND* reviewers.
# copy/add skill,agent,instruction,plugin etc from source
- When instructed to add/copy an extension and given a source (github repo, marketplace etc), do not install it, but rather add it as if project root was the custom configs directory (like .claude/, .github/ etc)

# conventions
- default branch name when creating repositories is "main"
- default to delegating todo writing to small, fast, cheap model subagent

# steward
- additional command that performs instructions-audit only adding changes that surfaced in the last 5 commits
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
- `${CLAUDE_PLUGIN_ROOT}` verification in Copilot
  - Support for `${CLAUDE_PLUGIN_ROOT}` resolution in GitHub Copilot CLI is unverified —
    the vendored `superpowers` `SessionStart` hook suggests it may work despite docs saying
    otherwise. Confirm against a real Copilot install and update AGENTS.md's Host
    portability section with a definitive answer.

