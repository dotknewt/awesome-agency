# Defending LLMs (Hardening Reference)

> Load this file when the task is hardening an LLM-backed application against prompt injection, jailbreaks, or context poisoning — designing guardrails, isolating untrusted content, or validating inputs/outputs. Pairs with `references/exploiting.md`, which documents the attack techniques these defenses target.

### Input Sanitization and Validation

- **Schema-validate** structured inputs before injection into prompts.
- **Length limits** on user content reduce injection surface.
- **Strip or encode** special sequences: `<`, `>`, XML tags, markdown delimiters your prompt uses as structure.
- **Content classifiers** (a second, cheap model call) to flag injection attempts before they reach the main model.

### Context Isolation

The root cause of most injection attacks is that user-supplied content shares the same channel as instructions. Mitigations:

```
Option A: XML/delimiter isolation
  <system>…instructions…</system>
  <user_content>…untrusted…</user_content>

Option B: Separate API call for untrusted content
  Step 1: Classify/summarize untrusted content with a restricted model
  Step 2: Inject only the structured summary into the main prompt

Option C: Tool boundary
  Never inject raw tool output into prompt; parse and project to a schema first
```

### Output Validation

- **Format enforcement**: constrain model output to JSON schema; reject malformed responses.
- **Content filtering**: scan output for PII, policy violations, injected instruction echoes.
- **Action confirmation**: for agentic systems, require human-in-the-loop before irreversible actions.

### Minimal Privilege Context

- Only include context the model needs for the current step.
- Avoid injecting credentials, secrets, or sensitive data into prompts — use tool calls that return only what's needed.
- Rotate/expire context: don't carry sensitive retrieved data across turns beyond its useful life.

### Defense Patterns Summary

```
1. Classify before inject   — run a cheap guard model on untrusted content
2. Isolate by channel       — XML delimiters or separate calls for user vs. system content
3. Constrain outputs        — structured schemas, not free text, for actionable responses
4. Log and audit            — full prompt/response pairs; alerts on anomalous patterns
5. HITL on high-stakes ops  — confirm before deleting, writing, or sending
```
