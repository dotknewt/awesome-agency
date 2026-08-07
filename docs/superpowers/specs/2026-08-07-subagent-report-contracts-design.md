# Subagent Report Contracts — Design

**Date:** 2026-08-07
**Status:** Approved
**Scope:** `plugins/superpowers/` (vendored bundle, treated as intentional soft fork)

## Problem

Superpowers' own guidance is that subagents hand artifacts over as files and return a
short contract to the orchestrator. Only the SDD **implementer** prompt enforces this
(full report → `[REPORT_FILE]`, ≤15-line status contract back). Every **reviewer**
prompt does the opposite — the full report is the subagent's final message, landing
verbatim in the orchestrator's context:

- `skills/subagent-driven-development/task-reviewer-prompt.md` — "Your final message is the report itself"
- `skills/subagent-driven-development/re-review-prompt.md` — same
- `skills/requesting-code-review/code-reviewer.md` — Output Format is the full in-message review
- `skills/brainstorming/spec-document-reviewer-prompt.md`, `skills/writing-plans/plan-document-reviewer-prompt.md` — compact, but still fully in-message
- `skills/dispatching-parallel-agents/SKILL.md` — "return summary" guidance, no file+contract rule

The SDD fix loop compounds the leak: findings are pasted verbatim into fix dispatches
and into the re-review's `[FINDINGS]` placeholder, so each finding transits the
controller's context at least three times.

## Design

### The contract pattern (uniform)

Every dispatched subagent writes its full output to a file the controller names (or a
`mktemp` fallback when standalone) and returns a short contract — ≤15 lines, styled
after the implementer's existing contract so all contracts read alike.

Reviewer contract:

- **Verdicts:** spec compliance (✅/❌/⚠️) + task quality (Approved | Needs fixes) —
  or a single **Status** for document reviewers
- **Counts:** findings per severity (Critical/Important/Minor)
- **One line per Critical/Important finding:** `file:line — gist`
- **Review-file path**

The one-liners exist so the controller can adjudicate (severity calibration, plan
conflicts, fix-round routing) without opening the file. The controller opens the review
file only when a ruling genuinely needs the full detail.

### Findings travel by path

- **Fix dispatch (SDD):** carries the brief path, the implementer's report-file path,
  and the review-file path. The implementer reads the findings itself. No findings text
  is pasted into the dispatch.
- **Re-review dispatch:** `[FINDINGS]` (verbatim copy) becomes `[FINDINGS_FILE]` (the
  prior review's file) plus the list of finding identifiers under re-check. The
  re-reviewer reads the prior review itself.
- **Re-review output:** same file + contract pattern; each re-review appends to or
  writes a new review file, path returned in the contract.

### Per-file changes

1. **`task-reviewer-prompt.md`** — new `[REVIEW_FILE]` placeholder (controller
   allocates in the plan's sdd workspace, like `[DIFF_FILE]`); full review written
   there; final message replaced by the contract above.
2. **`re-review-prompt.md`** — `[FINDINGS_FILE]` replaces `[FINDINGS]`; same file +
   contract output.
3. **`subagent-driven-development/SKILL.md`** — controller allocates review-file
   paths; fix dispatches pass paths only; adjudication from contract one-liners;
   workspace cleanup covers review files.
4. **`requesting-code-review/code-reviewer.md`** — `[REVIEW_FILE]` with mktemp
   fallback; file + contract output.
5. **`requesting-code-review/SKILL.md`** — narrative ("only the findings come back to
   you") and example transcript updated to the contract pattern.
6. **`spec-document-reviewer-prompt.md`**, **`plan-document-reviewer-prompt.md`** —
   scaled-down: full review to file, contract = Status + issue one-liners + path.
7. **`dispatching-parallel-agents/SKILL.md`** — prompt-structure rule: each parallel
   agent writes detailed output to a per-agent file and returns a short summary
   contract; integration steps reference the files for detail.

### Fork bookkeeping

`plugins/superpowers/` is vendored from obra/superpowers (`.vendored` marker). This
change makes it an intentional soft fork:

- New `plugins/superpowers/LOCAL-CHANGES.md` records the upstream version forked from
  (6.2.0) and the per-file rationale, so a future re-sync knows what to preserve or
  re-apply.
- `plugin.json` version bumps `6.2.0 → 6.2.1` so cached installs re-fetch.
- `RELEASE-NOTES.md` stays pinned to upstream — no local entries (per AGENTS.md).
- `.vendored` marker stays (release-notes discipline exemption still applies).

## Error handling

- Reviewer cannot write the file (permissions, missing dir): report the failure in the
  final message and include the full review inline as fallback — a leaked report beats
  a lost one.
- Controller receives a contract without a path: treat as a malformed report; re-ask
  the reviewer once, then fall back to inline.

## Testing

No automated test surface exists for prompt prose. Validation is:
- repo CI scripts locally (marketplace drift, host-compat, plugin-root-refs, skill
  frontmatter, release-notes audit with the `.vendored` exemption),
- a consistency read-through: all contracts share the implementer contract's style,
  no remaining "final message is the report" text, no verbatim-findings plumbing left
  in SKILL.md.

## Out of scope

- Upstream PR to obra/superpowers (user chose soft fork; revisit at next re-sync).
- Any change to the implementer prompt beyond keeping it the canonical contract style.
