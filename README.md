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
claude plugin install engineering-toolkit@awesome-agency
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
| `mcp/` | Bundled MCP servers (`mcp/ludus/`). |
| `plugins/` | Bundle definitions: `.claude-plugin/plugin.json`, README, and symlinks into the pools above. Claude Code dereferences the symlinks at install time. |
| `docs/specs/` | Agent/skill/work-object specifications used by the dev tooling. |
| `docs/superpowers/specs/` | Dated feature design docs from the planning workflow. |
| `.claude/` | Repo-local development tooling (not distributed). |

## Bundles

| Plugin | What it does |
|---|---|
| `engineering-toolkit` | Idea-to-ship engineering flow — grilling, PRD/issue breakdown, TDD, code review. |
| `steward` | Repo stewardship — `/maintain` drift-audit orchestrator with read-only maintainer agents for docs, instructions, schemas, and conventions, plus skills that audit/revise/restructure AGENTS.md, scaffold conventions, and keep docs/STATE.md current. |
| `github-toolkit` | Issue templates, CI scaffolding, branch-warden + issue-filer agents. |
| `hooks-toolkit` | Safety/hygiene hooks — force-push guard, secret scanner, manifest validators. |
| `docker-toolkit` | Multi-stage Dockerfiles and MCP-server containerization. |
| `python-mcp-development` | Python MCP server development with FastMCP guidance, generation, and best-practice instructions. |
| `ludus-toolkit` | Ludus cyber-range skills + bundled MCP server. |
| `work-objects-toolkit` | Evidence-linked work objects with gated status transitions. |
| `agent-doublecheck` | Three-layer verification pipeline for AI output. |
| `agent-ember` | Ember, an AI-partnership persona agent. |
| `extension-audit` | Static, report-only security, capability, integrity, marketplace, and semantic-quality audits for extension artifacts. |

`work-object-guard` and `extension-audit` are the skills without standalone
entries — they depend on bundle-shipped scripts or hooks, so install their
respective bundles instead.
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
