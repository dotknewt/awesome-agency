---
name: agent-model-assignment
description: >
  Use when deciding which model an agent or subagent should run on, or reviewing an
  existing assignment. Triggers on "which model should this agent use", "assign a
  model", "is haiku enough for this agent", "should this be opus", "model frontmatter",
  "agent is too slow", "agent is too expensive", "subagent keeps losing track",
  "cut agent costs", or when writing a new agent's frontmatter. Applies a
  constraints-first decision procedure and explains the cost, speed, and reliability
  tradeoffs behind each tier.
---

# Assigning a model to an agent

An agent's `model` field takes a full model ID (e.g. `claude-opus-5`,
`claude-haiku-4-5`) — a tier alias (`haiku`, `sonnet`, `opus`, `fable`) or `inherit`
are **not** valid values here. **Always set it explicitly to a full ID.** Omitting the
field, or leaving it as a bare alias/`inherit`, cannot be told apart from an oversight,
and the next reader has no idea whether the pin was deliberate.

**Always pin a full ID; never write a bare alias or `inherit`.** Anthropic's dateless
model IDs are pinned snapshots, not evergreen pointers, so writing one freezes the
agent on that snapshot until someone revisits it — that staleness is a cost this
convention accepts deliberately, in exchange for every agent's behavior being
reproducible and reviewable from the file alone, with no dependency on what a bare
alias happens to resolve to on a given day or what the calling session's model is.
Treat a pinned ID the same way you'd treat a pinned dependency version: it needs
periodic review as models are deprecated, and that review is a known, recurring cost,
not a one-time decision.

## The ladder

Tiers below are a reasoning aid for picking *which* model to pin, not a set of valid
`model:` values. Prices per million tokens, verified 2026-08-06. Throughput is
third-party estimate: trust the ratios, not the absolute numbers. Re-check pricing at
`platform.claude.com/docs/en/about-claude/pricing` before making a cost argument, and
re-check the current full ID for each tier before pinning — the ones below drift the
same way the prices do.

| Tier | Full ID (verify before pinning) | Input / output | vs Haiku | Speed | Context | Knowledge cutoff |
| --- | --- | --- | --- | --- | --- | --- |
| Haiku-class | `claude-haiku-4-5` | $1 / $5 | 1× | fastest (~2–3× Sonnet) | **200K** | **Feb 2025** |
| Sonnet-class | `claude-sonnet-5` | $3 / $15 | 3× | ~2–3× Opus | 1M | Jan 2026 |
| Opus-class | `claude-opus-5` | $5 / $25 | 5× | slower | 1M | May 2026 |
| Fable-class | `claude-fable-5` | $10 / $50 | 10× | slowest | 1M | Jan 2026 |

The whole ladder spans 10×, which is narrower than most people assume. **Token volume
usually dominates tier choice**: an agent that reads half a repo on `haiku` can cost
more than a tightly scoped one on `opus`. Scope the agent's context before optimizing
its tier — restricting `tools` and narrowing its brief buys more than downgrading it.

## Decision procedure

Work these in order. The first two are hard constraints that disqualify a tier
outright; only then does task shape matter.

### 1. Does it exceed Haiku's hard limits?

Haiku caps at **200K tokens** of context (~150K words) and its knowledge ends
**Feb 2025**. Every other tier has a 1M window and a 2026 cutoff. So a Haiku-class ID
is off the table — regardless of how simple the task is — for an agent that:

- sweeps or greps a large repository, or reads many files into one context
- processes long documents, transcripts, or logs
- needs to know about library versions, APIs, or events after early 2025

This rules out more agents than the reasoning criterion does, and it is the failure
people miss, because a context overflow looks like a bad answer, not an error.

### 2. How long is its tool-call loop?

Reliability degrades non-linearly with chain length, and it degrades earliest on the
cheap tier:

| Loop length | Safe floor |
| --- | --- |
| Single-digit steps | Haiku-class |
| ~10–20 steps | Sonnet-class |
| 20+ steps of autonomous work | Opus-class |

Past roughly 7–10 steps, Haiku-class models start truncating loops, skipping steps,
and losing state rather than simply answering less well.

### 3. What shape is the work?

