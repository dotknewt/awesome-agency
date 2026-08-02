# Agent Triggering: Best Practices

Complete guide to writing `<example>`/`<commentary>` blocks that cause an agent to be dispatched reliably.

This is the convention actually used by every agent in `.claude/agents/` (`agent-creator.md`, `plugin-validator.md`, `skill-reviewer.md`) and documented as canonical in `docs/specs/agents/Agent-Specification.md`. `scripts/validate-agent.sh` checks for it. If you see an agent file using a plain-prose description with no `<example>` blocks, that file has drifted from the convention — bring it back in line rather than treating it as a second valid style.

## Where trigger examples live

Everything lives in the `description:` field in YAML frontmatter, as a multi-line block scalar:

```yaml
description: |
  Use this agent when [conditions]. Examples:

  <example>
  ...
  </example>

  <example>
  ...
  </example>
```

There is no separate "When to invoke" section in the agent body. The `description:` field is loaded into context whenever the agent is registered, so the harness can decide when to dispatch — that's exactly why the examples belong there rather than in the body (which is only loaded once the agent is already invoked).

## Anatomy of an `<example>` block

```markdown
<example>
Context: [One-line situation — what just happened or what the user is asking for]
user: "[Realistic user message, in their own words]"
assistant: "[Optional — what the assistant says/does before triggering, e.g. for proactive cases]"
<commentary>
[Why the agent should trigger here — the reasoning, not a restatement of the context]
</commentary>
assistant: "I'll use the [agent-name] agent to [what it does]."
</example>
```

Fields, in order:

1. **`Context:`** — a short situational label, third person, not a quote.
2. **`user:`** — the literal (or realistically paraphrased) user message. Quoted, first person, as the user would actually phrase it.
3. **`assistant:`** (optional, before commentary) — used for proactive-triggering examples, where the assistant has already been doing something and the trigger condition is "the assistant just did X," not a fresh user message.
4. **`<commentary>...</commentary>`** — explains *why* this scenario should dispatch the agent. This is reasoning for whoever reads the agent file later (including future-you), not part of what gets shown to the user.
5. **`assistant:`** (after commentary) — shows the assistant actually invoking the agent, e.g. `"I'll use the code-reviewer agent to check the recent changes."` Real agent files typically show the Agent/Task tool being used here.

### Real example (from `.claude/agents/plugin-validator.md`)

```markdown
<example>
Context: User finished creating a new plugin
user: "I've created my first plugin with commands and hooks"
assistant: "Great! Let me validate the plugin structure."
<commentary>
Plugin created, proactively validate to catch issues early.
</commentary>
assistant: "I'll use the plugin-validator agent to check the plugin."
</example>
```

## Trigger types to cover

Aim for 2-4 examples that span these axes:

### Explicit request
The user directly asks for what the agent does.

```markdown
<example>
Context: User explicitly requests validation
user: "Validate my plugin before I publish it"
assistant: "I'll use the plugin-validator agent to perform comprehensive validation."
<commentary>
Explicit validation request triggers the agent.
</commentary>
</example>
```

### Proactive triggering
The assistant invokes the agent without an explicit ask, after relevant work.

```markdown
<example>
Context: User just created a new plugin
user: "I've created my first plugin with commands and hooks"
assistant: "Great! Let me validate the plugin structure."
<commentary>
Plugin created, proactively validate to catch issues early.
</commentary>
assistant: "I'll use the plugin-validator agent to check the plugin."
</example>
```

### Different phrasing, same intent
Cover at least two different ways a user might ask for the same thing, rather than three near-duplicate examples that vary only in wording.

```markdown
<example>
Context: User describes needed functionality
user: "I need an agent that generates unit tests for my code"
assistant: "I'll use the agent-creator agent to create a test generation agent."
<commentary>
User describes agent need, trigger agent-creator to build it.
</commentary>
</example>
```

### Implicit / described need
The user implies the need without naming the agent or using an obvious keyword.

```markdown
<example>
Context: User describes code as hard to follow
user: "This function is impossible to follow, can you make it clearer?"
assistant: "I'll use the refactoring agent to improve readability."
<commentary>
User describes a symptom (unclear code) rather than naming refactoring directly — still a trigger.
</commentary>
</example>
```

## How many examples?

- **Minimum: 2.** Usually one explicit + one proactive.
- **Recommended: 2-4.** All three real agents in this repo (`agent-creator`, `plugin-validator`, `skill-reviewer`) use exactly 3.
- **Maximum: ~5.** More than that bloats the frontmatter (loaded on every registration) without adding much routing signal.

