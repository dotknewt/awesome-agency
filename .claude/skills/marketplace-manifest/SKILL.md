---
name: marketplace-manifest
description: This skill should be used when the user asks to "edit marketplace.json", "generate marketplace", "add a marketplace entry", "register a new bundle", "withdraw a bundle", "BUNDLE_ORDER", "MICRO_VERSION", "micro-entry", or needs guidance on `.claude-plugin/marketplace.json`, `.github/scripts/generate-marketplace.py`, or marketplace CI validation.
metadata:
  version: "0.1.0"
---

# Marketplace Manifest Maintenance

## Overview

Treat `.claude-plugin/marketplace.json` as generated output. Never hand-edit it. All marketplace structure comes from `.github/scripts/generate-marketplace.py`, and CI enforces that the generated file is current.

Use this skill when adding, removing, renaming, or reviewing marketplace entries for bundles, skills, or agents. Cross-check host portability with the `host-portability` skill before shipping a new entry.

## Required Workflow

1. Edit the source of truth: bundle directories under `plugins/`, pool content under `skills/` or `agents/`, or constants in `.github/scripts/generate-marketplace.py`.
2. Regenerate the manifest:

   ```bash
   python3 .github/scripts/generate-marketplace.py
   ```

3. Verify generator drift exactly as CI does:

   ```bash
   python3 .github/scripts/generate-marketplace.py --check
   ```

4. Check host portability for all generated entries:

   ```bash
   python3 .github/scripts/check-host-compat.py
   ```

5. Inspect `.claude-plugin/marketplace.json` only as generated output. If it is wrong, fix the generator inputs or constants, then regenerate.

## Generator Responsibilities

`.github/scripts/generate-marketplace.py` builds three entry classes:

| Entry class | Source | Shape |
|---|---|---|
| Bundle | `plugins/<name>/` | `{ "name": "<name>", "description": <plugin.json description>, "source": "./plugins/<name>", "author": ... }` |
| Skill micro-entry | `skills/<name>/` | `{ "name": "<skill>", "description": <SKILL.md description>, "version": MICRO_VERSION, "source": "./skills/<name>", "strict": false }` |
| Agent micro-entry | `agents/<name>/` | `{ "name": "<agent>-agent", "description": <agent frontmatter description>, "version": MICRO_VERSION, "source": "./agents/<name>", "strict": false, "agents": ["./<agent>.md"] }` |

Bundle entries intentionally omit `version`; the bundle's `plugins/<name>/.claude-plugin/plugin.json` is authoritative. Micro-entries use the generator constant `MICRO_VERSION`, currently `1.0.0`, for coordinated standalone skill/agent refreshes.

## Registering Bundles

Add every shippable `plugins/<name>/` directory to `BUNDLE_ORDER` in `.github/scripts/generate-marketplace.py`. The generator hard-fails on any plugin directory not listed:

```text
bundles missing from BUNDLE_ORDER: ['<name>']
```

Use `BUNDLE_ORDER` for both registration and marketplace ordering. A listed-but-missing bundle is skipped, which is important for parked bundles in `wip/plugins/`.

Keep bundle metadata in `plugins/<name>/.claude-plugin/plugin.json`. Update the bundle version and `plugins/<name>/RELEASE-NOTES.md` when bundle members or metadata change; marketplace bundle entries still carry no version.

## Skill Micro-Entries

The generator creates a standalone entry for every directory under `skills/` except exclusions. Maintain these constants deliberately:

- `BUNDLE_BOUND_SKILLS` — skills that only work inside their owning bundle because they depend on plugin-root scripts, hooks, or other bundled files. They get no standalone micro-entry.
- `NON_SKILL_DIRS` — directories under `skills/` that are not shippable skills, such as `in-progress`.
- `SKILL_ENTRY_RENAMES` — rename micro-entries when a bare skill name collides with another marketplace entry name.

