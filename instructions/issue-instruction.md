## Choosing the right issue template

| Template | Title prefix | Use when |
|---|---|---|
| `new.yml` | `[new]` | Requesting a brand-new artifact that does not yet exist |
| `change.yml` | `[change]` | Improving or extending an artifact that already exists |
| `review.yml` | `[revise]` | Auditing an existing artifact for quality or correctness |

`new.yml` automatically applies `action:new`. `review.yml` automatically applies `action:revise`. `change.yml` requires selecting `improve` or `extend` from a dropdown — the `apply-labels` workflow applies the matching `action:*` label.

## Artifact type labels (`type:*`)

Every issue gets exactly one `type:*` label.

| Label | Applies to |
|---|---|
| `type:agent` | Claude Code subagent definition (`.claude/agents/*.md`) |
| `type:skill` | Claude Code skill (`skills/*/SKILL.md`) |
| `type:plugin` | Distributable plugin bundle (`plugins/*/`) |
| `type:hook` | Claude Code lifecycle hook (PreToolUse / PostToolUse / Stop / etc.) |
| `type:mcp` | Model Context Protocol server (`mcp/*/`) |
| `type:instruction` | Project-memory instruction file (`CLAUDE.md`, `AGENTS.md`, `instructions/*.md`) |

## Action labels (`action:*`)

Every issue gets exactly one `action:*` label.

| Label | Meaning |
|---|---|
| `action:new` | Create a new artifact from scratch |
| `action:improve` | Fix a defect or improve an existing artifact's behavior |
| `action:extend` | Add a new capability to an existing artifact |
| `action:revise` | Review an existing artifact for quality or correctness |

## Label combinations

- **`[new]` template** → `type:<artifact>` + `action:new` (auto-applied by template)
- **`[change]` template + improve** → `type:<artifact>` + `action:improve`
- **`[change]` template + extend** → `type:<artifact>` + `action:extend`
- **`[revise]` template** → `type:<artifact>` + `action:revise` (auto-applied by template)

GitHub-default labels (`bug`, `documentation`, `enhancement`, `help wanted`, `question`) are optional modifiers and do not replace `type:*` / `action:*`.

## For agents

Before calling `gh issue create`, run `gh label list --json name --limit 100` to get the live label set for this repo. Use this file to select the right `type:*` and `action:*` label combination. Never invent labels that do not appear in `gh label list` output.
