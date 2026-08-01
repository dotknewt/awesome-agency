# Work Object Specification

An evidence-linked work object is one directory per code-change task that
keeps the intended change (spec), the captured evidence (diff, test
output, run manifest), and the review decision together as a single
persistent, git-aware object. A reviewer — human or agent — inspects
evidence instead of trusting a summary. Implemented by the
`work-objects-toolkit` plugin (`work-object-guard` skill,
`check_preconditions.py` checker, `work-object-status-gate.sh` hook).

## Directory structure

```
work/<id>-<slug>/
  spec.md                  # intended change — written BEFORE code changes
  evidence/
    diff.patch             # literal `git diff <before>..<after>` output
    test-output.txt        # literal stdout+stderr of the test/build command
    run-manifest.json      # real SHAs, branch, timestamp, exact commands
  review.md                # decision + which evidence files were inspected
```

`<id>` is a stable task ID (issue number, ticket key, or date-based like
`CHG-20260801`); `<slug>` is a kebab-case short description. The `work/`
directory lives at the root of the repo whose changes it tracks (the
checker resolves the repo via `git rev-parse --show-toplevel` from the
work directory).

## spec.md

### Frontmatter

```yaml
---
id: <id>-<slug>
status: draft            # draft | in-review | approved | rejected
created: <ISO8601 date>
---
```

### Body

Three sections, filled in before any code change:

- `## Intent` — what the change is supposed to do, 2–5 sentences.
- `## Scope` — files/modules expected to change.
- `## Acceptance` — how "done" will be checked: which tests, which
  output, which behavior a reviewer should look for in `evidence/`.

Specs are never backfilled after the fact.

## evidence/

Evidence is **captured, never authored**: each file must be the redirect
of a real command's output, not a paraphrase.

### diff.patch

Literal `git diff <commit_before>..<commit_after> [-- <paths>]` output.
Must contain `diff --git` headers, and every path it touches must be
among the files git reports changed between the two commits (a
path-filtered diff is a subset and passes; a hand-written or mismatched
diff does not).

### test-output.txt

Literal stdout+stderr of the test/build command named in the manifest
(`<test_command> > evidence/test-output.txt 2>&1`).

### run-manifest.json

Required keys, all six:

| Key | Meaning |
|---|---|
| `commit_before` | SHA the diff starts from; must exist in history |
| `commit_after` | SHA the diff ends at; must equal the repo's actual current HEAD |
| `branch` | branch name at capture time |
| `generated_at` | ISO8601 timestamp of evidence capture |
| `diff_command` | the exact command that produced diff.patch |
| `test_command` | the exact command that produced test-output.txt |

Short-SHA prefixes are accepted for the HEAD match.

## review.md

### Frontmatter

```yaml
---
id: <id>-<slug>
status: approved          # approved | rejected | changes-requested
reviewer: <name-or-agent>
reviewed_at: <ISO8601>
---
```

### Body

- `## Evidence inspected` — every file under `evidence/` cited **by
  filename** with a specific claim about its contents
  ("test-output.txt — 14 passed, 0 failed", not "tests pass").
- `## Decision` — reasoning tied to specific lines/files in the
  evidence, not a general summary.

## Status transitions

Transitions are gated by
`python3 <plugin>/scripts/check_preconditions.py <work_dir> --transition <t>`.
Exit 0 permits the transition; non-zero prints a `BLOCKED:` reason and is
a hard stop — never narrated past.

| Transition | Checks |
|---|---|
| `--transition in-review` | spec.md + all three evidence files exist, non-empty; manifest valid with all six keys; `commit_after` == actual HEAD and exists in history; `commit_before` exists; diff.patch is real git output touching only actually-changed files |
| `--transition approved` | everything above, plus: review.md exists, has YAML frontmatter whose `status` is `approved`, and names every file in `evidence/` |

The plugin's PreToolUse hook enforces this independently of agent
discipline: a Write/Edit that flips `status:` to `in-review`/`approved`
in `work/*/spec.md` or `work/*/review.md` is blocked (exit 2) when the
checker fails. A `review.md` write claiming `approved` is gated with the
`in-review` check — the full `approved` check needs `review.md` on disk,
which that write is creating — and the full gate fires when `spec.md` is
flipped to `approved` afterward.

Evidence is never silently overwritten: a new round of changes gets a
new `commit_after` and fresh evidence; old evidence is kept so the
history of attempts stays inspectable. Consequently evidence goes stale
by design when HEAD moves — the checker blocks until it is recaptured.

## Relationship to superpowers

The `superpowers` plugin's `subagent-driven-development` produces
ephemeral evidence bundles (gitignored `.superpowers/sdd/` review
packages and task reports), and `verification-before-completion` states
the evidence-before-claims discipline as prose. Work objects are the
durable, git-tracked, mechanically enforced complement: use SDD scratch
for in-session control flow, a work object when the evidence should
outlive the session and be reviewable from the repo alone. No changes to
the superpowers plugin are implied.

## Validation limits

The checks are deliberately shallow and mechanical: they prove the
reviewer/author engaged with real artifacts, not that the judgment was
sound. Known limits:

- The hook intercepts Write/Edit tools only; shell redirection writes
  bypass it (the skill's hard rule and a project AGENTS.md drop-in cover
  that path).
- The diff-consistency check is name-level, not content-level.
- Review citation checking is substring-based; it defeats generic
  sign-offs, not determined bad faith.