| If the agent's job is… | Use | Because |
| --- | --- | --- |
| Mechanical and bounded — git plumbing, filing an issue, updating a state file, syntactic checks, short structured extraction | Haiku-class | Procedural work with a checkable answer, 3–5× cheaper and 2–3× faster, and these agents run often. |
| A long or unbounded tool-use loop — driving a CLI, iterating over many files, multi-step orchestration | Sonnet-class | The production default for agentic loops, and empirically better than Opus at them: Sonnet 5 leads Opus 5 on Terminal-Bench 2.1 (80.4% vs 74.6%) because throughput compounds over a long chain. |
| Generating a whole artifact from an ambiguous brief — design, architecture, planning, writing a config for an unfamiliar system | Opus-class | Quality is bounded by reasoning and a weak result is expensive to detect. Opus 5 leads SWE-bench Verified 96.0% vs Sonnet 5's 85.2%. |
| Adversarially checking work a cheaper session may have produced — verification, security review, subtle bug hunting | Opus-class | A verifier pinned to the same tier that produced the error it's hunting shares its blind spots. |
| Behaviorally dependent on one specific model — a persona whose voice *is* that model | that model's exact full ID | The agent *is* that model's behavior; any other pin silently replaces it. |
| Judgment work whose quality should track whatever the caller is already paying for | not expressible with a required pin — see below | A full-ID-only convention has no equivalent to `inherit`; state the actual intent instead. |

An agent that genuinely wants "run at the caller's tier" has no direct equivalent once
`inherit` is banned. Don't work around this by pinning a bare alias anyway. Instead,
pin the highest tier the work could plausibly need (usually Opus-class, since this row
only applies to judgment work) and record in the description that the tier is a floor,
not a fixed cost — a caller running an expensive session was going to spend more than
this agent's pin regardless. If the agent is genuinely meant to inherit the caller's
exact model as a persona-consistency requirement, that is the "behaviorally dependent
on one specific model" row above, not this one.

## Tradeoffs and traps

- **Cheap fails differently, not just worse.** Dropping a tier does not gently
  degrade output; it changes the failure mode from "slightly worse judgment" to
  "stopped early, skipped a step, lost the thread". Use a Haiku-class pin where a bad
  result would be *obvious*, not merely tolerable.
- **More expensive is not uniformly better.** Sonnet beats Opus at long CLI/tool
  loops. Fable costs 2× Opus while trailing it on most coding benchmarks. Reaching
  for the top of the ladder by default is slower *and* worse for agentic work.
- **Fable silently downgrades security-adjacent prompts.** Its internal classifier
  routes flagged queries to an older Opus. Never put a security or vulnerability
  agent on a Fable-class pin: less capability than Opus-class, twice the price, no
  signal.
- **Latency is a UX cost, not just a bill.** Across ~20 sequential tool calls,
  time-to-first-token alone spans roughly 5s on Haiku, 10s on Sonnet, 30s on Fable.
  For an agent a human waits on, that gap is felt.
- **A stale pin is a silent regression.** A full ID that was the right tier when
  chosen doesn't stay current — it can end up deprecated, or simply behind newer
  models in its own tier, without the file changing at all. Treat a pinned model ID
  like a pinned dependency version: revisit it periodically, not just when writing
  the agent.
- **Reflexive Haiku-class for anything that "looks simple".** Drift and consistency
  checks read as mechanical but often are not: deciding whether documented *intent*
  still holds is judgment work. Split by task, not by agent family — checking that a
  command still exists is syntactic; checking that a doc still describes reality is
  not.

## Reasoning effort

Some models expose an adjustable reasoning-effort or thinking-budget control
alongside the model choice itself. Claude Code's agent frontmatter has no dedicated
field for this — there is no schema change here — but where the pinned model (or the
host running it) does support tuning effort, state the intended level in the same
place you record the model choice (the `description`, or a body comment), matching it
to the task shape from the decision procedure above: mechanical/bounded work wants the
lowest effort that reliably produces a checkable answer, long autonomous loops want a
middle setting, and generating an artifact from an ambiguous brief or adversarial
review wants the highest effort available. Leaving effort unstated when the model
supports choosing it has the same "can't tell deliberate from oversight" problem this
skill exists to avoid for `model` itself.

## Record the reason

State *why* the tier was chosen where a reviewer will see it: in the agent's
`description` when callers benefit from knowing ("Runs on a cheap model so the main
session does not burn tokens on git plumbing"), or in a comment in the body when it is
purely internal. Do not put an HTML comment above the frontmatter — the `---` block
must start at line 1 or the file will not parse as an agent.

Do not keep a central list of which agent uses which model. Such lists drift from the
files within a few changes, and a stale list reads as normative.

## Evidence quality

Pricing, context windows, and cutoffs are from Anthropic's published docs. SWE-bench
and Terminal-Bench figures are from public leaderboards and agree across sources.
Throughput figures are community estimates with no official numbers published. The
security and creative-writing recommendations are extrapolated from general capability
scaling — **no tier-specific benchmark exists for either**, so treat those two rows as
reasoned defaults rather than measured results.
