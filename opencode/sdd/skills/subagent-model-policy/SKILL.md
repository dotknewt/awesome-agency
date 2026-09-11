---
name: subagent-model-policy
description: Use when the user says "use sdd", requests subagent-driven development, asks to spawn smaller-model subagents, or specifies a model for delegated work in OpenCode.
---

# Subagent Model Policy

The shipped default is **openai/gpt-5.6-sol for every delegated role unless the user specifies another model**. Load `subagent-driven-development` for the SDD workflow; this policy replaces its model-selection advice, automatic fix-loop upgrades, and strongest-model final-review rule. Preserve the workflow's task and review gates.

## Selection

| Condition | Selected model |
| --- | --- |
| Explicit task/role override | User's exact provider/model ID |
| Explicit run-wide override | User's exact provider/model ID |
| Neither | `openai/gpt-5.6-sol` |

Apply this to implementers, fixers, task reviewers, re-reviewers, and final reviewers. A complex task, deadline, repeated failure, or final review does not authorize a model upgrade. Improve the brief or split work while retaining the selected model. A later explicit user instruction wins within its scope. Run overrides expire with that run; they do not rewrite the shipped default.

## Dispatch contract

1. Record the run default and any role/task overrides in the SDD ledger so they survive compaction.
2. Call `subagent_dispatch` with `description`, `prompt`, `role` (`worker` or `reviewer`), and the resolved `model`. Provide focused briefs and report paths using the SDD workflow. Reviewers return their report; the controller saves it because reviewers cannot edit files or run shell commands.
3. Record returned `task_id`, actual `model`, and role with the task. Model identity comes from response metadata, not the child's self-description.
4. Resume with `task_id`, matching `role`, and the resolved `model`. Omission preserves the child's last model, but explicit selection is preferred. Fresh roles/tasks get fresh children.

Example: “use sdd with openai/gpt-6-astra for reviewers” means workers/fixers use Sol and **all reviewer roles**, including final review, use Astra:

```json
{"description":"Review task 1","prompt":"Read the supplied task brief, report, and review package; return spec and quality verdicts.","role":"reviewer","model":"openai/gpt-6-astra"}
```

## Common mistakes

- **Task has no model field:** do not invent one or put model instructions in the prompt. Use `subagent_dispatch`; it explicitly passes the model through the SDK.
- **Tool missing after installation:** quit and restart OpenCode. Report the blocker rather than silently using an inherited model.
- **Unavailable model or identity mismatch:** report the error and request a user-selected replacement; no silent fallback.
- **SDD says keep going:** inability to enforce the selected model is an additional dispatch blocker under this policy.
- **Missing model ledger after compaction:** recover overrides from the user's instructions and child-session metadata. If the intended override remains ambiguous, ask before dispatching.
- **“SDD requires a stronger final reviewer”:** the shipped policy default overrides that skill's default advice.
- **`small_model` configuration:** it is not the default for Task subagents.
- **Nested delegation:** workers and reviewers cannot dispatch their own agents; the controller owns dispatch.

Implementation: `awesome-agency/runtime/subagent-dispatch.ts` relative to the install target, with generated `sdd-worker`/`sdd-reviewer` agent definitions. Repository tests: `node --import ./opencode/node_modules/tsx/dist/loader.mjs --test opencode/sdd/skills/subagent-model-policy/tests/dispatch.test.mjs`.
