# superpowers

Vendored redistribution of [obra/superpowers](https://github.com/obra/superpowers)
(MIT, © Jesse Vincent), packaged as a bundle in the `awesome-agency` marketplace.

Superpowers is a complete development methodology for coding agents: brainstorm a
spec, write a plan, execute it with subagent-driven TDD, and review the result.
A `SessionStart` hook injects the `using-superpowers` skill so the rest trigger
automatically.

## Install

```
claude plugin marketplace add dotknewt/awesome-agency
claude plugin install superpowers@awesome-agency
```

## Skills

| Skill | Purpose |
| --- | --- |
| `brainstorming` | Turn a vague idea into a reviewed design spec. |
| `writing-plans` | Turn a spec into an implementation plan. |
| `executing-plans` | Work a plan phase by phase. |
| `subagent-driven-development` | Dispatch per-task subagents with review gates. |
| `dispatching-parallel-agents` | Fan work out across parallel agents. |
| `test-driven-development` | Strict red/green TDD loop. |
| `systematic-debugging` | Root-cause debugging framework. |
| `verification-before-completion` | Prove work is done before claiming done. |
| `requesting-code-review` / `receiving-code-review` | Both sides of a review. |
| `using-git-worktrees` | Isolated worktree workflow. |
| `finishing-a-development-branch` | Land or abandon a branch cleanly. |
| `writing-skills` | Author new skills. |
| `using-superpowers` | Entry point — how to find and use the rest. |

## Contents

Only shipping content is vendored: `skills/`, `hooks/` (SessionStart injector +
cross-platform `run-hook.cmd` wrapper), `.claude-plugin/plugin.json`, `LICENSE`,
and `RELEASE-NOTES.md` (kept as the upstream-drift reference — see below).
Upstream tests, docs, and non-Claude platform manifests
(Codex/Cursor/Kimi/OpenCode/Pi/Gemini) are intentionally omitted.

## Updating from upstream

`RELEASE-NOTES.md` here is pinned to the vendored version (currently v6.2.0).
To check for upstream changes, diff it against
[upstream RELEASE-NOTES.md](https://github.com/obra/superpowers/blob/main/RELEASE-NOTES.md):

```
curl -sfL https://raw.githubusercontent.com/obra/superpowers/main/RELEASE-NOTES.md \
  | diff plugins/superpowers/RELEASE-NOTES.md - | head -40
```

To sync: copy `skills/` and `hooks/` from the upstream tag, refresh
`RELEASE-NOTES.md` from that same tag, set the version in
`.claude-plugin/plugin.json` to match, then re-run
`.github/scripts/generate-marketplace.py`.
