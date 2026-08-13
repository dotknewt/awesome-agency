# Local Changes — intentional divergence from upstream

This bundle is vendored from [obra/superpowers](https://github.com/obra/superpowers)
(forked at upstream **v6.2.0**), but carries deliberate local modifications.
When re-syncing from upstream, preserve or re-apply the changes below.
`RELEASE-NOTES.md` stays pinned to upstream — local changes are recorded here,
never there.

## v6.2.4 (2026-08-13) — Copilot model-selection safe degradation

`subagent-driven-development`'s Model Selection section told the dispatching agent to
"always specify the model explicitly" using an abstract tier, which is safe on Claude
Code's Task tool (alias or pinned full ID) but not on every dispatch tool: GitHub
Copilot's `runSubagent` (Copilot Chat in VS Code) needs an exact `"Model Name
(Vendor)"` string with no alias support and no in-skill way to enumerate installed
models, so following the guidance literally there produced a hard "model not found"
dispatch failure instead of a graceful fallback. Model Selection now distinguishes
choosing a tier (host-independent, unchanged) from expressing that tier as a
dispatch-tool value (host-dependent): specify a model only when the value is known to
be valid for the active dispatch tool, otherwise omit the `model:` line entirely
(never leave it present with an empty value) and accept the session default; retry a
dispatch without `model` if it was rejected specifically for its model value, before
treating the task as blocked.

Diverged/added files:

- `skills/subagent-driven-development/SKILL.md` — Model Selection section reworded
  per above; points to the new reference file below for Copilot CLI ids.
- `skills/subagent-driven-development/references/copilot-model-ids.md` — new file: a
  dated, hand-maintained snapshot of Copilot CLI's `--model` short-id catalog
  (anthropic/openai ids), scoped explicitly to Copilot CLI's short-id format (not
  Copilot Chat's `"Model Name (Vendor)"` format) and treated as best-effort, not a
  live query.
- `skills/subagent-driven-development/implementer-prompt.md`,
  `re-review-prompt.md`, `task-reviewer-prompt.md` — `[MODEL — REQUIRED...]`
  placeholder reworded to state that omitting the model means deleting the entire
  `model:` line, not leaving it with an empty value.

## v6.2.3 (2026-08-08) — optional cross-model second opinion

The three "otherwise passed" gates — code review's merge verdict, the plan
reviewer's approval, and subagent-driven-development's whole-branch final
review — previously had no mechanism for a second, differently-modeled pass:
a reviewer's blind spots are often shared by a re-review from the same model
at the same or higher capability. For high-stakes cases (architecture-changing
diffs, security-sensitive code, expensive-to-reverse plan decisions, a
multi-phase initiative closing out) it's now suggested — never mandatory — to
dispatch one additional pass on a different, cheap/fast, low-reasoning-effort
model as a second pair of eyes before finishing, using the same
review-file/contract conventions already in place.

Diverged/added files:

- `skills/requesting-code-review/SKILL.md` — new "Optional: Second Opinion
  Before Final Acceptance" section after the act-on-feedback guidance.
- `skills/writing-plans/SKILL.md` — new "Optional: Second Opinion Before
  Final Acceptance" section after Self-Review, before Execution Handoff.
- `skills/subagent-driven-development/SKILL.md` — new "Optional: Second
  Opinion Before Final Acceptance" subsection in Final Review, before Finish.

## v6.2.2 (2026-08-08) — multi-phase resume protocol

An initiative split into a sequence of phase plans had no resume record above the
single plan level: `subagent-driven-development` deleted a plan's workspace on a clean
final review, so a session disrupted between phases (compaction, a crash, a closed
terminal) had nothing but git commits to reconstruct which phase the initiative was on.
Design: `docs/superpowers/specs/2026-08-08-multi-phase-resume-protocol-design.md`.

Diverged/added files:

- `skills/subagent-driven-development/SKILL.md` — phase-suffixed ledger identity line
  (`... (phase N of M: <initiative-slug>)`); Final Review appends a
  `Final review: clean`/`<K> parked` ledger line; Finish's workspace deletion is
  conditional on not being a phase with phases remaining; process diagram and example
  transcript updated; new rationalization row and cross-reference to the new skill.
- `skills/resuming-multi-phase-plans/SKILL.md` — new skill: resume protocol that reads
  phase ledgers across an initiative to determine what to resume, context-clearing
  guidance between phases, and initiative-level workspace cleanup once every phase's
  ledger reports its final review.

## v6.2.1 (2026-08-07) — subagent report contracts

Every dispatched subagent now writes its full output to a file and returns a
short contract (≤15 lines: verdicts, severity counts, one-liners for
Critical/Important findings, file path). Previously only the SDD implementer
followed this pattern; every reviewer returned its full report as its final
message, straight into the orchestrator's context, and the SDD fix loop
re-pasted findings verbatim into fix and re-review dispatches. Design:
`docs/superpowers/specs/2026-08-07-subagent-report-contracts-design.md`.

Diverged files:

- `skills/subagent-driven-development/task-reviewer-prompt.md` — new
  `[REVIEW_FILE]` placeholder; full review to file; final message is the
  contract.
- `skills/subagent-driven-development/re-review-prompt.md` — `[FINDINGS]`
  (verbatim copy) replaced by `[FINDINGS_FILE]` + `[FINDING_IDS]`; new
  `[REVIEW_FILE]`; contract output.
- `skills/subagent-driven-development/SKILL.md` — controller allocates
  review-file paths; fix dispatches pass paths, never pasted findings;
  adjudication from contract one-liners; example transcript updated.
- `skills/subagent-driven-development/implementer-prompt.md` — fix rounds
  arrive as one-liners + review-file path (After Review Findings section).
- `skills/requesting-code-review/code-reviewer.md` — `[REVIEW_FILE]` with
  mktemp fallback; contract output; contract example added.
- `skills/requesting-code-review/SKILL.md` — placeholder list, act-on-feedback
  guidance, example transcript, and rationalization table updated.
- `skills/brainstorming/spec-document-reviewer-prompt.md` — review to file,
  contract output.
- `skills/writing-plans/plan-document-reviewer-prompt.md` — review to file,
  contract output.
- `skills/dispatching-parallel-agents/SKILL.md` — per-agent report file +
  summary contract required in prompt structure and examples.
