---
name: release-notes
description: >
  Write and maintain a plugin's RELEASE-NOTES.md — one entry per released version,
  stating what changed and why it changed. Use when the user asks to "update the
  release notes", "add a changelog entry", "what changed in this version", when
  bumping a plugin's version in plugin.json, or when a maintenance sweep reports a
  missing or uninformative release-notes entry. Also use when backfilling notes for
  a plugin that has none.
---

# Release Notes

Every shipped extension in this marketplace keeps a `RELEASE-NOTES.md` at its
plugin root. It is the human record of *why the extension is the way it is* —
the reasoning that a diff throws away.

**The rule: if a bundle's content changed, its version bumped, and that bump has
an entry saying what changed and why.**

## The one thing that matters

An entry that only says *what* changed is worthless — `git log` already says that,
more accurately. The value is in the *why*.

| Don't write | Write |
|---|---|
| Updated `SKILL.md`. | Additional trigger wording added to improve automatic trigger reliability — the skill was not firing on "audit this plugin" phrasing. |
| Fixed the instructions symlink. | The bundle symlinked the whole shared `instructions/` pool, so it shipped 10 unrelated files and silently lost the 3 it reads when that pool was repurposed. Now scoped to `instructions/github-toolkit/`. |
| Bumped to 1.2.0. | *(not an entry — say what the bump contains)* |
| Various improvements. | *(not an entry — enumerate them or omit them)* |

The test: **could a reader who disagrees with the change tell why you made it?**
If not, the entry is not finished.

## Document shape

````markdown
# <Plugin Name> Release Notes

## v1.2.0 (2026-08-06)

### <Category>

- **<Bolded one-line lede.>** Then the why: what was wrong, what observation or
  report prompted it, and what the change does about it. One paragraph is plenty.

### Fixes

- **<Bolded lede.>** <Why.>

## v1.1.0 (2026-07-14)
...
````

Rules:

- **Newest version first.** Append new sections at the top, never rewrite history.
- **One `## v<version> (<YYYY-MM-DD>)` heading per released version**, matching the
  `version` in that bundle's `.claude-plugin/plugin.json` exactly (no `v` in the
  manifest, `v` in the heading). CI matches on this.
- **`###` category headings** group related entries. Invent categories that fit the
  change — component names (`Skills`, `Hooks`, `Agents`), themes
  (`Trigger Reliability`, `Windows`), or `Fixes`. Don't force a fixed taxonomy.
- **Bold lede, then prose.** The bolded sentence is the claim; the prose is the
  justification. A reader skimming only bold text should get an accurate summary.
- **Prefer one entry per user-visible change**, not one per commit. Three commits
  that together fix one bug are one entry.

## Writing an entry

1. Read the actual diff for the bundle's members — resolve the symlinks under
   `plugins/<name>/` to their pool paths, then `git log`/`git diff` those.
2. For each change, answer: *what was the observable problem?* If you cannot name
   one, the change was probably cosmetic — say so plainly or leave it out.
3. Group into categories, write the bold lede last (it is a summary of the prose,
   so write the prose first).
4. Bump `version` in `.claude-plugin/plugin.json` in the same edit. The heading and
   the manifest must agree before you finish.

Reference an issue or PR number when one exists (`(#1959)`), and name the evidence
when a change was driven by an observation ("observed in the wild", "eval runs
documented in `docs/specs/`"). Unsupported superlatives are noise.

## Scope in this repo

- **Applies to every bundle in `plugins/`** except vendored ones. `superpowers` is
  vendored from upstream and its `RELEASE-NOTES.md` is pinned for drift detection —
  never write into it.
- **Micro-entries get no notes.** Individually installable skills and agents share a
  flat `1.0.0`; the release record lives with the bundle that ships them.
- A pool artifact owned by two bundles gets an entry in **each** bundle's notes,
  written from that bundle's perspective.

## Backfilling a plugin with no notes

Create the file with a single entry for the current manifest version, reconstructed
from `git log`. Summarize the bundle's reason for existing and any notable decisions
still visible in the tree — don't fabricate a version history that was never
released. Mark it plainly:

```markdown
## v1.1.5 (2026-08-06)

Initial release notes, reconstructed from git history. Earlier versions shipped
without notes.
```

## Red flags

| Excuse | Reality |
|---|---|
| "The commit message already explains it." | Commit messages are per-commit and invisible to anyone reading the installed plugin. The notes are the shipped record. |
| "It's a trivial wording tweak." | Trigger wording is load-bearing — it decides whether the skill fires at all. Say what you changed it *for*. |
| "I'll write the notes when I cut the release." | The reasoning is in your head now and gone later. That is exactly what produces "various improvements". |
| "Nothing user-visible changed." | Then the version does not need a bump either. If you bumped, something changed — name it. |
