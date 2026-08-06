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
cross-platform `run-hook.cmd` wrapper), `.claude-plugin/plugin.json`, and
`LICENSE`. Upstream tests, docs, release notes, and non-Claude platform
manifests (Codex/Cursor/Kimi/OpenCode/Pi/Gemini) are intentionally omitted.

## Updating from upstream

Sync `skills/` and `hooks/` from an upstream checkout, keep the version in
`.claude-plugin/plugin.json` aligned with the upstream release, then re-run
`.github/scripts/generate-marketplace.py`.
