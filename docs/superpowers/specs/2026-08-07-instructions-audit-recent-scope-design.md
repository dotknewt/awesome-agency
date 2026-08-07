# instructions-audit: recent-commits scope — design

Date: 2026-08-07
Origin: `docs/TODO.md` → steward → "additional command that performs
instructions-audit only adding changes that surfaced in the last 5 commits"

## Problem

`instructions-audit` always runs a full-repo audit: discover every instruction
file, score each against the rubric, print a report, then run both sub-skills.
That is the right tool for periodic maintenance, but heavyweight for the common
case the TODO describes: "I just landed a few commits — fold anything they
surfaced into AGENTS.md." Today that user either pays for a full audit or
hand-edits, and there is no invocable that scopes the audit to recent history.

## Decision

Add a **scoped mode** to the existing `instructions-audit` skill, selected by
argument, instead of shipping a new command or a sibling skill.

Argument grammar (mirrors the `maintain` skill's, so the bundle stays
consistent):

- *(none)* → full audit, exactly as today.
- `recent` → scoped to the last **5** commits (the TODO's default).
- `last <N> commits` → scoped to the last N commits.
- `since <ref>` → scoped to `<ref>..HEAD`.

### Alternatives considered

- **Separate skill `instructions-audit-recent`** — duplicates the audit
  workflow and adds a micro-entry to maintain; the delta is a scoping rule,
  not a new capability. Rejected.
- **Literal `commands/steward/*.md` command** (the TODO's wording) — Copilot
  CLI has no commands concept; `.github/host-compat.json` requires every
  shipped command to have a skill counterpart, which collapses this option
  back into the chosen one. Skills are slash-invocable on both hosts
  (`/instructions-audit recent`), so the "command" intent is met. Rejected.

## Scoped-mode behavior

1. **Scope resolution** — compute `BASE` from the argument
   (`HEAD~5` for `recent`, `HEAD~N`, or `<ref>`); collect
   `git log --oneline $BASE..HEAD` and `git diff --name-status $BASE..HEAD`.
   If the range is empty (or the repo has fewer commits than requested, in
   which case clamp to the root commit), say so and offer the full audit —
   never silently fall back.
2. **Discovery unchanged** — instruction files are found exactly as in
   Phase 1; legacy-`CLAUDE.md` migration is still *flagged* (currency of the
   setup, not of content), but migration is only proposed, never bundled into
   the scoped edits.
3. **Assessment replaced** — no rubric scoring. Instead, derive candidate
   updates only from the commit range: changed commands/scripts/tooling,
   moved or renamed paths the instructions mention, new conventions the
   diff introduces, gotchas evident from fix commits.
4. **Report** — a short "Scoped Audit" report: the range audited, per-file
   proposed diffs with a one-line *why* citing the commit that surfaced it,
   and an explicit "not checked: everything outside this range" note.
5. **Sub-skills skipped** — `instructions-revise` (session learnings) and
   `instructions-restructure` (depth rebalancing) are full-audit concerns;
   scoped mode proposes its own diffs directly. User skip-phrases are moot.
6. **Apply gate unchanged** — propose diffs, wait for approval, then edit.

## Changes

- `skills/instructions-audit/SKILL.md` — add argument grammar to the
  description (trigger phrases: "audit recent changes", "update AGENTS.md for
  the last N commits") and a "Scoped mode" section implementing the behavior
  above.
- `plugins/steward/.claude-plugin/plugin.json` — bump `1.4.0` → `1.5.0`.
- `plugins/steward/RELEASE-NOTES.md` — v1.5.0 entry (what + why).
- `.claude-plugin/marketplace.json` — regenerate (description drift only).

No new files, entries, symlinks, or agents. `instructions-maintainer`'s
report-only role is untouched — this is the *applying* path, scoped.

## Testing

No test harness exists for skills beyond CI validation. Verify with:
generator `--check`, `check-host-compat.py`, skill-frontmatter validation,
`release-notes-audit.py --all`.
