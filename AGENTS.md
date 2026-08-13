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
- `commands/<bundle>/`, `hooks/<set>/{hooks.json,scripts/}`, `instructions/`,
  `instructions/<bundle>/` — remaining pools. The flat `instructions/*.md`
  files are generic (Copilot-style) guidance; **bundle-owned** instructions live in a
  scoped `instructions/<bundle>/` subdir, mirroring `commands/<bundle>/`. Never symlink
  the whole `instructions/` pool into a bundle or agent dir — that ships every unrelated
  file and silently breaks when the flat pool is repurposed. Pool content whose only
  consumer is a parked bundle stays put — the pools generate no marketplace entries,
  so an unused pool dir costs nothing and keeps the parked bundle revivable.
  There is no `mcp/` pool: `ludus-toolkit` vendors its MCP server in-tree at
  `plugins/ludus-toolkit/mcp/ludus/`.
- `plugins/<name>/` — bundle manifests + symlinks (one dir per bundle). Exception:
  `plugins/superpowers/` is a **vendored** third-party bundle (obra/superpowers, MIT) —
  real files, no pool symlinks, and its skills get no micro-entries. Update it by
  re-syncing `skills/` + `hooks/` from upstream and aligning the version in its `plugin.json`.
  Its `RELEASE-NOTES.md` is pinned to the vendored version — diff it against upstream's
  to detect drift. A `.vendored` marker file exempts a bundle from this repo's
  release-notes discipline; never write local entries into a vendored bundle's notes.
- `.claude-plugin/marketplace.json` — **generated**; never hand-edit (see below)
- `wip/plugins/<name>/` — bundles withdrawn from the marketplace while they are
  reworked. Same layout as `plugins/`, one extra `../` in every pool symlink. A bundle
  is withdrawn by moving its dir here **and** deleting its name from `BUNDLE_ORDER`;
  the generator skips listed-but-missing bundles silently, so a move alone leaves
  `marketplace.json` advertising a source that no longer resolves. CI's symlink and
  manifest scans deliberately do not walk `wip/`.
- `docs/specs/` — agent/skill/work-object specifications consumed by `.claude/` tooling; `docs/superpowers/specs/` — dated feature design docs from the planning workflow
- `.claude/` — repo-local dev tooling (agents: `agent-creator`, `plugin-validator`, `skill-reviewer`; commands: `create-agent`, `create-plugin`, `create-skill`, `pin-plugins`; skills for agent/command/hook/mcp/plugin development, marketplace-manifest maintenance, and host portability). Never published.
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
- Every non-vendored bundle keeps a `plugins/<name>/RELEASE-NOTES.md` with one
  `## v<version> (<date>)` heading per released version, matching `plugin.json`
  exactly. **Bump the version and add the entry in the same edit.** An entry must say
  *why* a change was made, not just what changed — see the `release-notes` skill.
  Enforced mechanically by `hooks/steward/scripts/release-notes-audit.py`; the
  "does it actually explain why" judgment is the `marketplace-maintainer` agent's.
- `repository` in every plugin.json points at `https://github.com/dotknewt/awesome-agency`.
- Every agent must declare `model` explicitly, as a full model ID — never a bare
  tier alias or `inherit`. Omitting the field defaults it to `inherit` silently,
  which makes a deliberate choice indistinguishable from an oversight, and a bare
  alias has the same problem one level down: it resolves to whatever Claude Code
  currently maps that tier to, so the agent's behavior isn't reproducible from the
  file alone. The decision procedure is the `agent-model-assignment` skill
  (`skills/agent-model-assignment/SKILL.md`): rule out a Haiku-class pin on hard
  constraints (200K context, Feb 2025 cutoff) first, then on tool-loop length, then
  match task shape — then pin today's full ID for the chosen tier. Where the pinned
  model supports adjustable reasoning effort, state the intended level alongside it.
  Record the reason in the description or a body comment. `.github/scripts/check-agent-models.py`
  enforces that the field is present — never the value (`--list` prints current
  assignments).
- Skill/agent content must reference its own aux files relative to the skill dir,
  or via `${CLAUDE_PLUGIN_ROOT}/...` for anything at plugin-root level. If an agent
  needs pool content (instructions, skills), symlink it into `agents/<name>/` so the
  micro-install stays self-contained. The same applies to a micro-installable skill:
  `${CLAUDE_PLUGIN_ROOT}` resolves to the *entry's* source dir, so shared content must
  be symlinked into **every** source that references it (e.g. `instructions/` exists
  under `wip/plugins/github-toolkit/`, `agents/issue-filer/`, and `skills/github-workflow/`).
  `.github/scripts/check-plugin-root-refs.py` enforces this.
