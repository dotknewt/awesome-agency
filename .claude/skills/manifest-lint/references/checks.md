# manifest-lint checks

## Reused from hooks-toolkit

Run via `hooks/hooks-toolkit/scripts/validate-plugin-json.sh` and `validate-skill-frontmatter.sh` — the hooks-toolkit pool's own validators, tracked in this repo. If you need to change these rules, change them there — both the `PostToolUse` hook and this skill call the same scripts. If the scripts are missing (incomplete checkout), manifest-lint prints a `WARN` and skips just these shared checks — the repo-wide checks below still run.

- Valid JSON (`plugin.json`, `marketplace.json`) / presence of `---` frontmatter delimiters (`SKILL.md`).
- Required fields: `name` + `description` on plugin manifests; `name` + `plugins[]` on `marketplace.json`; `name` + `description` in SKILL.md frontmatter.
- `name` must be kebab-case.
- `version`, if present, should look like semver (`X.Y.Z`) — warning only, doesn't fail.
- SKILL.md over 500 lines — warning, move detail into `references/`.

## New in manifest-lint (repo-wide only)

### name ↔ directory match

- `plugin.json`: `name` must equal the directory containing `.claude-plugin/` (e.g. `plugins/hooks-toolkit/.claude-plugin/plugin.json` → name must be `hooks-toolkit`).
- `SKILL.md`: `name` must equal its parent directory (e.g. `.claude/skills/manifest-lint/SKILL.md` → name must be `manifest-lint`).
- Deliberately scoped to `*/.claude-plugin/plugin.json` only — `.github/plugin/plugin.json` files (used by some forked plugins for a GitHub App manifest) are a different mechanism and excluded.
- Fix: rename the directory or the `name` field, whichever is correct.

### plugin.json ↔ marketplace.json version consistency

- For each `plugin.json`, look up the matching entry in `.claude-plugin/marketplace.json` by `name` and compare `version`.
- Fix: bump whichever one is stale so both agree. Bundle entries in the generated `marketplace.json` deliberately omit `version` (the bundle's `plugin.json` is authoritative), so this check only fires if an entry gains a version that then drifts.

### version bump vs. last commit

- There's no per-plugin git tag convention in this repo (`git tag` currently returns nothing), so "bumped since last release" can't be checked against a tag. Instead: if a manifest file has uncommitted changes AND its `version` field is identical to the version at `HEAD` for that file, warn.
- **Gitignored paths degrade with a visible `WARN`, not silently.** All real manifests are tracked in this repo now; the `git check-ignore` branch only fires for stray local copies and prints `WARN [file]: version-bump check skipped: path is git-ignored...` instead of silently passing.
- For paths that genuinely are new-but-tracked files inside `agency` itself (not gitignored, just not committed yet), the check still silently no-ops — there's really nothing to compare there, and that case doesn't need a warning.
- This only catches the "I edited a plugin.json / SKILL.md right now and forgot to bump" case — it says nothing about releases that already landed.
- If this repo adopts a tagging convention later (e.g. `<plugin-name>@X.Y.Z`, as hinted at in `skills/make-a-monorepo/SKILL.md`), update `check_version_bump()` in `scripts/manifest-lint.sh` to prefer `git describe --match "<plugin-name>@*"` over the `HEAD` comparison.
- Not a false-positive risk for intentional non-release edits (typo fixes, wording tweaks) — it's a warning, not an error, and won't fail the run.

### marketplace.json source shape

- `.plugins[].source` is a relative `./` path inside this single-repo marketplace:

  ```json
  "source": "./plugins/<bundle>"     // bundle entries
  "source": "./skills/<skill>"       // skill micro-entries
  "source": "./agents/<agent>"       // agent micro-entries
  ```

- manifest-lint checks, per entry: `source` is a string; it starts with `./`; it is not the bare `"./"` (repo-root sources unconditionally absorb every pooled agent/command via default discovery — see `AGENTS.md`); and the path exists in the repo.
- `marketplace.json` is **generated** — fix problems in the pools/bundles and re-run `.github/scripts/generate-marketplace.py` (or fix the generator), never by hand-editing the manifest. CI runs the generator with `--check`.
- Fix: restore/rename the missing pool directory, or regenerate the manifest if an entry is stale.

### broken symlinks (plugins/, agents/)

- Bundles (`plugins/<name>/`) and self-contained agent dirs (`agents/<name>/`) are built from symlinks into the shared pools; Claude Code dereferences them at install time. A broken link ships a broken plugin.
- manifest-lint runs `find plugins agents -xtype l` and reports each hit as an ERROR.
- Fix: repoint or remove the dead link (usually a pool item was renamed/deleted without updating the bundle), then regenerate the manifest if membership changed.
