---
name: project-environment
description: Scans AGENTS.md, the knowledge base, the skill set, and guardrails/hooks for gaps relevant to a spec'd-out idea, and drafts hook configs for any risky action found — the third of three spec-gap-closing layers, run before any code, docs, or planning. Writes specs/SLUG/environment.md. Use when invoked directly ("check my repo is ready for X", "audit the environment before we build this") or as the final step dispatched by project-manager, after project-spec and project-verify have completed.
---

# project-environment

## Why this exists

A correct spec can still fail in practice if the surrounding environment doesn't support it — missing conventions in AGENTS.md, a knowledge base an agent can't navigate, no skill for a repeated task, or a risky action nothing prevents an agent from taking unsupervised. This layer's job is to surface exactly those gaps, in priority order, with a concrete fix for each — and to make sure any action risky enough to need a hook actually gets one drafted, not just mentioned in passing.

Read `references/checkpoint-protocol.md` before starting — the itemized claim test, the attribution rule, the load-bearing test, checkpoint timing, the critic mechanism, and the logging format are identical to the other two layers and are not repeated here. Apply them to the gap findings themselves (each reported gap is a claim — it must be specific enough to be verified, not "the docs could be better").

## Standalone invocation and dependency check

This skill depends on `specs/SLUG/spec.md` and `specs/SLUG/verify.md` both existing with `status: complete` — each file's own frontmatter, nothing else. If invoked directly and either is missing:

> "environment gaps are easier to scope with a known goal and success criteria in hand. Run the missing layer(s) first, or proceed anyway scanning generically?"

Explicit choice, never silent either way. If the user proceeds anyway, `grounded_in` (below) records the state you actually observed for each dependency.

## Step 1 — Scan using existing maintainers, not from scratch

Check whether the `steward` plugin's maintainer agents are available (`steward:instructions-maintainer` for AGENTS.md, `steward:conventions-maintainer` for planning/doc conventions, `steward:schema-maintainer` for structured knowledge-base files, and any other `steward:*` maintainer relevant to what this specific idea touches). If available, dispatch to them and synthesize their findings — don't re-implement AGENTS.md or knowledge-base auditing logic that already exists and is maintained.

If `steward` is not installed or the dispatch fails, ask explicitly:

> "steward's maintainer agents aren't available — install steward, or should I run a built-in fallback scan instead (AGENTS.md's five sections, basic knowledge-base structure, guardrail presence)?"

If the user picks the fallback, check AGENTS.md for these five things a good instructions file covers (repo layout, skill routing, knowledge architecture, project lifecycle, working rules), check the knowledge base for chunking/metadata consistency and duplicate content, check for skills covering anything this idea will require doing repeatedly, and check for an existing ALWAYS/ASK BEFORE/NEVER guardrail classification.

## Step 2 — Report gaps in severity-ordered batches of 5

Rank every gap found by how much damage it could cause if left unaddressed (a missing guardrail around a destructive action outranks a stale AGENTS.md example). Report the top 5 in full:

- **File**: exact path
- **Problem**: what's wrong or missing, stated as a specific, checkable claim (subject to the itemized claim test)
- **Fix**: the exact change — not "improve this," but the actual replacement text, added section, or new file
- **Source**: `@observed` with the path or command you actually checked — a steward maintainer's finding is `@observed` too, naming the maintainer and what it reported — or `@inferred` if you're reasoning from what the spec implies rather than from something you read

Gaps are yours, not the user's. A gap the user accepted as risk, or picked from a batch you wrote, stays `@observed`/`@inferred` — accepting a risk is not the same as reporting a problem, and it must never be re-stated later as "the gap you flagged."

After the human responds to a batch (see Step 4), re-scan and report the next 5 highest-severity remaining gaps. Loop until none remain. Never silently cap at one batch of 5 and imply that's everything — if more exist, say so and keep going.

## Step 3 — Draft hook configs for risky actions

For any gap that amounts to "an agent could take this action with no barrier and it would be hard to undo" (touching production, sending external communications, deleting data, exposing secrets, spending money), don't just flag it — draft an actual PreToolUse hook that would gate it. A drafted hook is two pieces: the settings entry and the script it points at. The path is `$CLAUDE_PROJECT_DIR`-relative because these hooks land in the user's own project, not in a plugin — `${CLAUDE_PLUGIN_ROOT}` only resolves for hooks shipped inside an installed plugin.

```json
{
  "matcher": "Bash",
  "hooks": [{ "type": "command", "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/gate-prod-deploy.sh" }]
}
```

```bash
#!/usr/bin/env bash
# PreToolUse(Bash): make a production deploy require an explicit human decision.
set -euo pipefail

input=$(cat)                                              # payload arrives as JSON on stdin
[ "$(jq -r '.tool_name // ""' <<<"$input")" = "Bash" ] || exit 0
command=$(jq -r '.tool_input.command // ""' <<<"$input")

grep -qE '(^|[[:space:]])(kubectl|helm|terraform|fly|flyctl)[[:space:]].*prod' <<<"$command" || exit 0

jq -nc '{hookSpecificOutput: {hookEventName: "PreToolUse",
         permissionDecision: "ask",
         permissionDecisionReason: "targets production — confirm before running"}}'
exit 0
```

Three mechanics a drafted hook gets wrong easily, all of which make it silently inert:

- The payload is **JSON on stdin**, parsed with `jq`. There is no `$TOOL_INPUT` variable in a `type: command` hook — that interpolation exists only in `type: prompt` hooks.
- **Deny** is a plain-text reason on **stderr** plus `exit 2`. **Ask** is the `hookSpecificOutput` JSON above on **stdout** plus `exit 0` — the only path that can express "ask", since `exit 2` can only block. Every other non-zero exit is a non-blocking error: the tool call proceeds.
- A pattern list is a speed bump, not a control. `rm -fr`, added quoting, an alias, or a path built from a variable all walk straight past a regex. Draft narrowly, prefer `ask` over a promise of prevention, and when you present the hook, say plainly which cases it catches and which it doesn't — a gap closed on paper is worse than a gap left open, because nobody looks at it twice.

Present the drafted hook alongside the gap it addresses so the human can review and apply it — this skill drafts hooks, it does not install or activate them unasked.

## Step 4 — Resolve or accept, every batch

For each batch of 5, ask explicitly:

> "Here are the top 5 environment gaps for this idea. For each: fix it now, or explicitly accept the risk and move on?"

Render as a structured choice per gap (not one blanket yes/no for the whole batch) so accepting risk on gap 3 doesn't silently also wave through gap 1. Log every choice.

## Writing environment.md

```markdown
---
idea: "<working title>"
slug: <slug>
status: draft | in-progress | complete
grounded_in:
  spec.md: complete | incomplete | missing    # the state observed when this file was written
  verify.md: complete | incomplete | missing
---

## Environment Gaps
<batches of file/problem/fix, with resolved/accepted-risk status per gap>

## Hook Drafts
<drafted hook configs, tied to the gap each addresses>
```

Target 200-500 words per batch cycle; if many batches are needed, that's a signal worth naming to the user, not silently absorbing. Append every checkpoint to `specs/SLUG/environment.decisions.log`. Set `status: complete` once every gap found is either fixed or explicitly accepted as risk — not just reported. An accepted risk is a recorded decision, not an unfinished layer: it does not hold this file below `complete`.

## Handing off

When `environment.md` reaches `status: complete`, tell the user all three layers are done, list the three files and their logs, and note this skill's job ends here — it does not apply the drafted hooks or begin implementation itself.
