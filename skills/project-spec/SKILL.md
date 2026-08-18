---
name: project-spec
description: Interviews the user to draft the Goal, Scope, Non-goals, and Constraints of a new idea, feature, task, or project into specs/SLUG/spec.md — the first of three spec-gap-closing layers, run before any code, docs, or planning. Use when invoked directly ("run project-spec on this", "let's spec out X") or as the first step dispatched by project-manager. Every claim is tested for measurability and every checkpoint requires explicit human sign-off before the draft advances.
---

# project-spec

## Why this exists

Most scope drift starts in the very first sentence of an idea — "make it fast," "support users," "handle errors gracefully." Each of those sounds like a requirement but isn't one, because nothing about it can be checked. This skill's job is to turn a rough idea into a Goal/Scope/Non-goals/Constraints draft where every claim has been tested for measurability before it's allowed to stand.

Read `references/checkpoint-protocol.md` before starting — it defines the itemized claim test, the attribution rule (which claims are the user's and which are yours), the load-bearing test, checkpoint timing, the critic mechanism, and the logging format. Everything below assumes you've read it.

## Standalone invocation

If you were invoked directly (not via project-manager) and `specs/SLUG/` doesn't exist yet, propose a kebab-case slug from the idea's working title and confirm it with the user in one question before creating the folder — the same gate project-manager would have used. If the folder already exists with a `spec.md` mid-draft, resume from wherever its frontmatter `status` and section headers indicate you left off, rather than restarting.

## Interview flow

Draft continuously through these four sections, in order, applying the checkpoint protocol as you go — checkpoints are adaptive (see protocol section 4), not fixed to section boundaries:

1. **Goal** — what outcome does this idea produce, for whom, and why now? A goal claim must name an observable end-state, not an intention ("reduce signup abandonment by making the form shorter" vs. "improve signup").
2. **Scope** — what's explicitly included in this piece of work. Each scope item should be phrased so someone could later check "is this in or out" without asking you.
3. **Non-goals** — what's explicitly excluded, especially things a reasonable person might assume are included. Silence here is exactly the kind of gap this skill exists to prevent — if you can't think of any non-goals, that itself is worth flagging to the human rather than skipping the section.
4. **Constraints** — technical, timeline, resource, or policy boundaries the solution must respect. Treat "assumptions" the same way: an unstated assumption is a constraint nobody wrote down.

For each section, before presenting it at a checkpoint, run every claim through the itemized test, the attribution rule, and the load-bearing test from the protocol. Most of an early Goal draft is your wording, not the user's — a claim the user only ever saw as an option label you wrote is `@approved` at best, never something they told you.

## Writing spec.md

Create or update `specs/SLUG/spec.md` with this shape. Target 200-500 words total — a guide toward keeping the spec atomic and readable in one sitting, not a hard cap that would force truncating a genuinely necessary claim.

```markdown
---
idea: "<working title>"
slug: <slug>
status: draft | in-progress | complete
layers_complete: []
---

## Goal
<prose + itemized claims where useful>

## Scope
...

## Non-goals
...

## Constraints
...
```

Set `status: complete` and add `spec` to `layers_complete` only after the final checkpoint (Constraints) has an explicit human approval logged. Append every checkpoint to `specs/SLUG/spec.decisions.log` per the protocol's logging format.

## Handing off

When `spec.md` reaches `status: complete`, tell the user plainly that the Spec layer is done and that `project-verify` is the next step (whether they're running this standalone or via project-manager, don't assume — say it either way so nothing is silently expected).
