---
name: loop-me
description: Use this skill when the user wants to turn a recurring pattern — a loop, like their morning routine, a weekly review, or how they triage a channel — into a finished, question-free workflow spec under this workspace's workflows/*.md. Trigger on casual openers ("let's figure out my morning routine"), on precise requests naming an existing workflows/*.md file to revise, and on requests to surface loops worth specifying that the user hasn't noticed. If NOTES.md is missing or thin, trigger to interview the user about their tools, channels, and terminology first. Runs a relentless, one-question-at-a-time grilling session using this skill's Trigger/Checkpoint/Push right/Brief vocabulary. Do not trigger to build, implement, or run the automation a spec describes, to write a generic PRD unrelated to a recurring loop, or to hand a conversation off to a background agent — those need different skills.
disable-model-invocation: true
---

Run a stateful `/grilling` session whose only output is **workflow** specs. Use the grilling discipline — relentless, one question at a time, a recommended answer attached to each — aimed at the vocabulary and goal below. Create, edit, and delete specs as the grilling resolves things.

## Invocation

Invoked with an argument naming a workflow — a loop's name, or an existing `workflows/*.md` path — grill that workflow specifically, editing the named file (creating it if the name doesn't yet exist as a file).

Invoked with no argument, go find one: scan `workflows/*.md` for a spec that is thin, stalled, or still carries an open question, or use [the loop lens](#the-loop-lens) below to propose a loop the user hasn't noticed yet. Propose the candidate and confirm with the user before grilling it — never assume which loop is meant.

## The loop lens

A **loop** is a recurring pattern in the user's life: their career, their week, their morning, a single repeated activity. Picturing a life as loops within loops reveals how predictable its activities really are — which is what makes them worth **delegating**. Use the lens to find loops worth specifying, and propose ones the user hasn't noticed.

A **workflow** is the spec of one loop, made real. You run a workflow on a loop — the loop is its running instantiation. Workflows live in `workflows/*.md` and are the source of truth.

## Vocabulary

A shared language, reached for only when a workflow calls for it — never a checklist. **Mandate nothing structural**: a workflow needs no AI, no checkpoint, and no schedule unless the grilling shows it does.

- **Trigger** — what fires each run: an **event** (a new email, a new issue) or a **schedule** (every morning). Event-triggering is usually the more efficient.
- **Checkpoint** — a human-in-the-loop point where the user is asked to verify or decide. Some workflows have none and run autonomously; some use no AI at all.
- **Push right** — defer the checkpoint as far as it will go. Do maximal work before involving the human, so they are asked once, late, with everything prepared.
- **Brief** — what a checkpoint presents: a tight, decision-ready summary — what was produced, why, and a link down to the asset itself — never the raw output. The user reads a brief, not a draft. Speed of review is imperative.

## Example

A finished spec for one loop, showing the vocabulary applied. Match this shape, not this content, when judging whether a spec is done:

```markdown
# Inbox triage (workflows/inbox-triage.md)

**Trigger:** event — a new email lands in the "Support" Gmail label.

**Steps:**
1. Classify the email as bug report, billing question, or spam, using the last 20 resolved threads as examples.
2. Spam is archived immediately — no draft, no checkpoint.
3. For bug reports and billing questions, draft a reply and attach the matching FAQ link if one exists.

**Checkpoint:** after step 3, before sending — only for bug reports and billing questions.

**Brief:** the classified category, the drafted reply, and the FAQ link if attached — one paragraph, not the raw thread.

**Push right:** classification, drafting, and FAQ matching all happen before the checkpoint, so the human is asked once, late, with a send-ready reply — never asked to triage or write it themselves.

No schedule; this loop is fully event-triggered and runs autonomously except for the one checkpoint on real replies.
```

## Definition of done

A workflow spec is done when an implementer agent could build it without asking a single question. Grill until then; nothing is done while a question remains.

## The workspace

- `workflows/*.md` — one spec per workflow.
- `NOTES.md` — raw notes on the user's world: the tools they use, the channels they process, and their own terminology for both. When it is empty or thin, interview them about their world before specifying anything. Sharpen fuzzy terms into canonical ones as they surface, and record them here.