## Template library

### Code review agent

```yaml
description: |
  Use this agent when the user has written code and needs quality review, security analysis, or best practices validation. Examples:

  <example>
  Context: User just finished implementing a feature
  user: "Can you check if this looks good?"
  assistant: "I'll use the code-reviewer agent to review the recent changes."
  <commentary>
  User asks for a review of a just-completed feature — explicit trigger.
  </commentary>
  </example>

  <example>
  Context: Assistant just authored new code
  user: "Add a login endpoint"
  assistant: "Here's the login endpoint. Now let me review it before we call this done."
  <commentary>
  Assistant proactively reviews newly-written, security-sensitive code before declaring the task complete.
  </commentary>
  assistant: "I'll use the code-reviewer agent to check the new endpoint."
  </example>

  <example>
  Context: User signals readiness to open a PR
  user: "I think we're done here, let's ship this"
  assistant: "Before opening the PR, let me run a final review."
  <commentary>
  Pre-PR sanity check — proactively review the full diff first.
  </commentary>
  assistant: "I'll use the code-reviewer agent to check the diff."
  </example>
```

### Test generation agent

```yaml
description: |
  Use this agent when the user needs tests generated for code that lacks them. Examples:

  <example>
  Context: User asks for tests on a specific module
  user: "Write unit tests for the auth module"
  assistant: "I'll use the test-generator agent to create a test suite for the auth module."
  <commentary>
  Explicit test request for a named module.
  </commentary>
  </example>

  <example>
  Context: Assistant just wrote a new function with no tests
  user: "Add a function to parse the config file"
  assistant: "Here's the parser. It has no test coverage yet, so let me add tests before finishing."
  <commentary>
  Proactive coverage after writing new, untested code.
  </commentary>
  assistant: "I'll use the test-generator agent to generate tests for the new parser."
  </example>
```

### Documentation agent

```yaml
description: |
  Use this agent when the user needs documentation written or updated, especially for APIs. Examples:

  <example>
  Context: User asks for docs on a specific endpoint
  user: "Can you document the /users endpoint?"
  assistant: "I'll use the docs-generator agent to document the /users endpoint."
  <commentary>
  Explicit doc request for a named surface.
  </commentary>
  </example>

  <example>
  Context: Assistant just added a new public API function
  user: "Add a public exportReport() function"
  assistant: "Added exportReport(). It has no docstring yet, so let me document it."
  <commentary>
  Proactive documentation after adding new public API surface without docs.
  </commentary>
  assistant: "I'll use the docs-generator agent to document the new function."
  </example>
```

### Validation agent

```yaml
description: |
  Use this agent when the user needs code validated before commit or merge. Examples:

  <example>
  Context: User signals readiness to commit
  user: "Ready to commit this"
  assistant: "Let me validate first."
  <commentary>
  Pre-commit validation — run before the commit lands, surface issues first.
  </commentary>
  assistant: "I'll use the validation agent to check everything first."
  </example>

  <example>
  Context: User explicitly asks for validation
  user: "Can you validate this config?"
  assistant: "I'll use the validation agent to check the config."
  <commentary>
  Explicit validation request.
  </commentary>
  </example>
```

## Debugging triggering issues

### Agent not triggering

Check:
1. Do the examples' `Context:`/`user:` lines cover the actual phrasings the user is using?
2. Is there a more-specific competing agent winning the routing decision?
3. Does the opening prose sentence in `description:` clearly state the domain?

Fix: add or vary examples, and tighten the opening prose sentence.

### Agent triggers too often

Check:
1. The examples are too generic or overlap with another agent's scope.
2. Nothing in `description:` says when *not* to use the agent.

Fix: narrow the examples; add a line to the opening prose noting when not to invoke, if needed.

### Agent triggers in the wrong scenarios

Check whether the examples match what the agent's system prompt actually does.

Fix: rewrite the examples (and/or the `<commentary>`) to match the agent's real capabilities.

## Best practices summary

- Put trigger examples in `description:` as `<example>`/`<commentary>` blocks — not a body "When to invoke" section, not prose-only
- Cover both explicit and proactive triggering
- Vary phrasing across examples rather than repeating near-duplicates
- Show the assistant actually invoking the agent in at least the final `assistant:` line of each example
- Keep `<commentary>` focused on *why*, not a restatement of `Context:`

## Conclusion

Reliable triggering comes from concrete, varied `<example>`/`<commentary>` blocks in the `description:` field — the same convention used across every real agent in this repo.
