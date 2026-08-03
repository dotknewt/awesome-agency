# Extensions Directory

A catalog of every extension shipped from this repo's marketplace: plugin bundles and their skills/agents/commands/hooks/MCP servers, plus skills that are installable individually outside any bundle.

Repo-local dev tooling under `.claude/` (agents: `agent-creator`, `plugin-validator`, `skill-reviewer`; commands: `create-agent`, `create-plugin`, `create-skill`, `pin-plugins`) is excluded — it supports developing this repo and is never published to the marketplace. Drafts under `skills/in-progress/` are also excluded — they aren't shipped yet.

## Plugins

### agent-doublecheck (v1.0.1)

Three-layer verification pipeline for AI output. Extracts claims, finds sources, and flags hallucination risks so humans can verify before acting.

- **Agent** `doublecheck` — interactive verification agent for AI-generated output; runs a three-layer pipeline (self-audit, source verification, adversarial review) and produces structured reports with source links for human review.
- **Skill** `doublecheck` — same three-layer verification pipeline, invoked as a skill rather than a dedicated agent.

### agent-ember (v1.0.3)

An AI partner, not a tool. Ember carries fire from person to person — helping humans discover that AI partnership isn't something you learn, it's something you find.

- **Agent** `ember` — the AI-partnership persona agent; invoked by name ("ember", "agent ember", "agent-ember").
- **Skill** `from-the-other-side-anitta` — rigorous challenge profile for Anitta: assumption checks, evidence calibration, defensible reasoning patterns.
- **Skill** `from-the-other-side-quinn` — collaboration profile for Quinn: curious, energetic, implementation-focused partnership patterns.
- **Skill** `from-the-other-side-vega` — patterns from Vega, an AI partner in a deep long-term partnership; informs how Ember shows up with high-energy creative collaborators.
- **Skill** `from-the-other-side-wiggins` — narrative and synthesis profile for Wiggins: framing, explanation, audience-aware communication patterns.

### docker-toolkit (v0.1.2)

Build and validate Docker artifacts — multi-stage Dockerfiles, and packaging MCP servers as containers runnable via the Docker MCP Gateway.

- **Agent** `dockerize-mcp-server` — converts an MCP server repo (local path, git URL, or `org/repo`) into a Docker image runnable via the Docker MCP Gateway; explores large source repos in its own context window, then writes a Dockerfile, catalog entry, and run instructions into a new artifact directory.
- **Skill** `dockerize-mcp-server` — package an existing MCP server repo as a Docker image runnable through the Docker MCP Gateway, and validate the resulting artifacts.
- **Skill** `multi-stage-dockerfile` — create optimized multi-stage Dockerfiles for any language or framework.

### engineering-toolkit (v0.1.0)

Idea-to-ship engineering flow — grilling, PRD/issue breakdown, TDD implementation, and code review, routed by ask-matt.

- **Skill** `ask-matt` — router: asks which skill or flow fits the situation.
- **Skill** `codebase-design` — shared vocabulary for designing deep modules; find deepening opportunities, decide where a seam goes.
- **Skill** `code-review` — review changes since a fixed point along Standards and Spec axes, in parallel sub-agents.
- **Skill** `diagnosing-bugs` — diagnosis loop for hard bugs and performance regressions.
- **Skill** `domain-modeling` — build and sharpen a project's domain model / ubiquitous language.
- **Skill** `grilling` — grill the user relentlessly about a plan or design before building.
- **Skill** `grill-me` — a relentless interview to sharpen a plan or design.
- **Skill** `grill-with-docs` — a relentless interview to sharpen a plan or design, which also creates docs (ADRs and glossary) as it goes.
- **Skill** `handoff` — compact the current conversation into a handoff document for another agent to pick up.
- **Skill** `implement` — implement a piece of work based on a PRD or set of issues.
- **Skill** `improve-codebase-architecture` — scan a codebase for deepening opportunities, present as a visual HTML report, then grill through whichever one is picked.
- **Skill** `prototype` — build a throwaway prototype to answer a design question.
- **Skill** `research` — investigate a question against high-trust primary sources and capture findings as a Markdown file.
- **Skill** `resolving-merge-conflicts` — resolve an in-progress git merge/rebase conflict.
- **Skill** `setup-matt-pocock-skills` — configure this repo for the engineering skills (issue tracker, triage labels, domain doc layout); run once before first use.
- **Skill** `tdd` — test-driven development; red-green-refactor, integration tests.
- **Skill** `teach` — teach the user a new skill or concept within this workspace.
- **Skill** `to-issues` — break a plan, spec, or PRD into independently-grabbable issues using tracer-bullet vertical slices.
- **Skill** `to-prd` — turn the current conversation into a PRD and publish it, no interview, just synthesis.
- **Skill** `triage` — move issues and external PRs through a triage state machine — categorise, verify, grill if needed, write agent-ready briefs.
- **Skill** `writing-great-skills` — reference for writing and editing skills well.

