> ## Canonical documentation
> Fetch the current upstream reference at: https://code.claude.com/docs/en/sub-agents
> This file documents the format as observed in this repository; the upstream page is authoritative for edge cases and version-gated behavior.

# Specification

> The complete format specification for Claude Code subagents ("agents"), as used across this repository's project-level tooling (`.claude/agents/`) and its distributable content (the `agents/<name>/<name>.md` pool, symlinked into bundles at `plugins/*/agents/`).

## Directory structure

An agent is a single Markdown file with YAML frontmatter. There is no accompanying directory required — unlike a skill, an agent does not bundle `scripts/`, `references/`, or `assets/` alongside it. Everything the agent needs is either in its frontmatter (tool access, model, hooks) or in its own body text.

Where the file lives determines its scope:

| Location | Scope | Used for |
| --- | --- | --- |
| `.claude/agents/*.md` | Current project only | Dev-tooling agents specific to this repo, e.g. `.claude/agents/agent-creator.md`, `.claude/agents/plugin-validator.md`, `.claude/agents/skill-reviewer.md` |
| `~/.claude/agents/*.md` | Every project on the machine | Personal agents not tied to any one repo (not used in this repo, but supported) |
| `agents/<agent-name>/<agent-name>.md` | Shared pool (canonical source) | Every distributable agent, e.g. `agents/branch-warden/branch-warden.md`, `agents/ember/ember.md`. Each is published as a standalone `<name>-agent` marketplace micro-entry by `.github/scripts/generate-marketplace.py`. |
| `plugins/<plugin>/agents/*.md` | Wherever the plugin is enabled | Symlinks into the pool, listed **explicitly** in the bundle's `plugin.json` `agents` array (the default directory scan skips file-level symlinks), e.g. `plugins/github-toolkit/agents/branch-warden.md` |

```
.claude/agents/                # project-scoped agents (this repo's own tooling)
├── agent-creator.md
├── plugin-validator.md
└── skill-reviewer.md

agents/<agent-name>/           # shared pool — canonical source, dir-per-agent
└── <agent-name>.md            # (+ symlinked deps so solo installs are self-contained)

plugins/<plugin>/agents/       # bundle membership — symlinks into the pool
└── <agent-name>.md ⇒ ../../../agents/<agent-name>/<agent-name>.md
```

