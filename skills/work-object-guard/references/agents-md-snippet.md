# AGENTS.md drop-in — evidence-linked work objects

Paste the block below into the AGENTS.md of any project that should
enforce evidence-linked work objects. Do not add it to plugin or
marketplace repos that merely *ship* this toolkit.

```markdown
### Evidence-linked work objects

Every code-change task gets a `work/<id>-<slug>/` directory: `spec.md`
(written BEFORE any code change, `status: draft`), `evidence/diff.patch`,
`evidence/test-output.txt`, `evidence/run-manifest.json`, and `review.md`.

- Evidence is captured, never authored: redirect the real command's
  output (`git diff ... > evidence/diff.patch`; `<test cmd> >
  evidence/test-output.txt 2>&1`). Never hand-write or paraphrase it.
- `status:` may move to `in-review` or `approved` only after
  `check_preconditions.py <work_dir> --transition <status>` exits 0.
  A non-zero exit is a hard stop — fix the gap, do not narrate past it.
- `review.md` must cite each evidence file by name with a specific
  claim ("test-output.txt: 14 passed, 0 failed"), not "tests pass".
- Never overwrite existing evidence: a new round of changes gets a new
  `commit_after` and fresh evidence files alongside the old ones.
```
