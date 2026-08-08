# Multi-Phase Resume Protocol — Design

**Date:** 2026-08-08
**Status:** Approved
**Scope:** `plugins/superpowers/` (vendored bundle, treated as intentional soft fork)

## Problem

An initiative too large for one SDD plan is split into a sequence of phase plans
(`docs/superpowers/plans/<initiative>-phase-N-of-M.md`), each executed with
`subagent-driven-development` in its own turn. Today the skill treats every plan as
standalone: on a clean final review it deletes the plan's workspace
(`.superpowers/sdd/<plan-basename>/`) — "the git history is the record now"
(SKILL.md, Finish). That destroys the one artifact that says *which phase the
initiative is on* before the next phase's controller has read anything: the ledger. Git
log carries commits, not phase progress — reconstructing "phases 1-2 done, phase 3
mid-loop" from commit messages alone is exactly the failure the ledger exists to
prevent for tasks within one plan; nothing today extends that guarantee across phases.

If a session ends unexpectedly between phases — compaction, a crashed harness, a human
closing the terminal — the next session has no resume record for the initiative as a
whole, only for whichever single phase happens to still have its workspace.

## Design

### Phase-scoped ledger identity

A phase plan's ledger identity line gains an optional phase suffix:

```
# SDD ledger — plan: <plan file path> (phase N of M: <initiative-slug>)
```

Single-plan (non-phased) work keeps the existing unsuffixed line — no format change
required for the common case.

### Final-review ledger line

`subagent-driven-development`'s Final Review step now appends a durable line to the
ledger, mirroring the existing per-task completion lines:

- `Final review: clean`
- `Final review: <K> parked`

Previously the final review's outcome lived only in the reviewer's transient contract
message — never written to the ledger. This line is what a resume scan reads to tell
"phase complete" apart from "mid-review."

### Conditional workspace deletion

The Finish step's unconditional `rm -rf <workspace>` becomes conditional: delete only
when this plan is not one phase of a multi-phase initiative, or is the initiative's
last phase and every sibling phase's workspace has already reported
`Final review: clean`/`<K> parked`. Otherwise, leave the workspace in place — a clean
final review no longer implies deletion. `superpowers:resuming-multi-phase-plans` owns
the actual delete-when-every-phase-is-done step so the rule lives in one place.

### New skill: `resuming-multi-phase-plans`

A sibling skill to `subagent-driven-development`, invoked when an initiative spans more
than one phase plan:

- **Resume protocol:** at the start of any session working on a phase initiative
  (fresh start, after `/clear`, after compaction, after a crash), glob
  `.superpowers/sdd/*/progress.md`, filter by initiative-slug in the identity line,
  order by phase N, and classify each phase from its ledger using the same states
  `subagent-driven-development` already uses within one plan (no ledger → not started;
  last line is a fix round → resume that loop; all tasks complete, no final-review line
  → resume at Final Review; final-review line present → phase complete). This makes the
  set of phase ledgers the resume record — no separate manifest file, no reliance on
  conversation memory.
- **Context clearing between phases:** once a phase's ledger carries its
  `Final review: clean`/`<K> parked` line, that line plus git history is sufficient to
  resume — nothing forward-relevant lives only in conversation. The skill instructs
  proactively clearing/compacting context (or starting a new session) before dispatching
  the next phase, narrated to the human partner, instead of letting context accumulate
  across the whole initiative.
- **Finish:** once every phase's ledger shows a final-review line, the initiative is
  done — this skill deletes every phase's workspace under `.superpowers/sdd/`, the same
  cleanup `subagent-driven-development` performs for a single plan.

### Per-file changes

1. **`subagent-driven-development/SKILL.md`** — phase-suffixed ledger identity format
   (Setup); final-review ledger line (Final Review); Finish step's deletion made
   conditional, pointing at the new skill; process diagram's terminal node split into
   "record final review" and a deletion decision; cross-reference to
   `resuming-multi-phase-plans` in "When to Use".
2. **`resuming-multi-phase-plans/SKILL.md`** (new) — resume protocol, context-clearing
   guidance, and initiative-level Finish/cleanup, as above.

### Fork bookkeeping

- `plugins/superpowers/LOCAL-CHANGES.md` gains an entry recording this design and the
  diverged files, per the bundle's existing soft-fork convention.
- `plugin.json` version bumps to keep cached installs re-fetching.
- `RELEASE-NOTES.md` stays pinned to upstream — no local entries.
- New skill ships as a real file under `plugins/superpowers/skills/` (no pool symlink,
  consistent with the rest of the vendored bundle) and gets no marketplace micro-entry,
  matching every other superpowers skill.

## Error handling

- A phase ledger with a phase suffix that does not match any known plan file in the
  initiative: treat as a stray ledger (existing rule for mismatched ledgers already
  covers this) — leave it in place, do not delete or reuse it.
- A ledger missing the final-review line but with every task complete: resume at Final
  Review for that phase rather than assuming completion — the line's absence is
  authoritative.

## Testing

No automated test surface exists for prompt prose. Validation is the repo's CI scripts
locally (marketplace drift — none expected since the bundle takes no micro-entries,
host-compat, plugin-root-refs, skill frontmatter, release-notes audit under the
`.vendored` exemption) plus a consistency read-through against
`subagent-driven-development`'s existing ledger and workspace conventions.

## Out of scope

- Upstream PR to obra/superpowers (soft fork, as with the prior local change).
- A machine-readable phase manifest — the phase ledgers themselves are the resume
  record, per the problem statement; adding a second source of truth would let the two
  drift.
