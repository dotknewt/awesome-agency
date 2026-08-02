---
name: work-object-guard
description: Enforces evidence-linked work objects for code-change tasks — a spec, a captured git diff, captured test/build output, and a review that cites specific evidence, kept together under a per-task work directory (e.g. work/CHG-0001-slug/). Use this skill any time you are about to start a code change task, mark a task's status as in-review or approved, or write a review/summary of a completed change. Also use it when the user asks to scaffold a task, gate a review, or set up evidence-linked/verifiable work tracking. Do NOT let status move to in-review or approved by narrating that preconditions are met — always run the checker script and treat a non-zero exit as a hard stop.
---

# Work Object Guard

Keeps the intended change (spec), the actual diff, the actual test/build
output, and the review decision together as one inspectable object per
task, so a reviewer checks evidence instead of trusting a summary.

## When to use this

- Starting any code-change task → scaffold a new work object (Step 1).
- About to say a task is "ready for review" → run the checker for
  `in-review` (Step 3) before saying so.
- About to approve/merge/close a task → run the checker for `approved`
  (Step 4) before saying so.
- Writing a review → the checker will reject a review that doesn't
  name the evidence files it inspected — write review.md accordingly.

## Hard rule

**Never** write "tests pass" / "diff looks good" / "ready for review"
based on memory or a general impression. If you ran a test command or
produced a diff, the file in `evidence/` must contain that command's
actual output — not your paraphrase of it. If the checker script
blocks a transition, stop and fix the underlying gap; do not proceed
past a non-zero exit code by explaining why it's probably fine.

## Step 1 — Scaffold a new work object

```bash
id="CHG-$(date +%Y%m%d)-<short-slug>"
mkdir -p "work/$id/evidence"
cp "${CLAUDE_PLUGIN_ROOT}/skills/work-object-guard/references/spec_template.md" "work/$id/spec.md"
```

Fill in `spec.md`'s Intent / Scope / Acceptance sections *before*
touching code. Leave `status: draft`.

## Step 2 — Capture evidence (never hand-write it)

Run the actual commands and redirect their real output:

```bash
git diff <base>..<head> -- <paths> > "work/$id/evidence/diff.patch"
<test_command> > "work/$id/evidence/test-output.txt" 2>&1
```

Write `evidence/run-manifest.json` with the real commit SHAs — see
`references/manifest_template.json`. `commit_after` must be the actual
current HEAD of the diff you captured, not an approximation.

## Step 3 — Gate the in-review transition

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_preconditions.py" "work/$id" --transition in-review
```

- Exit 0 → set `spec.md` frontmatter `status: in-review`.
- Non-zero → read the `BLOCKED:` reason on stderr and fix it (missing
  file, empty file, stale SHA). Do not override.

## Step 4 — Review, then gate the approved transition

Write `review.md` (see `references/review_template.md`). It must:
- Include YAML frontmatter with a `status` field.
- Reference each file under `evidence/` **by filename**, with a
  specific claim about its contents (e.g. "test-output.txt: 14
  passed, 0 failed" — not "tests pass").

Then run:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_preconditions.py" "work/$id" --transition approved
```

Exit 0 → the transition is valid. Non-zero → the review is
incomplete (usually: an evidence file wasn't actually referenced) —
go back and inspect it properly rather than adding a token mention of
the filename to satisfy the check.

## What the checker actually verifies

See `scripts/check_preconditions.py` (at the plugin root, shared with
the enforcement hook) for the exact logic. In short:

- Required files exist and are non-empty.
- `run-manifest.json` is valid and has the required keys.
- `commit_after` matches the repo's actual current HEAD (git-aware —
  catches evidence that's gone stale because the branch moved on).
- `commit_before` and `commit_after` actually exist in the repo's
  history (catches fabricated SHAs).
- `diff.patch` parses as real git diff output and only touches files
  that actually changed between `commit_before` and `commit_after`
  (catches hand-written "evidence").
- For `approved`: `review.md` exists, its frontmatter decision is
  `approved`, and it names every evidence file.

This is deliberately a shallow, mechanical check — it cannot verify
that a review's *judgment* was sound, only that the reviewer engaged
with the real artifacts instead of writing a generic sign-off. Human
or senior-agent judgment is still required for the content of the
review itself.

## Enforcement hook

This plugin also ships a PreToolUse hook
(`scripts/work-object-status-gate.sh`) that independently blocks
Write/Edit calls flipping `status:` to `in-review` or `approved` in
`work/*/spec.md` or `work/*/review.md` when the checker fails — the
gate holds even if this skill's instructions are ignored. One
asymmetry to know: a `review.md` write claiming `status: approved` is
gated with the `in-review` check (evidence must exist and be fresh),
because the full `approved` check needs `review.md` on disk — which
that very write is about to create. The full `approved` gate fires
when `spec.md` is flipped to `approved` afterward. Running the checker
yourself first (Steps 3–4) means you never hit a blocked edit.

## Project drop-in

To make this pattern a standing rule in a project, paste the block in
`references/agents-md-snippet.md` into that project's AGENTS.md.

## Relationship to superpowers

The superpowers `subagent-driven-development` skill produces ephemeral
evidence (gitignored `.superpowers/sdd/` review packages and task
reports), and `verification-before-completion` states the
evidence-before-claims discipline as prose. Work objects are the
durable, git-tracked, mechanically gated version of the same idea —
use them when the evidence should outlive the session.

## Reference files

- `references/spec_template.md` — spec.md starting point
- `references/review_template.md` — review.md starting point
- `references/manifest_template.json` — run-manifest.json starting point
- `references/agents-md-snippet.md` — paste-ready AGENTS.md rule block
