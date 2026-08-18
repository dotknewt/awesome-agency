# Shared checkpoint protocol

This protocol is identical across project-spec, project-verify, and project-environment. Read it once; apply it at every checkpoint in this skill.

## 1. The itemized claim test (gap detection)

Never judge a draft as "good enough" from a general impression. Instead, pull every discrete claim in the drafted section out as its own line item — each requirement, each constraint, each goal statement, each success criterion — and test it against one fixed rule:

> Could someone point to a concrete outcome and say "this failed" or "this passed"?

Mark each line item:
- `✓ measurable — <what that outcome would look like>`
- `✗ gap — <specifically what's missing: a number, a trigger condition, an owner, a boundary>`

Show the **full list** at the checkpoint, not just the failures. This is the actual trust mechanism: the human isn't trusting that you silently checked and found nothing — they're independently re-checking a visible, itemized list against the same rule. An omitted claim is a visible hole, not a silent pass, because the list has to account for every sentence in the draft.

Bad example (fails the test): "make the report look good"
Good example (passes the test): "the report must have 3 sections, each ending with a recommendation"

## 2. The load-bearing test

Some decisions deserve a mandatory checkpoint even when every claim in them passed the measurability test cleanly — because the decision quietly constrains everything downstream. Tag a decision `⚠ load-bearing` if the answer to any of these three questions is yes:

1. **Dependency** — would reversing this decision later force rework or invalidation of a section that's already been signed off?
2. **Reversibility** — once implementation starts, is this expensive or effectively impossible to undo (auth strategy, storage format, public API shape, irreversible side effects)?
3. **Precedent** — is this the kind of decision other future specs would likely copy or inherit without re-examining it (a naming convention, a default trigger behavior, a security posture)?

A `⚠ load-bearing` tag forces a checkpoint regardless of the ✓/✗ verdict.

## 3. When to stop for a checkpoint

Checkpoints are adaptive, not fixed to section boundaries. Keep drafting continuously; stop and open a checkpoint the moment the itemized claim list for what you've just drafted contains either:
- any `✗ gap`, or
- any `⚠ load-bearing` tag

If a section's claims are all `✓` and none are load-bearing, no checkpoint is needed — move on to the next section without interrupting.

## 4. Sign-off order at every checkpoint

1. **Agent self-check** — state explicitly why you believe the draft meets criteria (or exactly what gap/load-bearing item you're bringing to the human).
2. **Critic pass (conditional)** — run this step only if the current draft has 3+ sections, 300+ words, OR contains a `⚠ load-bearing` tag. Invoke the `codex-plugin-cc` plugin, asking it to adversarially review the draft for gaps, inconsistencies, or unstated assumptions. If `codex-plugin-cc` is not installed or fails to invoke, stop and ask the human explicitly: install it, fall back to an independent adversarial subagent (a fresh agent, no memory of the drafting conversation, told to try to refute the draft), or skip the critic pass for this checkpoint. Never silently substitute or silently skip.
3. **Human approval** — render a structured question (AskUserQuestion or equivalent) with the itemized list and, if run, the critic's findings. Never treat silence, a topic change, or free-text ambiguity as approval — require an explicit choice.

Below the critic threshold, skip straight from self-check to human approval.

## 5. Logging every checkpoint

Every checkpoint — regardless of whether it needed a critic pass — gets one structured entry appended to this layer's `.decisions.log` file:

```yaml
- checkpoint_id: <sequential number>
  layer: spec | verify | environment
  timestamp: <ISO 8601, from `date -Iseconds`>
  claims:
    - text: "<claim text>"
      verdict: "✓" | "✗"
      load_bearing: true | false
      justification: "<why>"
  agent_self_check: "<summary>"
  critic:
    invoked: true | false
    tool: "codex-plugin-cc" | "subagent-fallback" | null
    verdict: "<summary or null>"
  human_response: "<the exact recorded answer>"
```

Nothing here is optional formatting — the log is the audit trail that lets anyone verify later that judgment was actually applied, not hand-waved.
