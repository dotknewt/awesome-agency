---
name: agent-development
description: This skill should be used when the user asks to "create an agent", "add an agent", "write a subagent", "agent frontmatter", "when to use description", "agent examples", "agent tools", "agent colors", "autonomous agent", or needs guidance on agent structure, system prompts, triggering conditions, or agent development best practices for Claude Code plugins.
metadata:
  version: "0.1.0"
---

# Agent Development for Claude Code Plugins

## Overview

Agents are autonomous subprocesses that handle complex, multi-step tasks independently. Understanding agent structure, triggering conditions, and system prompt design enables creating powerful autonomous capabilities.

**Key concepts:**
- Agents are FOR autonomous work, commands are FOR user-initiated actions
- Markdown file format with YAML frontmatter
- Triggering via a `description:` field containing `<example>`/`<commentary>` blocks — this is the convention every real agent in this repo uses (see `.claude/agents/agent-creator.md`, `plugin-validator.md`, `skill-reviewer.md`)
- System prompt (the markdown body) defines agent behavior
- Only `name` and `description` are required; `model`, `color`, and `tools` are optional

## Agent File Structure

### Complete Format

```markdown
---
name: agent-identifier
description: |
  Use this agent when [triggering conditions]. Examples:

  <example>
  Context: [Situation that should trigger the agent]
  user: "[User message]"
  assistant: "[Response before triggering, if any]"
  <commentary>
  [Why the agent should trigger in this scenario]
  </commentary>
  assistant: "I'll use the [agent-name] agent to [what it does]."
  </example>

  <example>
  Context: [Another situation — vary phrasing and explicit vs. proactive triggering]
  user: "[User message]"
  assistant: "[Response]"
  <commentary>
  [Why the agent should trigger]
  </commentary>
  </example>
model: inherit
color: blue
tools: ["Read", "Write", "Grep"]
---

You are [agent role description]...

**Your Core Responsibilities:**
1. [Responsibility 1]
2. [Responsibility 2]

**[Task] Process:**
[Step-by-step workflow]

**Output Format:**
[What to return]
```