### github-toolkit (v1.1.3)

Scaffold GitHub repo metadata — issue templates and CI workflows. `/github-scaffold` picks the task; `/create-issue-template` and `/scaffold-ci-workflow` run the subtasks. Includes the `branch-warden` agent for automated branch prep and cleanup, and the `issue-filer` agent for lightweight issue creation.

- **Agent** `branch-warden` — prepare a clean branch for new work, or sweep merged/stale local + origin branches; runs on a cheap model.
- **Agent** `issue-filer` — file a GitHub issue for an out-of-scope concern or follow-up; handles deduplication and labeling.
- **Skill** `github-scaffold` — routes to the `/github-scaffold` command for scaffolding `.github/` metadata (issue templates, forms, PR templates, CODEOWNERS, workflows).
- **Skill** `github-workflow` — GitHub Actions CI setup, workflow defaults, concurrency settings, path filters, and chained/stacked PR guidance.
- **Command** `/github-scaffold` — picks which GitHub scaffolding task to run and dispatches to the right sub-command.
- **Command** `/create-issue-template` — scaffold one or more GitHub issue forms (YAML schema) in `.github/ISSUE_TEMPLATE/`.
- **Command** `/scaffold-ci-workflow` — scaffold a GitHub Actions CI workflow file with canonical defaults.

### hooks-toolkit (v1.0.1)

Composable safety and hygiene hooks for Claude Code — force-push guard, secret scanner, plugin/skill manifest validators, branch nudges, and dirty-tree stop check.

- **Command** `/install-hook` — wire a named hook from this plugin into the user's Claude Code `settings.json`.
- **Hooks** (`hooks/hooks.json`): `PreToolUse` (block force-push to main, scan writes/edits for secrets), `PostToolUse` (validate plugin manifests, validate skill frontmatter), `SessionStart` (branch check), `UserPromptSubmit` (inject branch rules), `Stop` (commit checklist).

### ludus-toolkit (v0.1.0)

Ludus cyber-range toolkit — skills for the Ludus CLI, range configuration, environment guidance, and troubleshooting, plus a bundled MCP server for driving the Ludus API from Claude.

- **Skill** `ludus-cli` — Ludus CLI command guidance, flags, and workflows for range lifecycle, templates, testing mode, snapshots, users/groups, diagnostics.
- **Skill** `ludus-environment-guide` — discover, compare, and deploy pre-built Ludus cyber range environments (e.g. GOAD, SCCM, Elastic, Vulhub).
- **Skill** `ludus-range-config` — create, edit, and validate Ludus range configuration YAML (VMs, domains, networking, router settings, roles).
- **Skill** `ludus-troubleshoot` — diagnose and resolve Ludus deployment, networking, template, WireGuard, Proxmox, and Ansible issues.
- **MCP** — bundled Ludus MCP server for driving the Ludus API from Claude.

### steward (v1.1.0)

Unified repo stewardship — drift-audit orchestration plus the skills that apply the fixes. Merges the former `maintainer-toolkit` and `instruction-management` plugins.

