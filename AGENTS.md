# AGENTS.md

This file provides guidance to AI agents (Claude Code, Codex, Cursor, etc.) when working with code in this repository.

# awesome-agency

`awesome-agency` is dotKnewt's single-repo Claude Code plugin marketplace. All distributable
content lives here in shared top-level pools; plugins are thin bundles over those
pools. The former sibling repos (`dotknewt/skills`, `dotknewt/agents`,
`dotknewt/toolkits`) were consolidated into this repo and archived.

## Architecture (load-bearing — verified against Claude Code behavior)

Two distribution mechanisms coexist in `.claude-plugin/marketplace.json`:

1. **Bundles** — `plugins/<name>/` contains a real `.claude-plugin/plugin.json`
   plus **symlinks** into the top-level pools (`skills/<s>`, `agents/<a>.md`,
   `commands` → `../../commands/<name>`, `hooks/hooks.json`, `scripts`,
   `.mcp.json`). Claude Code dereferences symlinks into real files at install
   time, and the install cache contains only the plugin directory. Marketplace
   entries for bundles are minimal (`source: "./plugins/<name>"`, no version —
   `plugin.json` is authoritative).
   Two symlink rules learned the hard way (live-source loading skips
   **file-level** symlinks during default directory scans, while directory
   symlinks and direct file reads work):
   - Agents MUST be listed explicitly in the bundle's `plugin.json`
     (`"agents": ["./agents/<a>.md", ...]`) — custom-file loading follows
     symlinks; the default `./agents/` scan does not.
   - The commands pool is per-bundle (`commands/<bundle>/*.md`) and each bundle
     symlinks the whole directory (`plugins/<name>/commands → ../../commands/<name>`)
     so the default scan walks real files through a directory symlink.
2. **Micro-entries** — every skill and agent is individually installable via
   inline entries with narrow sources: `{name: "<skill>", source: "./skills/<skill>",
   strict: false}` and `{name: "<agent>-agent", source: "./agents/<agent>",
   strict: false, agents: ["./<agent>.md"]}`. The agents pool is dir-per-agent
   (`agents/<name>/<name>.md`) for exactly this reason.

**Do not** create marketplace entries with `source: "./"` — Claude Code
unconditionally default-scans `./agents/` and `./commands/` at the plugin source
root (empty arrays do not suppress; the `commands` field is additive), so a
repo-root source would absorb every pooled agent and command. Also: entry-level
`hooks` must be an inline object (file-path form fails to load), and shipped
content references its own files via `${CLAUDE_PLUGIN_ROOT}/...`.

## Repository layout

- `skills/` — all skills (`<name>/SKILL.md`); `skills/in-progress/` = unshipped drafts, never listed in the marketplace
- `agents/` — dir-per-agent (`<name>/<name>.md` + symlinked deps so solo installs are self-contained)
- `commands/`, `hooks/<set>/{hooks.json,scripts/}`, `instructions/`, `mcp/ludus/` — remaining pools
- `plugins/<name>/` — bundle manifests + symlinks (one dir per bundle). Exception:
  `plugins/superpowers/` is a **vendored** third-party bundle (obra/superpowers, MIT) —
  real files, no pool symlinks, and its skills get no micro-entries. Update it by
  re-syncing `skills/` + `hooks/` from upstream and aligning the version in its `plugin.json`.
  Its `RELEASE-NOTES.md` is pinned to the vendored version — diff it against upstream's
  to detect drift.
- `.claude-plugin/marketplace.json` — **generated**; never hand-edit (see below)
- `docs/specs/` — agent/skill/work-object specifications consumed by `.claude/` tooling; `docs/superpowers/specs/` — dated feature design docs from the planning workflow
- `.claude/` — repo-local dev tooling (agents: `agent-creator`, `plugin-validator`, `skill-reviewer`; commands: `create-agent`, `create-plugin`, `create-skill`, `pin-plugins`; skills for agent/command/hook/mcp/plugin development). Never published.
- `docs/TODO.md` — backlog notes; `docs/STATE.md` — session bookmarks (stub unless an effort is active)

## marketplace.json is generated

Run `.github/scripts/generate-marketplace.py` after any pool or bundle change;
CI runs it with `--check` and fails on drift. Exclusions/renames (bundle-bound
skills like `work-object-guard`, and any skill whose bare name collides with a
bundle name) are constants at the top of that script. New bundles must also be added
to `BUNDLE_ORDER` in that script — the generator hard-fails on any
`plugins/<name>/` directory not listed there (the list also controls marketplace
entry order).

The marketplace `"name"` is `awesome-agency` — installs are keyed as
`<plugin>@<marketplace>`.
Changing it requires reinstalling existing marketplace plugins under the new
identifier.

## Conventions

- Bundle versions live ONLY in `plugins/<name>/.claude-plugin/plugin.json`. Bump
  on any change to the bundle's members or metadata. Micro-entries use a flat
  `1.0.0` (bump `MICRO_VERSION` in the generator if a coordinated refresh is needed).
- `repository` in every plugin.json points at `https://github.com/dotknewt/awesome-agency`.
- Skill/agent content must reference its own aux files relative to the skill dir,
  or via `${CLAUDE_PLUGIN_ROOT}/...` for anything at plugin-root level. If an agent
  needs pool content (instructions, skills), symlink it into `agents/<name>/` so the
  micro-install stays self-contained.
- `claude plugin install` caches by `<name>/<version>` — a source change without a
  version bump may report "already installed" without re-fetching. Verify with
  explicit `uninstall` + `install`.
- Refresh a live install with `claude plugin marketplace update awesome-agency`.

## Validation

- CI: `.github/workflows/validate.yml` — generator drift check, marketplace shape
  (jq), source-path existence, broken-symlink scan (`find plugins agents -xtype l`),
  `plugin.json` validation and SKILL.md frontmatter validation via
  `hooks/hooks-toolkit/scripts/validate-{plugin-json,skill-frontmatter}.sh`.
- Locally: `claude plugin validate .` for a quick manifest check.

## No build or test step

There is no top-level build, lint, or test command beyond the CI workflow above.
