# Steward Release Notes

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
