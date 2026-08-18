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
  to detect drift; never write local entries into it. A `.vendored` marker file
  redirects local-change entries to `LOCAL-CHANGES.md` instead — it does **not**
  exempt the bundle from bumping `plugin.json`'s version on every local content
  change (a source change without a bump can leave a cached install unrefreshed).
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
  A `.vendored` bundle follows the same bump-and-entry-in-the-same-edit rule, just
  against `LOCAL-CHANGES.md` instead of `RELEASE-NOTES.md` (which stays pinned to
  upstream). Enforced mechanically by `hooks/steward/scripts/release-notes-audit.py`
  for both notes files; the "does it actually explain why" judgment is the
  `marketplace-maintainer` agent's.
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
This is a distinct exemption from the release-notes/version-bump one in Conventions above:
a `.vendored` bundle still must bump `plugin.json` and record the entry in `LOCAL-CHANGES.md`.

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

## Project Memory

Durable project memory lives in `vault/` (Markdown + flat YAML frontmatter, Obsidian-compatible), provided by the `vault-memory`
plugin (`plugins/vault-memory/`). Auto-memory is OFF: nothing about this project is stored in user-global memory, and personal
preferences never go into the vault (they belong in `~/.claude/`).

## Map — the `obsidian` MCP server is rooted at `vault/`: MCP path `kb/x.md` == native path `vault/kb/x.md`
- `vault/INDEX.md` — root map (≤150 lines). Injected at SessionStart. Start here, not from search.
- `vault/kb/` — atomic project knowledge (`kind: fact|convention|gotcha|pattern|concept`), `kb/decisions/adr-NNNN-*.md` (ADRs), `kb/moc-<area>.md` (hubs)
- `vault/docs/` — human-facing docs (`kind: howto|reference|explanation|tutorial`, Diátaxis)
- `vault/sources/` — one note per external source: provenance + verbatim excerpts + claims; excerpts immutable after capture
- `vault/plans/` (plan-mode output) · `vault/sessions/` (hook-generated session notes) · `vault/archive/` (retired notes) — HISTORY:
  never read them by default; when continuing prior work read only the last session note's curated sections + the active plan.
- Conventions (types, frontmatter, naming, links, lifecycle): skill `vault-conventions` (`plugins/vault-memory/skills/vault-conventions/SKILL.md`).
  It auto-loads when you touch `vault/kb|docs|sources|archive` with native tools; when writing through MCP tools, invoke/read it first.

## Protocol
1. Index first, then search. Before non-trivial work run `/vault-find "<one-sentence task goal> + 3–6 key terms"` (identifiers, file
   paths, error strings, domain nouns; add `--history` when continuing prior work) — the read-only `vault-librarian` returns a ≤40-line
   briefing. Read at most 3–5 notes yourself, partially where possible (`get_note_outline` → `read_note_lines`). Never bulk-read a folder.
2. Persist with `/vault-save` when: a decision among alternatives was made; a non-obvious repo fact/gotcha/coupling was learned
   (>5 min to rediscover); the user corrected you or repeated a clarification; a repeatable ≥3-step procedure emerged (done ≥2×);
   an external source shaped code or a decision. Search before create · update > create · supersede > overwrite · archive > delete.
3. Never persist: transient state, raw tool output, secrets/tokens/keys, personal preferences, other projects' knowledge,
   anything derivable from code in <1 min, speculation (unless `status: draft` + `confidence: unverified`).
4. Trust but verify: before acting on a kb fact, check its `evidence` (grep the cited path/symbol). Wrong → fix now or set
   `status: needs-review` + `review_note`. Never leave a wrong note silently.
5. Run `/vault-session` before `/compact`, before ending a substantial session, and after finishing a major sub-task.
6. Maintenance is user-run: when the SessionStart briefing reports notes past `review_after`, *mention* it and suggest the user runs
   `/vault-review due` (user-only skill). If asked to review in chat, delegate to the `vault-curator` subagent with the scope and
   whether to apply safe actions. Large sweeps: `/vault-audit` (workflow, proposes only); web research with provenance: `/vault-research`.
   Deletions always need user confirmation (`delete_note` prompts and only `trashMode:"local"` is allowed).
7. Delegate to keep context clean: `vault-librarian` (retrieval → briefing), `vault-researcher` (web → `sources/`),
   `vault-curator` (review/merge/archive). Subagents return digests and paths, never raw notes.
8. Budget: briefing ≤1.5k tokens + ≤4k tokens of note content per task; prefer 3 strong notes over 10 weak (distractors hurt).
9. When compacting, preserve: decisions made, open questions, next step, and the vault paths touched; drop tool outputs.

## Tools — which for what
- Ranked recall: `mcp__obsidian__search_notes {query, pathPrefix:"kb"|"docs"|"sources", excludePaths:["archive","sessions","plans","_templates","_bases"], limit:15}`
  — substring-OR + BM25, no stemming → run 2–3 phrasings; `searchFrontmatter:true, searchContent:false` searches YAML text (tags/status/aliases).
- Exact strings, identifiers, backlinks (`\[\[basename`), enumeration (`Grep '^description:' vault/kb`, `Glob vault/**/*.md`): native Grep/Glob.
- Read: `get_frontmatter` (cheap triage), `read_multiple_notes` (≤10; `includeContent:false` = frontmatter only), `get_note_outline` + `read_note_lines`, `wiki_link`.
- Write: `write_note` (creates dirs; pass the `frontmatter` object; `overwrite` without it wipes YAML), `update_frontmatter {merge:true}` (arrays are
  replaced wholesale — read first, send the full list; keys can't be deleted), `patch_note` (exact unique string; sees YAML too), `move_note`
  (no link rewrite — patch referrers first), `delete_note` only `trashMode:"local"`. Never `manage_tags add/remove` (promotes body `#tokens`); `manage_tags list` is fine.
- Code, `.claude/**`, `plugins/**`, `AGENTS.md`: native tools only (dot-paths and everything outside `vault/` are invisible to the MCP server).
- Lint the vault any time: `node plugins/vault-memory/hooks/vault-lint.mjs --all` (or `--all --json`). Hooks validate every write into `vault/`
  (hard violations are denied, schema issues are warned) — fix warnings immediately.
