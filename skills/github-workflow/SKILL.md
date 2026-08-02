---
name: github-workflow
description: >
  Use when the user asks about GitHub Actions CI setup, workflow defaults, concurrency
  settings, path filters, or chained / stacked PRs. Triggers on phrases like
  "set up CI defaults", "GitHub Actions concurrency", "cancel superseded runs",
  "skip workflow for docs changes", "path filters", "stacked PRs", "chained PRs",
  "follow-up PR", "branch off an unmerged branch", "rebase onto main",
  "squash-merge tangle", "same-file conflict", "open a PR for this change",
  "how do I chain multiple PRs", or "after this PR merges".
---

## Baseline (always loaded)

`plugins/github-toolkit/instructions/branch-hygiene.md` — one branch per PR, cleanup after squash-merge, stale-branch sweep.
`plugins/github-toolkit/instructions/commit-vs-pr.md` — when to commit directly vs. open a PR. Do not restate these; they are already in context.

---

## CI defaults for new workflows

See the annotated template at `skills/github-workflow/references/ci-defaults.yml`. The four non-negotiable defaults:

### 1. Push trigger on `main` only

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

Never add `branches: ['**']` or `branches: ['*']` to the push trigger. PR events already run CI on every feature branch push; adding a parallel push trigger doubles the bill and clutters the checks list.

### 2. Concurrency — cancel PR runs, preserve main runs

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
```

The expression evaluates to `true` for pull_request events (cancels the queued run when a new push arrives) and `false` for push-to-main (lets the run finish — you want a clean main history, not a cancelled deploy).

### 3. Path filters — skip for pure docs/config changes

```yaml
on:
  push:
    paths-ignore:
      - "**.md"
      - "instructions/**"
      - "docs/**"
      - ".gitignore"
      - "LICENSE"
  pull_request:
    paths-ignore:  # mirror the push block
      - "**.md"
      - "instructions/**"
      - "docs/**"
      - ".gitignore"
      - "LICENSE"
```

Adjust the list to match your repo's non-code paths. `.github/workflows/sync-labels.yml` in this repo is the existing path-filter precedent (paths-include variant). If a workflow *only* cares about a narrow set of files, use `paths:` (include) instead of `paths-ignore:` (exclude).

### 4. `workflow_dispatch` for manual reruns

Always add `workflow_dispatch: {}` so you can trigger the workflow from the GitHub UI without pushing a dummy commit.

---

## Chained / stacked PR sequencing

### Default: sequence, don't stack

Open PR #2 only after PR #1 merges. This is the safe default and avoids all of the problems below.

Stack (branch off an unmerged branch) only when:
- PR #2 genuinely depends on code in PR #1 (not just "related"), **and**
- The two PRs touch disjoint file sets.

If any file appears in both PRs, sequence instead.

### Detecting the conflict trap before it bites

Before opening PR #2 while PR #1 is still open:

```bash
git diff --name-only main...pr-1-branch > /tmp/pr1-files.txt
git diff --name-only main...pr-2-branch > /tmp/pr2-files.txt
comm -12 <(sort /tmp/pr1-files.txt) <(sort /tmp/pr2-files.txt)
```

Any output from `comm` is an overlap. Overlapping PRs will conflict when one merges. Split the work along file boundaries or sequence the PRs.

### Branching off an unmerged branch

```bash
git checkout pr-1-branch
git checkout -b pr-2-branch
```

Understand the recovery path before you do this. **Before** following branch-hygiene.md cleanup, save `pr-1-branch`'s tip SHA — you need it as the exclusion point for the rebase:

```bash
git rev-parse pr-1-branch   # save this SHA, e.g. abc1234
```

After PR #1 squash-merges:

```bash
git checkout main && git pull --ff-only origin main
git rebase --onto main abc1234 pr-2-branch   # abc1234 = saved SHA of pr-1-branch tip
git push --force-with-lease origin pr-2-branch
```

`--onto main abc1234` replays only the commits unique to `pr-2-branch` (i.e., above `abc1234`) onto the new `main`. If you already deleted `pr-1-branch` without saving the SHA, recover it with `git reflog | grep pr-1-branch`.

This keeps the history linear and the squash-merge of PR #2 clean.

### Rebase-on-main cadence

While PR #1 is open and receiving review-driven commits, rebase `pr-2-branch` onto the tip of `pr-1-branch` after each significant change:

```bash
git fetch origin
git rebase origin/pr-1-branch pr-2-branch
```

After PR #1 merges, do the `--onto main` rebase above immediately — don't wait until PR #2 review is complete.

Always rebase, never merge `main` back into a feature branch. A merge commit breaks the linear history that makes squash-merge clean.

### Squash-merge tangle recovery

If PR #1 squash-merged and you accidentally committed follow-up work onto `pr-1-branch` instead of a new branch:

```bash
git log pr-1-branch --oneline   # identify the new commits above the squash point
git checkout main && git pull --ff-only origin main
git checkout -b pr-2-branch
git cherry-pick <sha1> [<sha2> ...]
git push -u origin pr-2-branch
```

Do **not** try `git rebase main pr-1-branch`. The squash commit that landed in `main` re-introduces every change from PR #1 as a new commit SHA, so Git sees them all as conflicts. Cherry-pick is the clean path.

See `plugins/github-toolkit/instructions/branch-hygiene.md` for local and remote branch cleanup after recovery.
