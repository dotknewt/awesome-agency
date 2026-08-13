# Scoped Re-Review Prompt Template

Use this template when dispatching a re-review after a fix round. The
re-reviewer verifies the findings were addressed and checks the fix diff for
new breakage. It is not a fresh review — the full review already happened.

**Purpose:** Verify each finding from the previous review was addressed, and
that the fix itself broke nothing.

```
Subagent (general-purpose):
  description: "Re-review Task N fix round R"
  model: [MODEL — choose per SKILL.md Model Selection; set to a value you
         know your dispatch tool accepts, or omit it if it doesn't — an
         omitted model inherits the session's model, which may be more
         expensive but is never a dispatch-time failure]
  prompt: |
    You are re-reviewing one task's fix round. A previous review produced
    findings; an implementer has attempted to fix them. Your job is to
    verdict each finding and inspect the fix diff — nothing else.

    ## The Task

    Read the task brief: [BRIEF_FILE]

    ## The Findings Under Verification

    Read the previous review: [FINDINGS_FILE]

    The findings under verification are its Critical/Important findings
    and spec gaps — specifically: [FINDING_IDS]

    ## The Fix

    Read the implementer's report (fix reports are appended at the end):
    [REPORT_FILE]

    **Fix base:** [FIX_BASE_SHA] (the head the previous review saw)
    **Head:** [HEAD_SHA]
    **Diff file:** [DIFF_FILE]

    Read the diff file once — it contains the fix commits, a stat summary,
    and the fix diff with surrounding context. Do not re-run git commands.
    If the diff file is missing, fetch the diff yourself:
    `git diff --stat [FIX_BASE_SHA]..[HEAD_SHA]` and
    `git diff [FIX_BASE_SHA]..[HEAD_SHA]`.

    Your review is read-only on this checkout. Do not mutate the working
    tree, the index, HEAD, or branch state in any way.

    ## Scope

    Your scope is the findings list and the fix diff. Verdict every finding.
    Inspect the fix diff for new problems the fix itself introduced. Do NOT
    re-review code the fix did not touch: if you notice an issue entirely
    outside the fix diff, report it under Out-of-Scope Observations — it
    does not block this task and does not extend the loop. A broad
    whole-branch review happens after all tasks are complete.

    ## Tests

    The implementer re-ran the tests covering the amended code and appended
    the results to the report file. Treat the report as unverified claims:
    confirm the fix report names the covering tests and shows their output,
    and verify the claims against the diff. Do not re-run the suite to
    confirm their report. Run a test only when reading the code raises a
    specific doubt that no existing run answers — and then a focused test,
    never a package-wide suite.

    ## Review File Format

    Write your full re-review to [REVIEW_FILE] — every line there is a
    verdict, a finding with file:line, or a check you ran; no preamble,
    no process narration. If you cannot write the file, say so and
    include the full re-review in your final message instead.

    Structure [REVIEW_FILE] as:

    ### Finding Verdicts

    For each finding in The Findings Under Verification, in order:
    - **[finding one-liner]** — ADDRESSED | NOT ADDRESSED, with file:line
      evidence. "Attempted" is not addressed: the specific defect must no
      longer exist.

    ### New Breakage in the Fix Diff

    Anything the fix itself broke or introduced, with severity
    (Critical/Important/Minor) and file:line. "None" if clean.

    ### Out-of-Scope Observations

    Issues you noticed entirely outside the fix diff. Non-blocking; the
    controller ledgers these for the final review. "None" if none.

    ### Verdict

    **Fix round:** [All findings addressed, no new Critical/Important
    breakage | Findings remain open] — list the open ones.

    ## Final Message — Report Contract

    Report back with ONLY (under 15 lines — the detail lives in the
    review file):
    - **Round verdict:** all addressed | findings remain open
    - Per-finding one-liners: `<finding gist> — ADDRESSED | NOT ADDRESSED`
    - New Critical/Important breakage one-liners (`file:line — gist`),
      or "new breakage: none"
    - Out-of-scope observation count (detail stays in the file)
    - The review file path
```

**Placeholders:**
- `[MODEL]` — reviewer model per SKILL.md Model Selection; scoped
  re-reviews of small fix diffs take a cheap-to-mid tier. Omit if your
  dispatch tool doesn't accept a value you know is valid.
- `[BRIEF_FILE]` — the task brief file (same file the implementer worked from)
- `[FINDINGS_FILE]` — the previous review's file (the task reviewer's
  `…-review.md`, or the prior round's re-review file)
- `[FINDING_IDS]` — the one-liners of the findings under re-check, copied
  from the previous review's contract (gists only — the detail is in
  `[FINDINGS_FILE]`)
- `[REPORT_FILE]` — the implementer's report file (fix reports appended)
- `[FIX_BASE_SHA]` — the head the previous review saw
- `[HEAD_SHA]` — current commit
- `[DIFF_FILE]` — the path `scripts/review-package PLAN_FILE FIX_BASE HEAD` printed
- `[REVIEW_FILE]` — where the re-reviewer writes its full re-review
  (previous review file's name + `-r<R>`, e.g. `…/task-N-review-r2.md`)

**Re-reviewer returns:** the short contract only — round verdict,
per-finding ADDRESSED/NOT ADDRESSED one-liners, new-breakage one-liners,
out-of-scope count, and the review file path. The detail lives in
`[REVIEW_FILE]`.
