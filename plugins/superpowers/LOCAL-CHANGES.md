# Local Changes — intentional divergence from upstream

This bundle is vendored from [obra/superpowers](https://github.com/obra/superpowers)
(forked at upstream **v6.2.0**), but carries deliberate local modifications.
When re-syncing from upstream, preserve or re-apply the changes below.
`RELEASE-NOTES.md` stays pinned to upstream — local changes are recorded here,
never there.

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
