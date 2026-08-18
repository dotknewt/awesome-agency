---
name: project-manager
description: Orchestrates a spec-gap-closing interview before any code, docs, or planning begins on a new idea, feature, task, project, extension, or enhancement. Use this whenever the user expresses real intent to build something new — phrases like "I want to add...", "let's build...", "new project idea:", "I need a feature that..." — NOT on speculative musing like "what if we..." or "someday maybe...". Runs project-spec, then project-verify, then project-environment in sequence, with an explicit confirm gate before starting and a human sign-off at every checkpoint along the way. Make sure to invoke this before touching code or writing a plan whenever the user commits to a new piece of work, even if they don't explicitly ask for a "spec".
---

# project-manager

## Why this exists

Ideas drift into code before anyone has agreed what "done" means. Vague requirements get silently interpreted by whoever picks up the work next — which, for an agent, means guessing and moving on. This skill exists to make that guessing impossible: nothing gets built until the goal, the definition of success, and the surrounding environment have all been checked explicitly, and every consequential decision along the way was seen and approved by a human, not assumed.

You are the orchestrator. You do not draft spec content yourself — you decide whether to start, hand off to the three layer skills in order, and refuse to let one begin before the previous one has been explicitly signed off.

## Step 1 — Detect real intent, not speculation

Only treat a message as triggering this skill if it signals actual commitment to build, not exploratory musing. Use judgment, not keyword matching:

| Signal | Trigger? |
|---|---|
| "I want to add OAuth login" | Yes — commitment |
| "let's build a Slack bot for standups" | Yes — commitment |
| "new project idea: a habit tracker" | Yes — explicit declaration |
| "what if we supported dark mode someday?" | No — hypothetical |
| "thinking about a browser extension" | No — musing, not committing |
| "not sure if this is worth doing, but maybe X?" | No — hedged |

If you're unsure which bucket a message falls in, err toward not triggering — a missed trigger costs the user one extra sentence to invoke this skill by name; a false trigger costs them an interruption to something they didn't ask to formalize.

## Step 2 — The confirm gate (never skip this)

Before asking a single interview question or writing any file, stop and get explicit confirmation. Propose a short kebab-case slug derived from the idea's working title (e.g. "OAuth login" → `oauth-login`), and combine the start-confirmation and the slug-confirmation into one question so you're not interrupting twice for what's really one decision:

> "This sounds like a new [idea/feature/project] — run the spec-gap process before any planning or code? Proposed folder: `specs/<slug>/`."
> Options: **Yes, start** / **No, just discussing** / **Different slug**

Render this as a structured question (not free text) so the answer is unambiguous. If the answer is "No," stop completely — don't create any files, don't proceed with a lighter-weight version of the interview. A "no" here means the user wanted to think out loud, not commit.

## Step 3 — Run the three layers in order

Once confirmed, invoke each layer skill in sequence. Do not start layer N+1 until layer N has produced its file and logged an explicit human sign-off in its decisions log.

1. **project-spec** — produces `specs/<slug>/spec.md` (Goal, Scope, Non-goals, Constraints)
2. **project-verify** — produces `specs/<slug>/verify.md` (Evaluation Criteria, External Signal), depends on spec.md
3. **project-environment** — produces `specs/<slug>/environment.md` (Environment Gaps, Hook Drafts), depends on spec.md and verify.md

Each layer skill is self-contained and can also be invoked directly by name outside this orchestration (see each skill's own standalone-invocation handling). Your job here is purely sequencing and refusing to skip ahead.

If a layer skill reports that its own critic or dependency (codex-plugin-cc, steward maintainers) is unavailable, let that layer skill's own fallback logic handle it — don't intervene or make that call for it.

## Step 4 — Wrap-up

Once all three files exist and each shows `status: complete` in its own frontmatter, report back to the user:

- The location of all three files and their decision logs
- A one-line summary of what's now known: the goal, how success will be checked, and what environment gaps (if any) were flagged or explicitly accepted as risk
- That the idea is now ready for planning/implementation — this skill's job ends here; it does not write code or a build plan itself

If any layer's status is not `complete` (e.g. the user paused partway through, or explicitly accepted an open risk rather than resolving it), say so plainly rather than reporting the process as finished.

## What this skill must never do

- Never draft Goal/Scope/Criteria/Environment content itself — that's each layer's job, not the orchestrator's.
- Never treat silence, a topic change, or an ambiguous reply as approval at any gate.
- Never start layer N+1 while layer N's file is missing or its status isn't `complete` (or explicitly accepted-with-risk, for project-environment specifically).
