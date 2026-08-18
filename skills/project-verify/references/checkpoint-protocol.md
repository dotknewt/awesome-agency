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

Re-presenting a section the human already approved is the one exception to showing everything: list every new or changed claim in full, and collapse the untouched approved ones to a count plus the checkpoint that carries them ("9 previously approved claims unchanged — checkpoint 3"). The full list is the trust mechanism for claims currently under review; replaying approved ones verbatim at every later checkpoint is noise, and noise is how a real gap gets skimmed past.

## 2. Attribution: every claim carries its source

You write most of the words in this interview — the questions, the option labels, the drafted claims, the summaries of what you heard. That creates a specific failure this rule exists to block: a claim **you** authored is offered to the human as an option, they pick it, and from then on you cite it back to them as something *they* reported. Nothing new was ever learned; your own guess acquired a human's name on it.

So every line item in the itemized list carries a source tag alongside its ✓/✗ verdict:

- `@user` — the human stated it in their own words, unprompted by a label you wrote. A fact they confirmed by restating it themselves is `@user`; a fact they confirmed by agreeing to *your* paraphrase ("so what you're saying is X?" → "yes") is `@approved`, because the wording — and any detail you added while paraphrasing — is still yours. When the difference is load-bearing, ask them to say it back in their own words rather than guessing which tag applies
- `@approved` — you drafted or proposed it; the human picked or confirmed your wording
- `@inferred` — you derived it from something else and nobody has confirmed it yet
- `@observed — <path, command, or output>` — you checked something concrete; cite what

Rules that follow from the tags:

1. **Choosing an option you wrote is approval of your wording, not testimony.** It tells you the phrasing is acceptable; it does not establish that any fact asserted inside the label is true, and it never upgrades `@approved` to `@user`.
2. **Never say "you said", "as you reported", "per your description", "you told me"** — or write the same attribution into a spec file or log — for anything not tagged `@user`. For `@approved` say "you approved my phrasing of X"; for `@inferred` say "I inferred X from Y — is that right?"; for `@observed` name the file or command.
3. **Don't smuggle unverified facts into option labels.** If you need a fact confirmed, ask about the fact directly ("is X actually happening?") instead of embedding it in a label attached to a choice about something else. When a label has to carry an unconfirmed premise, phrase it as a condition — "if X is happening, then …" — so picking it doesn't silently ratify X.
4. **Inference is fine; laundering it isn't.** An `@inferred` claim can stay in the draft, but it stays tagged, and it cannot be used as the grounding for a downstream claim until it's been confirmed as its own line item at a checkpoint. Once confirmed it becomes `@approved` — or `@user` if the human restated it in their own words. Confirmation alone never promotes a claim to `@user`; that tag is about who authored the words, and that fact doesn't change retroactively.
5. **Carry the tag into the written files.** In `spec.md`, `verify.md`, and `environment.md`, each claim ends with its source tag — "the signup form drops to 3 fields `@approved`" — and the prose around it stays flat. Flat means no narrated attribution: never "the user reports the form is too long," which is the same laundering one layer up. The `.decisions.log` holds the detail (exact wording, who authored the option, what was checked); the file holds the one-token version, because the file is what anyone actually reads later. A criterion that was your guess and a criterion that was the user's requirement fail very differently, and nobody reconstructs that by diffing a spec against its log.

If, mid-draft, you catch yourself about to write a claim whose only source is a menu you wrote earlier, that is a `✗ gap` and a checkpoint — not a claim.

## 3. The load-bearing test

Some decisions deserve a mandatory checkpoint even when every claim in them passed the measurability test cleanly — because the decision quietly constrains everything downstream. Tag a decision `⚠ load-bearing` if the answer to any of these three questions is yes:

1. **Dependency** — would reversing this decision later force rework or invalidation of a section that's already been signed off?
2. **Reversibility** — once implementation starts, is this expensive or effectively impossible to undo (auth strategy, storage format, public API shape, irreversible side effects)?
3. **Precedent** — is this the kind of decision other future specs would likely copy or inherit without re-examining it (a naming convention, a default trigger behavior, a security posture)?

A `⚠ load-bearing` tag forces a checkpoint regardless of the ✓/✗ verdict.