- `claude plugin install` caches by `<name>/<version>` — a source change without a
  version bump may report "already installed" without re-fetching. Verify with
  explicit `uninstall` + `install`.
- Refresh a live install with `claude plugin marketplace update awesome-agency`.

## Host portability (Claude Code + Copilot CLI)

Both are supported install targets. GitHub Copilot CLI reads this repo's
`.claude-plugin/marketplace.json` and dereferences pool symlinks at install time exactly
as Claude Code does — verified against a real install cache, and contrary to GitHub's own
documentation. Treat observed behavior as authoritative over vendor docs here.

`.github/host-compat.json` is the machine-readable source of truth for what each host
honors; `.github/scripts/check-host-compat.py` derives every check from it and runs in CI
over **each marketplace entry**, so micro-installs are covered too. Add a capability to the
matrix, never to the script. `--list` prints the current posture; `--strict` treats warnings
as errors. Waive a specific artifact via `known_exceptions` in the matrix rather than
inventing new frontmatter keys — exceptions belong somewhere reviewable.

Severity follows one rule: a bundle that is **broken** in a host fails; one that is merely
**degraded** reports. What Copilot silently drops:

- **`model:`** — no value pinned here routes Claude Code's own session model on Copilot; it
  falls back to whatever the calling session is using, with only a log line. Keep the pinned
  full ID anyway (both hosts read the same `agents/*.md`, so no per-host value is possible),
  but **an agent must be correct at any model** — never rely on a cheap model for
  correctness, and never advertise a model-dependent benefit in agent prose without
  qualifying it as Claude-only. The checker flags exactly that combination. See
  `docs/TODO.md` for the deferred fix.
- **`disable-model-invocation`** — an explicit-invocation-only skill becomes auto-invocable.
  State the constraint in the skill **body** too, so the model self-restricts.
- **`color:`** — cosmetic, ignored with a warning.
- **Slash commands** — Copilot has no `commands/` concept; skills fill that role, so every
  shipped command needs a skill counterpart or a declared exception.
- **Bundle-local `.mcp.json`** — read as project config, not auto-started; document manual
  setup in the bundle README.
- **Hook events** — Copilot accepts PascalCase names as a compatibility mode but supports a
  smaller set. Stay within `shared_hook_events` in the matrix.

`${CLAUDE_PLUGIN_ROOT}` support in Copilot is **unverified** (docs say no; the vendored
superpowers `SessionStart` hook suggests otherwise). It warns rather than fails.

Copilot Chat in VS Code is a **separate surface from Copilot CLI** and is not covered by
the matrix above — its `runSubagent` tool was observed hard-erroring ("model not found")
on an unrecognized `model:` value, unlike Copilot CLI's silent session-model fallback.
Do not assume the "degraded, not broken" characterization above extends to it. See
`docs/TODO.md`'s Copilot model-selection entry.

A `.vendored` bundle is exempt from the *authoring* rules above (it follows upstream's
conventions), but is still checked for host-installability facts — hook events, bundled MCP,
and `${CLAUDE_PLUGIN_ROOT}` — because those decide whether its code runs in a user's session.

## Validation

- CI: `.github/workflows/validate.yml` — generator drift check, marketplace shape
  (jq), source-path existence, broken-symlink scan (`find plugins agents -xtype l`),
  `${CLAUDE_PLUGIN_ROOT}` reference resolution
  (`.github/scripts/check-plugin-root-refs.py`, run per marketplace entry so
  micro-installs are covered too), agent model declarations
  (`.github/scripts/check-agent-models.py`), cross-host installability
  (`.github/scripts/check-host-compat.py`, also per marketplace entry),
  `plugin.json` validation and SKILL.md frontmatter
  validation via `hooks/hooks-toolkit/scripts/validate-{plugin-json,skill-frontmatter}.sh`,
  and release-notes coverage via `hooks/steward/scripts/release-notes-audit.py`
  (`--all` on every run; `--base <pr-base>` on PRs, to catch a changed bundle that
  skipped its version bump).
- Locally: `claude plugin validate .` for a quick manifest check.

## No build or test step

There is no top-level build, lint, or test command beyond the CI workflow above.