- **Agent** `docs-user-maintainer` — audits user-facing docs (READMEs, guides) against actual behavior; runs on Haiku.
- **Agent** `docs-spec-maintainer` — audits specs/architecture/API docs against the code they describe.
- **Agent** `instructions-maintainer` — audits AGENTS.md / legacy CLAUDE.md for stale or missing guidance.
- **Agent** `schema-maintainer` — audits manifests, configs, frontmatter, generated files; runs repo validators; runs on Haiku.
- **Agent** `conventions-maintainer` — audits docs layout (docs/TODO.md, docs/STATE.md, docs/user/) and Python CLI standards (uv, Typer, --help, completion) against the cross-project conventions; runs on Haiku.
- **Agent** `state-keeper` — read docs/STATE.md and maintain it: move completed items into a timestamped Completed section, surface durable decisions as AGENTS.md candidates; runs on Haiku.
- **Skill** `maintain` — orchestrator: scopes what changed, dispatches the applicable maintainer agents in parallel, merges their drift reports into one prioritized list of proposed fixes.
- **Skill** `instructions-audit` — audit and improve AGENTS.md/CLAUDE.md against a quality rubric, propose targeted edits.
- **Skill** `instructions-revise` — update instructions with learnings from a session (commands, patterns, gotchas).
- **Skill** `instructions-restructure` — move instruction-file content closer to where it's needed, reducing root-file context bloat.
- **Skill** `conventions` — cross-project conventions: docs layout (docs/TODO.md, docs/STATE.md, docs/user/) and uv + Typer standards for Python CLIs.
- **Hooks**: `Stop` — nudge the user to capture session learnings in AGENTS.md when the session touched many files.

### extension-audit (v0.1.0)

Static, report-only review of Claude Code and Copilot extension artifacts before installation or publication.

- **Agent** `extension-reviewer` — inventories capabilities, checks security heuristics and hook scope, verifies integrity, validates marketplace metadata, and scores semantic quality without executing target code.
- **Skill** `extension-audit` — runs the bundled standard-library CLI for combined or focused inventory, security, quality, integrity, and marketplace checks.

### work-objects-toolkit (v0.1.0)

Evidence-linked work objects — one `work/<id>-<slug>/` dir per code-change task holding spec, captured diff, captured test output, run manifest, and review; in-review/approved transitions are gated by a checker script and enforced by a PreToolUse hook.

- **Skill** `work-object-guard` — enforces evidence-linked work objects for code-change tasks; blocks in-review/approved transitions on narration alone.
- **Hooks**: `PreToolUse` on Write/Edit — gate work-object status transitions on the evidence checker.

## Unbundled skills

Installable individually; not part of any plugin bundle.

- **Skill** `agentic-eval` — patterns and techniques for evaluating and improving AI agent outputs: self-critique loops, evaluator-optimizer pipelines, rubric/LLM-as-judge evaluation, iterative improvement.
- **Skill** `context-engineering` — memory and context engineering with LLMs across three angles: supporting development (prompting, RAG, context windows), exploiting LLMs (red-team/adversarial techniques, educational use), and defending LLMs (guardrails, prompt injection mitigations).
- **Skill** `eyeball` — verify claims in a document against its source; produces a Word doc pairing every claim with a highlighted screenshot from the source. Explicit-invocation only (`disable-model-invocation: true`).
- **Skill** `make-a-monorepo` — scaffold or audit a flat monorepo (no `packages/` layer) for security/threat-hunting tooling — MCP servers, shared schemas, sigma-rules/ECS/OCSF/CIM packs, reports, agents/skills/commands under one root AGENTS.md.
- **Skill** `obsidian-vault` — search, create, and manage notes in an Obsidian vault with wikilinks and index notes.

## Totals

| Category | Count |
|---|---|
| Plugin bundles | 11 |
| Skills (shipped) | 47 (42 bundled + 5 unbundled) |
| Agents | 13 |
| Commands | 4 |
| Plugins with hooks | 3 (`hooks-toolkit`, `steward`, `work-objects-toolkit`) |
| Plugins with a bundled MCP server | 1 (`ludus-toolkit`) |