`model`, `color`, and `tools` are all optional and can be omitted entirely — see [Frontmatter Fields](#frontmatter-fields).

## Frontmatter Fields

### name (required)

Agent identifier used for namespacing and invocation.

**Format:** lowercase, numbers, hyphens only
**Length:** 3-50 characters
**Pattern:** Must start and end with alphanumeric

**Good examples:** `code-reviewer`, `test-generator`, `api-docs-writer`, `security-analyzer`
**Bad examples:** `helper` (too generic), `-agent-` (starts/ends with hyphen), `my_agent` (underscores not allowed), `ag` (too short, < 3 chars)

### description (required)

Defines when Claude should trigger this agent. **This is the most critical field** — it is loaded into context whenever the agent is registered, so the harness can decide when to dispatch.

The repository convention is a multi-line YAML block scalar (`description: |`) that opens with "Use this agent when...", then gives 2-4 `<example>` blocks. Each example has a `Context`, a `user` message, an optional `assistant` line, and a `<commentary>` explaining why the agent should fire. This is not a stylistic choice — every real agent in `.claude/agents/` uses this exact shape, and `scripts/validate-agent.sh` checks for it.

Full format guide, anatomy of a good example, trigger-type taxonomy, and a template library: **`references/triggering-examples.md`**.

### model (optional)

Which model the agent should use. **Defaults to `inherit`** if the field is omitted.

**Options:** `inherit` (same model as parent — recommended), `sonnet`, `opus`, `haiku`

### color (optional)

Purely cosmetic visual identifier in the UI — it has no effect on agent behavior.

**Canonical palette:** `red`, `blue`, `green`, `yellow`, `purple`, `orange`, `pink`, `cyan`

> `magenta` appears in a couple of existing agents (e.g. `.claude/agents/agent-creator.md`) but is **not** part of the canonical palette. Treat it as a legacy value inherited from an earlier convention — prefer `purple` for new agents.

**Guidelines:** use distinct colors for different agents in the same plugin; blue/cyan for analysis or review, green for generation, yellow for validation/caution, red for security-critical work.

### tools (optional)

Restrict the agent to specific tools. **Default: if omitted, the agent has access to all tools.**

All three forms are valid and equivalent:

```yaml
# JSON-array form
tools: ["Read", "Write", "Grep"]
```

```yaml
# bare comma-separated string
tools: Read, Write, Grep
```

```yaml
# YAML block list
tools:
  - Read
  - Write
  - Grep
```

**Best practice:** limit tools to the minimum needed (principle of least privilege).

### disallowedTools (optional)

The inverse of `tools:` — a denylist. Use it when an agent should keep broad or full access but must never touch a specific tool. Accepts the same three forms as `tools:`.

```yaml
disallowedTools: ["Bash"]
```

Don't set both `tools` and `disallowedTools` on the same agent — pick an allow-list or a deny-list, not both.

## System Prompt Design

The markdown body becomes the agent's system prompt, written in second person ("You are...", "You will..."). For the complete structure (core responsibilities, process steps, quality standards, output format, edge cases), four reusable patterns (analysis / generation / validation / orchestration agents), writing-style rules, and common pitfalls with before/after examples, see **`references/system-prompt-design.md`**.

## Creating Agents

### Method 1: AI-Assisted Generation

> **See also:** this method, plus `examples/agent-creation-prompt.md` and `references/agent-creation-system-prompt.md`, walk through the same "extract intent → design persona → architect instructions → create identifier → craft `<example>` triggers" process that the live `.claude/agents/agent-creator.md` agent already automates end-to-end. For day-to-day agent creation in this repo, just ask for the `agent-creator` agent (or the `/create-agent` command) rather than driving the prompt by hand. These docs remain useful for driving the prompt manually (e.g. outside the Task tool) or for understanding the underlying pattern. A human should decide whether this content should eventually be consolidated into a shorter pointer.

`references/agent-creation-system-prompt.md` contains the exact system prompt used by `.claude/agents/agent-creator.md`, including its `<example>`-block triggering step. `examples/agent-creation-prompt.md` has a complete worked template.

### Method 2: Manual Creation

1. Choose agent identifier (3-50 chars, lowercase, hyphens)
2. Write `description:` with 2-4 `<example>`/`<commentary>` blocks (see `references/triggering-examples.md`)
3. Select model — optional, defaults to `inherit`
4. Choose a color — optional, cosmetic only
5. Define `tools` (or `disallowedTools`) if restricting access — optional
6. Write the system prompt (see `references/system-prompt-design.md`)
7. Save as `agents/agent-name.md`

## Validation Rules

### Identifier Validation

```
✅ Valid: code-reviewer, test-gen, api-analyzer-v2
❌ Invalid: ag (too short), -start (starts with hyphen), my_agent (underscore)
```

**Rules:** 3-50 characters; lowercase letters, numbers, hyphens only; must start and end with alphanumeric; no underscores, spaces, or special characters.

### Description Validation

**Length:** 10-5,000 characters
**Must include:** triggering conditions and 2-4 `<example>`/`<commentary>` blocks
**Best:** an opening prose sentence plus 2-4 well-varied examples

### System Prompt Validation

**Length:** 20-10,000 characters
**Best:** 500-3,000 characters
**Structure:** clear responsibilities, process, output format

## Agent Organization

### Plugin Agents Directory

```
plugin-name/
└── agents/
    ├── analyzer.md
    ├── reviewer.md
    └── generator.md
```

All `.md` files in `agents/` are auto-discovered.

### Namespacing

Agents are namespaced automatically:
- Single plugin: `agent-name`
- With subdirectories: `plugin:subdir:agent-name`

## Testing Agents

1. Write the agent with well-varied `<example>` blocks (see `references/triggering-examples.md` for debugging tips if it isn't triggering)
2. Try phrasings similar to — and different from — the examples
3. Confirm Claude dispatches to the agent as expected
4. Give it a typical task and confirm it follows its process, output format, and edge-case handling

## Quick Reference

### Minimal Agent

```markdown
---
name: simple-agent
description: |
  Use this agent when [condition]. Examples:

  <example>
  Context: [Situation]
  user: "[User message]"
  assistant: "I'll use the simple-agent agent to [does X]."
  <commentary>
  [Why it should trigger]
  </commentary>
  </example>

  <example>
  Context: [Another situation]
  user: "[User message]"
  assistant: "I'll use the simple-agent agent to [does X]."
  <commentary>
  [Why it should trigger]
  </commentary>
  </example>
---

You are an agent that [does X].

Process:
1. [Step 1]
2. [Step 2]

Output: [What to provide]
```

Note this minimal example omits `model`, `color`, and `tools` entirely — all optional.

### Frontmatter Fields Summary

| Field | Required | Format | Example |
|-------|----------|--------|---------|
| name | Yes | lowercase-hyphens | `code-reviewer` |
| description | Yes | Prose + `<example>`/`<commentary>` blocks | `Use this agent when... <example>...</example>` |
| model | No — defaults to `inherit` | `inherit`/`sonnet`/`opus`/`haiku` | `inherit` |
| color | No — cosmetic only | color name | `blue` |
| tools | No — defaults to all tools | array / comma-string / YAML list | `["Read", "Grep"]` |
| disallowedTools | No | same forms as `tools` | `["Bash"]` |

### Best Practices

Full DO/DON'T lists live in `references/triggering-examples.md` and `references/system-prompt-design.md`. In short:
- ✅ Ground triggering in 2-4 `<example>`/`<commentary>` blocks that cover both explicit and proactive scenarios — not prose-only descriptions
- ✅ Use `inherit` for model unless there's a specific need
- ✅ Choose tools by least privilege
- ✅ Write specific, structured system prompts and test triggering thoroughly
- ❌ Don't invent required fields — only `name`/`description` are required
- ❌ Don't give every agent in a plugin the same color
- ❌ Don't grant unnecessary tool access

## Additional Resources

### Canonical Spec

- **`docs/specs/agents/Agent-Specification.md`** — the source of truth for agent conventions in this repo. Where this skill and the spec disagree, the spec wins; this skill exists to teach it, not to redefine it.

### Reference Files

- **`references/system-prompt-design.md`** — complete system prompt patterns
- **`references/triggering-examples.md`** — `<example>`/`<commentary>` format, anatomy of a good example, and a template library
- **`references/agent-creation-system-prompt.md`** — the exact system prompt used by `.claude/agents/agent-creator.md`

### Example Files

- **`examples/agent-creation-prompt.md`** — AI-assisted agent generation template
- **`examples/complete-agent-examples.md`** — full agent examples for different use cases

### Utility Scripts

- **`scripts/validate-agent.sh`** — validate agent file structure

### Evals

- **`evals/evals.json`** — test cases for this skill's own output quality
- **`evals/eval_queries.json`** — labeled queries for testing whether this skill's `description` triggers correctly

### External Resources

- **Creating custom subagents**: https://code.claude.com/docs/en/sub-agents
- **Running agents in parallel**: https://code.claude.com/docs/en/agents
- **Agent teams**: https://code.claude.com/docs/en/agent-teams
- **Orchestration with dynamic workflows**: https://code.claude.com/docs/en/workflows
- **Isolating sessions with worktrees**: https://code.claude.com/docs/en/worktrees

## Implementation Workflow

To create an agent for a plugin:

1. Define agent purpose and triggering conditions
2. Choose creation method (AI-assisted via `agent-creator`, or manual)
3. Create `agents/agent-name.md`
4. Write frontmatter with `name` and `description`; add `model`/`color`/`tools` only if you need something other than the defaults
5. Write the system prompt following `references/system-prompt-design.md`
6. Write 2-4 `<example>`/`<commentary>` blocks in `description:` covering both explicit and proactive triggers
7. Validate with `scripts/validate-agent.sh`
8. Test triggering with real scenarios
9. Document the agent in the plugin README

Focus on clear triggering conditions and comprehensive system prompts for autonomous operation.