## 4. When to stop for a checkpoint

Checkpoints are adaptive, not fixed to section boundaries. Keep drafting continuously; stop and open a checkpoint the moment the itemized claim list for what you've just drafted contains either:
- any `✗ gap`, or
- any `⚠ load-bearing` tag, or
- any `@inferred` claim that a later claim depends on (section 2, rule 4)

If a section's claims are all `✓`, none are load-bearing, and no unconfirmed inference is holding anything up, no checkpoint is needed — move on to the next section without interrupting.

## 5. Sign-off order at every checkpoint

1. **Agent self-check** — state explicitly why you believe the draft meets criteria (or exactly what gap/load-bearing item you're bringing to the human), and read the source tags back: name every `@inferred` claim as yours, and every `@approved` claim as your wording they signed rather than something they reported. A claim whose only source is an option label you wrote earlier gets said out loud as exactly that.
2. **Critic pass (conditional)** — run this step when the checkpoint carries a `⚠ load-bearing` tag, or when it is the layer's final checkpoint (the one that would set `status: complete`). Ordinary mid-draft gap checkpoints don't get one: a threshold that fires nearly every time teaches everyone to skim the critic, which costs more than it catches.

   **Hand the critic its inputs, not just the prose.** Give it the drafted section, the tagged itemized list, and the `.decisions.log` entries behind any claim you want traced. A critic that receives only the draft can check measurability and internal consistency — nothing more. It cannot tell `@user` from `@approved`, because that difference does not exist in the text, and the sanctioned subagent fallback below has no memory of the conversation to recover it from. If the critic can't be given the tagged list, say so at the checkpoint and scope its remit to measurability rather than reporting an attribution review that never happened.

   Ask it to adversarially review for gaps, inconsistencies, unstated assumptions, and — when it has the tagged list — misattributed claims: anything presented as the human's that traces back to an option label you wrote.

   Invoke the `codex-plugin-cc` plugin for this. If it is not installed or fails to invoke, stop and ask the human explicitly: install it, fall back to an independent adversarial subagent (a fresh agent, no memory of the drafting conversation, told to try to refute the draft), or skip the critic pass. Record that answer once as `critic.fallback_choice` and reuse it for every later critic pass in this slug — re-asking the same question at each checkpoint is how a gate becomes a formality. Re-open it only if the human raises it or `codex-plugin-cc` becomes available. Never silently substitute or silently skip.
3. **Human approval** — render a structured question (AskUserQuestion or equivalent) with the itemized list, its source tags, and, if run, the critic's findings. Never treat silence, a topic change, or free-text ambiguity as approval — require an explicit choice.

Below the critic threshold, skip straight from self-check to human approval.

## 6. Logging every checkpoint

Every checkpoint — regardless of whether it needed a critic pass — gets one structured entry appended to this layer's `.decisions.log` file:

```yaml
- checkpoint_id: <sequential number>
  layer: spec | verify | environment
  timestamp: <ISO 8601, from `date -Iseconds`>
  claims:
    - text: "<claim text>"
      verdict: "✓" | "✗"
      source: "@user" | "@approved" | "@inferred" | "@observed"
      source_detail: "<the human's own words, the option label you wrote, or the path/command checked>"
      load_bearing: true | false
      justification: "<why>"
  agent_self_check: "<summary>"
  critic:
    invoked: true | false
    tool: "codex-plugin-cc" | "subagent-fallback" | null
    inputs: [draft-section, tagged-claim-list, decisions-log]  # what it actually received
    fallback_choice: install | subagent | skip | null   # decided once per slug, then reused
    verdict: "<summary or null>"
  human_response:
    verbatim: "<the exact recorded answer, or the exact label chosen>"
    form: free-text | chose-option
    options_authored_by: agent | human   # only when form: chose-option — omit for free-text
```

Nothing here is optional formatting — the log is the audit trail that lets anyone verify later that judgment was actually applied, not hand-waved, and that every claim in the spec is traceable to whoever actually made it. `source` plus `human_response.form` is what makes a later reader able to tell an answer the human gave from a menu item they clicked, and `critic.inputs` is what makes a critic verdict readable as evidence rather than a rubber stamp — a critic that never saw the tagged list did not check attribution, whatever its summary says.
