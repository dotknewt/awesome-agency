# awesome-agency

dotKnewt's Claude Code plugin marketplace — one repo holding every skill, agent,
command, and hook, organized awesome-copilot-style: shared component pools at the
top level, with plugins as thin bundles that reference them.

```
/plugin marketplace add dotknewt/awesome-agency
```

## Install

**A bundle** (curated set of skills/agents/commands/hooks):

```
claude plugin install steward@awesome-agency
```

**A single skill** (most shipped skills are individually installable):

```
claude plugin install tdd@awesome-agency
```

**A single agent** (suffix `-agent`):

```
claude plugin install ember-agent@awesome-agency
```

Installing a bundle plus one of its skills standalone loads that skill twice
(once per plugin namespace) — harmless, but avoid it.

## Layout

| Directory | Contents |
|---|---|
| `skills/` | All skills, one directory each (`<name>/SKILL.md`). `skills/in-progress/` holds unshipped drafts. Most shipped skills are individually installable. |
| `agents/` | All agents, one directory each (`<name>/<name>.md`, plus symlinked dependencies so single-agent installs are self-contained). |
| `commands/` | Slash-command definitions, one subdirectory per owning bundle. |
| `hooks/` | Hook sets — `<set>/hooks.json` + `<set>/scripts/`. |
| `instructions/` | Reference instruction docs used by agents/commands. |
| `plugins/` | Bundle definitions: `.claude-plugin/plugin.json`, README, and symlinks into the pools above. Claude Code dereferences the symlinks at install time. |
| `wip/plugins/` | Parked bundles, withdrawn from the marketplace while they are reworked. Same layout as `plugins/`, but nothing here is installable. |
| `docs/specs/` | Agent/skill/work-object specifications used by the dev tooling. |
| `docs/superpowers/specs/` | Dated feature design docs from the planning workflow. |
| `.claude/` | Repo-local development tooling (not distributed). |

## Bundles

| Plugin | What it does |
|---|---|
| `steward` | Repo stewardship — `/maintain` drift-audit orchestrator with read-only maintainer agents for docs, instructions, schemas, and conventions, plus skills that audit/revise/restructure AGENTS.md, scaffold conventions, and keep docs/STATE.md current. |
| `docker-toolkit` | Multi-stage Dockerfiles and MCP-server containerization. |
| `python-mcp-development` | Python MCP server development with FastMCP guidance, generation, and best-practice instructions. |
| `ludus-toolkit` | Ludus cyber-range skills + bundled MCP server. |
| `superpowers` | Vendored [obra/superpowers](https://github.com/obra/superpowers) (MIT) — brainstorm → plan → subagent-driven TDD → review, with a SessionStart skill injector. |
| `project-workflow` | Spec-gap interview before any code — `project-manager` sequences `project-spec` (goal/scope/non-goals), `project-verify` (measurable criteria + external signals), and `project-environment` (AGENTS.md/KB/skill/guardrail gaps with drafted hooks) into `specs/<slug>/`, human-signed-off at each checkpoint. |

`engineering-toolkit`, `github-toolkit`, `hooks-toolkit`,
`work-objects-toolkit`, and `extension-audit` are parked under `wip/plugins/`
and are no longer installable; `agent-doublecheck` was retired in favour of the
standalone `doublecheck-agent` entry. The skills those bundles carried are still
individually installable from the pools.

`work-object-guard` and `extension-audit` are the skills without standalone
entries — they depend on scripts or hooks shipped by parked bundles, so they
stay unshipped until those bundles return.
Similarly, prefer installing `steward` over the standalone `maintain`
skill — the orchestrator dispatches the five maintainer agents that only ship
with the bundle.

## Contributing / maintaining

- Add a skill: create `skills/<name>/SKILL.md`, then run
  `.github/scripts/generate-marketplace.py` to regenerate the manifest
  (every pool item gets a micro-entry automatically).
- Add an agent: create `agents/<name>/<name>.md`, regenerate.
- Change bundle membership: add/remove symlinks under `plugins/<name>/`,
  bump the version in its `plugin.json`, regenerate.
- CI (`.github/workflows/validate.yml`) fails on stale manifests, broken
  symlinks, invalid `plugin.json`, and malformed skill frontmatter.

Formerly this marketplace aggregated three sibling repos
(`dotknewt/skills`, `dotknewt/agents`, `dotknewt/toolkits`); their content now
lives here and the old repos are archived. If you still have the old
`dotknewt-*` marketplaces added, remove them and reinstall from
`awesome-agency`.
