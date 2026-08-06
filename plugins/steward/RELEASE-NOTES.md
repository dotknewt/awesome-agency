# Steward Release Notes

## v1.3.0 (2026-08-06)

### Deliberate Model Assignment

- **`docs-spec-maintainer`, `instructions-maintainer`, and `marketplace-maintainer`
  now state `model: inherit` outright.** All three already ran on the caller's model,
  but only because the field was absent and Claude Code defaults it silently — which
  made a deliberate choice indistinguishable from an oversight, and invited a future
  contributor to "optimize" them onto Haiku alongside their cheaper siblings. That
  would be wrong: unlike `docs-user-maintainer`, which checks syntactically verifiable
  things like stale commands and version numbers, these three have to judge whether a
  documented *intent* still holds, and `marketplace-maintainer` specifically exists to
  answer a question no validator can. Each description now says so, so the reasoning
  survives the next person to read it.

- **`schema-maintainer` and `conventions-maintainer` moved from Haiku to Sonnet.**
  Both were put on Haiku to keep routine audits cheap, but both sweep an entire
  repository — which runs into two limits the original choice did not account for:
  Haiku caps at 200K tokens of context, and its reliability on long tool-call chains
  degrades past roughly 7–10 steps, exactly the shape of "walk the repo and run every
  validator". The failure mode is silent: a context overflow reads as a thin audit,
  not an error, so these agents could have been quietly under-reporting on any
  large repo. `docs-user-maintainer` stays on Haiku — stale commands and wrong
  version numbers really are syntactically checkable — but its description now warns
  that a docs-heavy repo can exceed the same cap.


## v1.2.0 (2026-08-06)

### Marketplace Release Discipline

- **New `marketplace-maintainer` agent audits whether changes were recorded, and
  why.** Nothing in this repo checked that a bundle whose content changed also said
  what changed — the reasoning behind a change survived only in commit messages,
  which are invisible to anyone reading the installed plugin. The agent resolves
  bundle ownership through the pool symlinks, then reports bundles missing a version
  bump or a release-notes entry, and — the part no validator can do — flags entries
  that merely restate the diff instead of giving a reason. It is chartered to leave
  manifest validity to `schema-maintainer` so `/maintain` does not have to dedupe
  overlapping findings.
- **New `release-notes` skill defines the document.** It carries the heading and
  category format, the requirement that an entry state *why*, and the rule that the
  `## v<version>` heading and `plugin.json` must be bumped in the same edit. It is
  the applying mechanism `/maintain` offers for release-notes findings, mirroring how
  instruction findings route through `instructions-revise`.
- **`release-notes-audit.py` is the shared engine.** The mechanical checks live in
  one script under `scripts/` rather than being restated in prose, so the agent and
  this repository's CI cannot drift apart in what they consider a violation. Bundles
  carrying a `.vendored` marker are exempt, which keeps upstream-synced bundles
  pristine.

### Maintain

- **`/maintain` routes to the new maintainer** when changes touch `plugins/` or any
  pooled artifact a bundle ships. The `full` sweep no longer hard-codes "all five"
  maintainers, since the applicable set now depends on what kind of repo it is
  running in.

## v1.1.0 (2026-08-06)

Notes for earlier versions reconstructed from git history.

### Maintain

- **`conventions` wired into the sweep.** Project conventions drifted silently
  because no maintainer owned them; `conventions-maintainer` now reports gaps and
  the `conventions` skill's scaffold mode applies them, routing STATE.md creation
  through `state-keeper`.

## v1.0.0 (2026-08-06)

### Merge

- **`maintainer-toolkit` and `instruction-management` merged into `steward`.** The
  two plugins were always installed together — the maintainers reported instruction
  drift that only the other plugin's skills could fix — and splitting them meant a
  user could install the reporting half without the applying half.
- **Five read-only maintainer agents** (user docs, spec docs, instructions, schemas,
  state) report drift; the `/maintain` orchestrator merges their findings into one
  prioritized list. Agents never write: report-and-propose keeps a sweep from
  applying a fix nobody approved.
