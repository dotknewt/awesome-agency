---
name: host-portability
description: This skill should be used when the user asks about "Claude Code and Copilot CLI compatibility", "host portability", "Copilot plugin support", "host-compat", "check-host-compat", "known_exceptions", or needs guidance on authoring plugins, agents, skills, hooks, commands, or MCP config that install correctly in both Claude Code and GitHub Copilot CLI.
metadata:
  version: "0.1.0"
---

# Host Portability for Marketplace Artifacts

## Overview

Treat both Claude Code and GitHub Copilot CLI as supported install targets for this marketplace. Read `.github/host-compat.json` first; it is the machine-readable source of truth for host capability claims, severities, evidence, and `known_exceptions`. Use `.github/scripts/check-host-compat.py` as the derived checker, not as a separate policy document.

This guidance is empirical. It records behavior verified on a real machine, including behavior that contradicts vendor documentation. When observed behavior and docs disagree, follow `.github/host-compat.json`.

## Required Workflow

1. Read `.github/host-compat.json` before making portability claims.
2. Run the checker in list mode to see the current posture:

   ```bash
   python3 .github/scripts/check-host-compat.py --list
   ```

3. For review-grade validation, run the normal checker:

   ```bash
   python3 .github/scripts/check-host-compat.py
   ```

4. For stricter local review, fail on warnings too:

   ```bash
   python3 .github/scripts/check-host-compat.py --strict
   ```

5. Fix error-severity findings before shipping. Treat warnings as degraded behavior that must be intentionally accepted, documented, or declared as a known exception.

## Shared Subset

Assume both hosts install from `.claude-plugin/marketplace.json` and load the shared core:

| Capability | Shared behavior |
|---|---|
| Marketplace install | Both hosts install entries from `.claude-plugin/marketplace.json`. |
| Symlinks | Both hosts dereference symlinks at install time. |
| Skills | Both hosts load Agent Skills from `SKILL.md` with YAML frontmatter. |
| Agents | Both hosts load markdown agents with YAML frontmatter. |
| Shared hook events | Restrict hooks to `.github/host-compat.json` `shared_hook_events` unless the artifact has a declared exception. |

Key empirical fact: Copilot CLI **does** read `.claude-plugin/marketplace.json` and **does** dereference symlinks. GitHub's own docs were wrong for this repo's tested behavior. The matrix evidence cites the observed Copilot install cache under `~/.copilot/installed-plugins/awesome-agency/`.

## Copilot Divergences

Expect Copilot CLI to silently drop or reinterpret several Claude Code fields:

| Capability | Copilot behavior | Authoring rule |
|---|---|---|
| `model:` aliases on agents | Ignored; Copilot falls back to the session model. Logs include `model "haiku" is not available; will use current model instead` and equivalent messages for other aliases. | Keep required model fields for Claude Code, but make every agent correct at any model. Never rely on a cheap model for correctness. |
| Agent `color:` | Ignored; logs report an unknown field. | Treat as cosmetic only. Never encode meaning in color. |
| `disable-model-invocation: true` on skills | Ignored; an explicit-invocation-only skill becomes auto-invocable. | State the invocation constraint in the skill body prose so the model self-restricts. |
| Slash commands | Unsupported; Copilot has no slash-command concept. Skills fill that role. | Every shipped command needs a skill counterpart, or a declared host exception. |
| Bundle-local `.mcp.json` | Read as project-level config, not auto-started as a plugin-bundled server. | Document manual Copilot setup for bundled MCP servers or declare an exception. |
| `${CLAUDE_PLUGIN_ROOT}` | Unverified and contradictory. GitHub docs say no expansion, but observed superpowers behavior conflicts with that. | Do not assert support or lack of support in Copilot. Let the checker warn. |

## Load-Bearing Authoring Rules

Make agents model-portable. An agent's pinned `model:` value (a full model ID per this repo's convention) routes correctly in Claude Code, but its instructions must still produce correct output if Copilot runs it on the current session model instead. Use model choice only for cost, latency, or context budgeting, never for correctness.

Qualify model-dependent prose. Do not advertise benefits such as "runs on Haiku," "uses a cheap model," "saves main-session tokens," or "keeps cost low" unless the claim is explicitly scoped to Claude Code. The checker flags unqualified model-benefit claims because Copilot ignores the field.

Guard explicit-only skills twice. If a skill uses `disable-model-invocation: true`, include an early body sentence such as "Invoke this skill only when explicitly requested" or "Do not invoke this skill automatically." The frontmatter works in Claude Code but is dropped by Copilot.

Prefer skills for user-invoked workflows. Since Copilot has no slash-command concept, do not ship a command-only capability unless the bundle is intentionally Claude-only and recorded in `known_exceptions`.

Keep hook events shared by default. Use only the matrix `shared_hook_events` in shipped `hooks.json`. Add an exception before using a Claude-only event.

## Declaring Known Exceptions

Use `.github/host-compat.json` `known_exceptions` only for intentional, reviewed divergence. Each entry names an artifact path, a capability id, and a reason:

```json
{
  "artifact": "plugins/ludus-toolkit",
  "capability": "bundled-mcp",
  "reason": "Ships an in-tree MCP server. Copilot users configure it manually; the bundle README documents the steps."
}
```

Match `capability` to a real id in the matrix, such as `bundled-mcp`, `commands`, `hook-events`, `agent-model-alias`, `skill-disable-model-invocation`, or `plugin-root-var`. Scope `artifact` narrowly: prefer a specific bundle, skill, agent, or file path over a broad waiver. Explain why the exception is safe for users of the degraded host.

An entry missing `artifact` or `capability` is reported as an error rather than silently ignored.

## Vendored Bundles

A bundle marked with a `.vendored` file (currently `plugins/superpowers/`) follows upstream's authoring conventions, so the **authoring** capabilities are skipped for it: `agent-model-alias`, `agent-color`, `skill-disable-model-invocation`, and `commands`.

Host-installability capabilities are still checked — `hook-events`, `plugin-root-var`, and `bundled-mcp`. Upstream's conventions have no bearing on whether the code actually runs in a user's Copilot session, and a vendored bundle ships as a real marketplace entry.

After editing exceptions, run:

```bash
python3 .github/scripts/check-host-compat.py --list
python3 .github/scripts/check-host-compat.py --strict
```

## CI Integration

The marketplace CI job in `.github/workflows/validate.yml` runs:

```bash
python3 .github/scripts/check-host-compat.py
```

Default CI fails on error-severity findings. `--strict` is available locally for maintainers who want warnings to block before review.

## Common Mistakes

- Trusting vendor docs over `.github/host-compat.json` for Copilot marketplace installs or symlink behavior.
- Claiming an agent is safe because Claude Code routes it to a cheap model; Copilot can run it on any session model.
- Relying only on `disable-model-invocation` for a dangerous or explicit-only skill.
- Shipping a slash command without a skill counterpart and forgetting that Copilot users cannot invoke it.
- Documenting `${CLAUDE_PLUGIN_ROOT}` as supported or unsupported in Copilot before the contradiction is resolved.