The generator reads each skill description from `skills/<name>/SKILL.md` frontmatter and truncates long descriptions for marketplace display. Fix bad descriptions in the skill source, not in `marketplace.json`.

## Agent Micro-Entries

The agents pool is dir-per-agent: `agents/<name>/<name>.md`. The generator creates `<name>-agent` entries with narrow sources and explicit `agents: ["./<name>.md"]` so standalone installs load the symlinked agent file correctly.

Keep standalone agents self-contained. If an agent references pooled instructions or skills, symlink those resources into `agents/<name>/` so the micro-install includes them.

## Forbidden Repo-Root Sources

Never create an entry with `source: "./"`. Claude Code default-scans `./agents/` and `./commands/` at the plugin source root, and empty arrays do not suppress those scans. A repo-root source would absorb every pooled agent and command into one install.

CI repeats this rule in `.github/workflows/validate.yml` under `source paths are relative and exist`:

```bash
case "$src" in
  ./) echo "::error::source './' is forbidden (repo-root sources absorb every pooled agent/command)"; failed=1 ;;
  ./*) [ -e "$src" ] || { echo "::error::source path does not exist: $src"; failed=1; } ;;
  *) echo "::error::source must start with ./ : $src"; failed=1 ;;
esac
```

## Withdrawing Bundles

Withdraw a bundle by doing both operations:

1. Move `plugins/<name>/` to `wip/plugins/<name>/`.
2. Remove `<name>` from `BUNDLE_ORDER`.

Do not only move the directory. A listed-but-missing bundle is skipped, but an unlisted directory under `plugins/` hard-fails. Regenerate and run `--check` after the move.

Remember that `wip/plugins/<name>/` symlinks need one extra `../` compared with `plugins/<name>/`, and CI's symlink and manifest scans deliberately do not walk `wip/`.

## CI Marketplace Job

The `marketplace` job in `.github/workflows/validate.yml` verifies:

- Generated manifest drift: `python3 .github/scripts/generate-marketplace.py --check`.
- JSON shape and marketplace name `awesome-agency` via `jq`.
- Kebab-case, unique plugin entry names.
- Relative existing sources, with `./` forbidden.
- No broken symlinks under `plugins` or `agents`.
- `${CLAUDE_PLUGIN_ROOT}` references resolve via `.github/scripts/check-plugin-root-refs.py`.
- Every agent declares a model via `.github/scripts/check-agent-models.py`.
- Cross-host installability via `.github/scripts/check-host-compat.py`.

Run the smallest relevant checks locally after changing marketplace inputs. For a pure generator edit, run at least:

```bash
python3 .github/scripts/generate-marketplace.py --check
python3 .github/scripts/check-host-compat.py
```

## Host-Compatibility Gate

Before adding a new marketplace entry, apply the `host-portability` skill. The generated entry must satisfy the host matrix in `.github/host-compat.json`:

- Provide skill counterparts for command-only capabilities, or declare a `commands` exception.
- Avoid unqualified model-dependent claims in agents because Copilot ignores `model:` aliases.
- Add body prose guards for skills using `disable-model-invocation: true`.
- Restrict hooks to shared events unless a `hook-events` exception is intentional.
- Document manual Copilot setup for bundled `.mcp.json` servers or add a `bundled-mcp` exception.

Do not encode host-specific policy in `marketplace.json`; put policy in `.github/host-compat.json` and let the checker derive findings.

## Common Mistakes

- Editing `.claude-plugin/marketplace.json` directly instead of regenerating it.
- Creating `plugins/<name>/` without adding `<name>` to `BUNDLE_ORDER`.
- Forgetting to remove a withdrawn bundle from `BUNDLE_ORDER`.
- Adding a skill that depends on bundle-local scripts but forgetting `BUNDLE_BOUND_SKILLS`.
- Bumping individual micro-entry versions by hand instead of changing `MICRO_VERSION`.
- Using `source: "./"` to make a broad entry and accidentally shipping every pooled command and agent.