Both `.claude/agents/` and `~/.claude/agents/` are scanned recursively, so subfolders (e.g. `agents/review/`) are permitted for organization — the subfolder path does not affect how the agent is identified or invoked, since identity comes only from the `name` field. Inside a **plugin's** `agents/` directory, subfolders do matter: they become part of the agent's scoped identifier (see [Invocation](#invocation)).

The filename does not need to match the `name` field, though this repo's convention (seen in every local example) is to name the file `<name>.md`.

## `<agent-name>.md` format

The file must contain YAML frontmatter followed by Markdown content, the same two-part structure as a skill's `SKILL.md`.

### Frontmatter

Only `name` and `description` are required by the canonical spec. Everything else is optional to Claude Code — but this repo additionally **requires `model`** on every agent it ships, enforced in CI. See [Model conventions](#model-conventions).

| Field | Required | Constraints |
| --- | --- | --- |
| `name` | Yes | Unique identifier. Lowercase letters, numbers, and hyphens; must start and end with alphanumeric. This repo's convention: 3–50 characters, 2–4 words. |
| `description` | Yes | Tells Claude when to delegate to this agent. This is the field the harness reads to decide whether to dispatch — see [The description field](#the-description-field). |
| `tools` | No | Restricts the agent to a specific set of tools. Omit to inherit every tool available in the parent conversation. See [Tool restriction syntax](#tool-restriction-syntax). |
| `disallowedTools` | No | Denylist form of the above: inherit everything except the tools listed. Not seen in this repo's local agents, but valid per the canonical spec. |
| `model` | Yes (repo convention) | Which model the agent runs on: this repo requires a full model ID (`inherit`/`sonnet`/`opus`/`haiku` are valid Claude Code syntax but not used here). Optional to Claude Code (defaults to `inherit`), but mandatory here so the choice is deliberate and reviewable. See [Model conventions](#model-conventions). |
| `color` | No | Display color for the agent in the task list/transcript UI. Purely cosmetic — has no effect on behavior. See [Color](#color). |

<Card>
  **Minimal example:**

  ```markdown agent-name.md
  ---
  name: safe-researcher
  description: Research agent with restricted capabilities. Use when a task needs web/codebase lookups but must not modify anything.
  ---
  ```

  **Example with commonly-used optional fields:**

  ```markdown agent-name.md
  ---
  name: branch-warden
  description: Prepare a clean branch for new work, or sweep merged/stale local + origin branches. Invoke before starting an unrelated task to confirm the working branch matches the task.
  model: claude-haiku-4-5-20251001
  tools:
    - Bash
    - Read
  ---
  ```
</Card>

#### `name` field

The required `name` field:

* Uses lowercase letters, numbers, and hyphens only
* Must start and end with an alphanumeric character
* Should be 3–50 characters, typically 2–4 words joined by hyphens
* Must be unique within its scope — if two files in the same scope declare the same name, only one loads

<Card>
  **Valid examples (from this repo):**

  ```yaml
  name: agent-creator
  name: plugin-validator
  name: branch-warden
  name: dockerize-mcp-server
  ```

  **Invalid examples:**

  ```yaml
  name: helper        # too generic, gives Claude no signal about scope
  name: -reviewer      # cannot start with a hyphen
  name: my_agent        # underscores not allowed
  name: ag              # too short
  ```
</Card>

#### `description` field

The required `description` field is the single most important field in the file: it is loaded into context for every registered agent, and it is what the harness compares against the current task to decide whether to delegate. See [The description field](#the-description-field) below for the full convention used in this repo.

#### `tools` field

The optional `tools` field restricts the agent to a specific allowlist. See [Tool restriction syntax](#tool-restriction-syntax).

#### `model` field

The `model` field selects which model the agent runs on. Claude Code treats it as optional; this repo requires it on every agent. See [Model conventions](#model-conventions).

#### `color` field

The optional `color` field is a display hint only — it changes how the agent shows up in the task list and transcript, nothing else.

Canonical values (per the upstream Claude Code docs): `red`, `blue`, `green`, `yellow`, `purple`, `orange`, `pink`, `cyan`.

**Discrepancy worth flagging:** this repo's own `.claude/agents/agent-creator.md` and the `agent-development` skill both use `magenta` instead of `purple`. `magenta` is not in the canonical list above. Treat it as either a historical alias that happens to still render, or a stale value predating a spec change — don't assume it is guaranteed to keep working. When writing a new agent, prefer the canonical `purple` unless you have a reason to match the existing (possibly-stale) local convention.

<Card>
  **Examples seen locally:**

  ```yaml
  color: magenta   # agent-creator.md — see discrepancy note above
  color: yellow    # plugin-validator.md
  color: cyan      # skill-reviewer.md
  ```

  Many agents in this repo (all of the pool agents under `agents/*/`) omit `color` entirely. It has no functional effect, so omitting it is fine.
</Card>

### Body content

The Markdown body after the frontmatter is the agent's **entire system prompt**. Unlike the main Claude Code system prompt, a subagent receives only this text plus basic environment details (working directory, and — unless the agent is one of the built-in `Explore`/`Plan` agents — the project's `AGENTS.md`/`CLAUDE.md` memory files and a git-status snapshot). Write it in second person, addressing the agent directly ("You are...", not "I am...").

There are no format restrictions, but the local examples converge on a common shape:

* An opening line establishing the agent's role/persona
* A **Core Responsibilities** or **Steps** section (numbered)
* Domain-specific process detail (e.g. `plugin-validator.md`'s 10-step validation process, `branch-warden.md`'s two named modes)
* An **Output Format** section describing exactly what the agent should return to its caller
* A **Constraints** or **Edge Cases** section stating what the agent must never do (e.g. `issue-filer.md`: "Do not edit any files"; `state-keeper.md`: "Never read or write `AGENTS.md`")

Keep the system prompt focused. The local examples range from ~40 lines (`issue-filer.md`, `state-keeper.md`) to ~180 lines (`plugin-validator.md`); there is no hard limit, but a single agent should do one job well rather than several jobs adequately.

## The `description` field

The `description` field is loaded into context whenever the agent is registered, so it is the only thing the harness has to decide *whether* to delegate — before any of the body text is read. A vague description ("Helps with code review") gives the harness nothing to match against; a description with concrete trigger phrases and worked scenarios gives it many.

### The `<example>`/`<commentary>` convention

Every agent in `.claude/agents/` in this repo (`agent-creator.md`, `plugin-validator.md`, `skill-reviewer.md`) writes its description as a block scalar containing 2–4 `<example>` blocks:

```
<example>
Context: [situation that should trigger the agent]
user: "[user message]"
assistant: "[response before triggering, if any]"
<commentary>
[why the agent should trigger in this scenario]
</commentary>
assistant: "I'll use the [agent-name] agent to [what it does]."
</example>
```

**This is a repository convention, not a schema requirement.** The canonical Claude Code spec only requires `description` to be a non-empty string — it says nothing about `<example>` tags. The convention traces back to Claude Code's own internal agent-creation prompt (see `.claude/agents/agent-creator.md`'s closing note: "This agent automates agent creation using the proven patterns from Claude Code's internal implementation"), and it has stuck in this repo because it works: a worked example anchors a specific phrasing, a specific context, and a specific outcome all in one place, which gives the harness more surface area to match a real user message against than a single abstract sentence does.

Why concrete examples improve triggering, concretely:

* **Coverage of phrasing variety.** Users describe the same need in different words ("review my skill" vs. "does this look good?" vs. "check skill quality"). Each `<example>` can carry a different phrasing, so the description covers more of the input space than one sentence can.
* **Both reactive and proactive triggering.** An example can show the user explicitly asking, or show the assistant proactively deciding to trigger after some other action (e.g. `plugin-validator.md`'s example: "User finished creating a new plugin" → assistant proactively validates). Writing this out in an example is more reliable than describing it abstractly in prose ("use proactively") because the example makes the shape of the triggering moment explicit.
* **The `<commentary>` states the *why*.** This is not shown to the end user; it exists to make the reasoning behind the trigger explicit for anyone reading or maintaining the agent file later.

Toolkit-plugin agents in this repo (`branch-warden.md`, `issue-filer.md`, `dockerize-mcp-server.md`, `state-keeper.md`) use a simpler, single-paragraph description with no `<example>` blocks — this is also valid, and appropriate for agents that are invoked mostly by name from another agent's prompt rather than auto-triggered from open-ended user phrasing. Use the `<example>` convention when the agent needs to catch varied, unpredictable natural-language phrasing from a human; a plain descriptive paragraph is enough when the agent is a narrow subroutine that a calling agent invokes deliberately and explicitly.

## Tool restriction syntax

The `tools` field is an allowlist. If omitted, the agent inherits every tool available to the parent conversation (including MCP tools). Least privilege is the standard convention: grant only what the agent's job requires.

Three equivalent forms are all valid YAML and all seen in this repo's own agent files:

```yaml
# Comma-separated bare string (the form the canonical docs and the
# Claude Code quickstart wizard both produce)
tools: Read, Grep, Glob

# Inline JSON-style array (used by every agent under .claude/agents/
# in this repo)
tools: ["Write", "Read"]

# YAML block list (used by toolkit-plugin agents, e.g. branch-warden.md,
# state-keeper.md)
tools:
  - Bash
  - Read
```

All three parse to the same underlying list; pick whichever reads best for the number of tools involved (a bare comma-separated string for two or three tools, a block list once the set grows past four or five).

To deny specific tools while inheriting everything else instead of allowlisting, use `disallowedTools` in place of `tools`:

```yaml
disallowedTools: Write, Edit
```

If both fields are set, `disallowedTools` is applied first and `tools` is then resolved against what remains.

To grant unrestricted access, omit `tools` entirely — do not write `tools: "*"` or `tools: All tools`; the absence of the field, not a wildcard value, is what means "all tools" in the canonical spec. (`dockerize-mcp-server.md` shows the pattern for granting broad-but-specific access instead: it lists `Read, Glob, Grep, Write, Edit, Bash` plus four `mcp__MCP_DOCKER__*`-prefixed MCP tools by exact name, rather than granting the whole MCP server.)

## Model conventions

Every agent in this repo **must declare `model` explicitly, as a full model ID.**
Omitting the field is valid Claude Code — it silently means `inherit` — but an
omission is indistinguishable from an oversight, so this repo forbids it.
`.github/scripts/check-agent-models.py` enforces in CI that the field is present. It
deliberately does **not** validate the value — model names change faster than a
checked-in allowlist can track, and a validator that rejects a model released last
week is worse than no validator.

### Accepted values

| Value | Meaning |
| --- | --- |
| A full model ID, e.g. `claude-fable-5`, `claude-haiku-4-5-20251001` | Pins the agent to one exact model. This is the only accepted value in this repo. |

`inherit` and the bare tier aliases (`haiku`/`sonnet`/`opus`/`fable`) are valid Claude
Code syntax but are **not** used here: this repo always pins a full model ID, even
though Anthropic's dateless IDs (e.g. `claude-fable-5`) are pinned snapshots too, not
evergreen pointers, and so need periodic review as models are deprecated. See the
`agent-model-assignment` skill's opening section ("Always pin a full ID; never write a
bare alias or `inherit`") for the rationale.

**Always pin a full model ID.** Nothing checks this value; it is a judgment call
which exact ID to choose (see [Choosing a tier](#choosing-a-tier) below), and the
reason belongs in the file per [Recording the reason](#recording-the-reason).

### Choosing a tier

**The decision procedure lives in the `agent-model-assignment` skill**
(`skills/agent-model-assignment/SKILL.md`) — it is shipped as a skill rather than
written out here so it applies in any repo, not just this one, and so there is one
copy to keep current instead of two. Read it before assigning a model. In outline:

1. **Rule out a Haiku-class pin on hard constraints first.** 200K context (~150K
   words) and a Feb 2025 knowledge cutoff, against 1M and 2026 for every other tier.
   This disqualifies more agents than any reasoning criterion does.
2. **Then on loop length.** Haiku-class holds single-digit tool-call chains;
   Sonnet-class the teens; past ~20 autonomous steps it is Opus-class.
3. **Then match task shape:** Haiku-class for mechanical bounded work, Sonnet-class
   for long tool-use loops, Opus-class for generating an artifact from an ambiguous
   brief or for adversarial review, a pinned model for a persona that *is* that
   model. There is no `inherit` fallback for judgment work that should scale with
   the caller — see the skill's "What shape is the work?" section for how to handle
   that case with a full-ID-only convention.

Two results from that skill are worth repeating because they contradict intuition:
**Sonnet beats Opus on long CLI/tool loops** (Terminal-Bench 2.1: 80.4% vs 74.6%), so
reaching for the top of the ladder makes agentic work slower *and* worse; and
**Fable silently routes security-adjacent prompts to an older Opus**, so a security
agent pinned to a Fable-class model gets less capability than Opus-class at twice the
price.

### Recording the reason

The tier is a design decision, so state it where a reviewer will see it rather than
in a list here. Put it in the agent's `description` when callers benefit from knowing
(`branch-warden`: "Runs on a cheap model so the main session does not burn tokens on
git plumbing"; `state-keeper` and `docs-user-maintainer` do the same), or in a
`<!-- ... -->` HTML comment in the body when it is purely internal. Do **not** put an
HTML comment above the frontmatter — the `---` block must start at line 1 or the file
will not parse as an agent.

This section deliberately does **not** enumerate what each agent in the repo currently
uses. That list existed here before and rotted — it drifted from the actual files
within a few changes, and a stale example list is worse than none, because it reads
as normative. The files are the source of truth; `check-agent-models.py --list` prints
the current assignments on demand.

## Invocation

Agents are invoked through the `Agent` tool (this tool was called `Task` prior to Claude Code v2.1.63; `Task(...)` references still work as an alias). The calling agent passes a `subagent_type` naming the agent to delegate to, plus a task prompt describing what it needs done.

* **Automatic delegation.** Claude matches the current task against every registered agent's `description` and delegates on its own when there's a strong match. This is why the `description` field's quality (see above) matters more than any other single piece of the file.
* **Proactive-triggering guidance.** Include phrasing like "use proactively" or "trigger proactively after X" directly in the description (see `plugin-validator.md`: "Also trigger proactively after user creates or modifies plugin components") to push Claude toward delegating without being asked explicitly.
* **Explicit invocation.** A user (or another agent) can name the agent directly in a prompt ("Use the branch-warden agent to clean up merged branches"), or `@`-mention it (`@agent-branch-warden`) to force that specific agent rather than leaving the choice to automatic matching.
* **Scoped identifiers for plugin agents.** An agent shipped inside a plugin is namespaced by the plugin (and any subfolder within the plugin's `agents/` directory): `plugin-name:agent-name`, or `plugin-name:subdir:agent-name` if organized into subfolders. Project- and user-scoped agents (`.claude/agents/`, `~/.claude/agents/`) are addressed by their bare `name` — subfolders there are for organization only and do not become part of the identifier.
* **Isolation.** Each agent invocation starts a fresh context window — it does not see the calling conversation's history, only the task prompt it's handed, plus (for non-`Explore`/`Plan` agents) the project's memory files and a git-status snapshot. Passing everything the agent needs into the task prompt is the caller's responsibility.

## Validation

There is no first-party `agent-ref` CLI analogous to `skills-ref` in this repo. One local script approximates it (referenced from the `agent-development` skill and used by `.claude/agents/plugin-validator.md`):

```bash
.claude/skills/agent-development/scripts/validate-agent.sh agents/<agent-name>/<agent-name>.md
```

Known limitation: the script reads only the same-line value of `description:`, so block-scalar descriptions (`description: >`) trigger a false "description too short" warning — ignore it for agents using that style.

At minimum, before publishing a new agent file, confirm:

* `name` is unique in its scope, lowercase-hyphenated, 3–50 characters
* `description` is non-empty and states concrete triggering conditions (with `<example>` blocks if the agent needs to catch varied natural-language phrasing)
* `tools` (if present) lists only tools the system prompt actually needs
* `model` is present (required here even though Claude Code allows omitting it) — a full model ID, never a bare alias or `inherit`
* The body is written in second person and includes an explicit output format

## Minimal worked example

A complete, valid agent — restricted to read-only tools, pinned to a cheap model, with a description that would trigger both reactively and proactively:

```markdown
---
name: changelog-drafter
description: |
  Use this agent when the user asks to "draft a changelog", "summarize what changed", or after a batch of commits lands that should be reflected in release notes. Examples:

  <example>
  Context: User just merged several PRs and wants release notes
  user: "Can you draft a changelog for this release?"
  assistant: "I'll use the changelog-drafter agent to summarize the recent commits."
  <commentary>
  Explicit changelog request, trigger changelog-drafter to summarize git history.
  </commentary>
  </example>

  <example>
  Context: User just merged a PR
  user: "Merged! Ship it."
  assistant: "Let me draft changelog notes for that before we move on."
  <commentary>
  A merge just happened; proactively draft changelog notes rather than waiting to be asked.
  </commentary>
  assistant: "I'll use the changelog-drafter agent to summarize what changed."
  </example>
model: claude-haiku-4-5
color: cyan
tools: Bash, Read
---

You are a changelog drafter. Your only job is to read recent git history and
turn it into a short, human-readable changelog entry.

## Steps

1. Run `git log --oneline -20` (or a caller-specified range) to see recent commits.
2. Group commits into Added / Changed / Fixed / Removed.
3. Rewrite each commit message as a one-line, user-facing sentence — drop
   internal details (file names, refactor mechanics) unless user-visible.
4. Return the changelog as Markdown, newest section first.

## Constraints

- Do not edit any files. Return the changelog as text for the caller to place.
- If commit messages are too terse to summarize confidently, say so rather
  than guessing at intent.
```
