---
name: claude-handoff
description: Use when the user asks to hand off, delegate, or continue the current work in a background or new session — e.g. "can you keep working on this while I step away", "spin up a background agent for this", "hand this off", "continue this without me", "keep going on this while I'm in a meeting" — even if they don't say "handoff" explicitly. Writes a redacted, artifact-referencing handoff summary and launches a fresh background agent seeded with it via `claude --bg`.
disable-model-invocation: true
# `disable-model-invocation` is a Claude-Code-specific extension, not part of
# the base Agent Skills spec's documented frontmatter fields (name,
# description, license, compatibility, metadata, allowed-tools). It stays
# top-level rather than moving under `metadata:` because Claude Code only
# honors it there — `metadata` is inert key-value storage per spec, not read
# for behavior. Kept intentionally: launching a background agent is a
# consequential, user-initiated action, not something Claude should trigger
# on its own judgment from the description alone.
---

Write a handoff summary of the current conversation so a fresh agent can continue the work. Instead of saving it, launch a background agent seeded with the summary as its prompt: `claude --bg --name "<descriptive name>" "<handoff summary>"`. It starts in the current working directory and returns immediately; the user manages it with `claude agents`.

Always pass `-n`/`--name` with a descriptive name (e.g. `--name "Fix login bug"`) — it sets the display name shown in the job list, session picker, and terminal title. If the user gave a name (e.g. "spin up a background agent named migrate-db"), use it verbatim.

If the user passed arguments (e.g. `/claude-handoff focus on the auth refactor`), treat them as a description of what the next session will focus on and tailor the summary accordingly.

## Handoff Summary

Structure the summary with this template so output is consistent across handoffs — adapt the depth of each section to the task, but keep all five headings:

```markdown
## Handoff Summary

### Context
[Why this work is happening — the original request or goal, one to three sentences.]

### Current State
[What's done, what's in progress, and where things stand right now. Point at files and paths rather than pasting their contents.]

### Next Steps
[Ordered list of what the new agent should do next.]

### Suggested Skills
[Skills the new agent should invoke and why, e.g. "- `verify` — confirm the migration script runs end to end".]

### References
[Paths or URLs to PRDs, plans, ADRs, issues, commits, or diffs relevant to the work. Do not paste their contents — see Gotchas.]
```

Pass this whole markdown block as the `<handoff summary>` argument to `claude --bg`.

## Gotchas

- Never inline a full file diff, PRD, or command output dump in the summary — reference the path (and line range, if relevant) instead. The summary becomes the new agent's prompt; a wall of pasted content burns its context before it's read anything.
- Before including any command output in the summary, scan it for API keys, tokens, passwords, and other secrets (common patterns: `sk-`, `ghp_`, `AKIA`, `Bearer `, `-----BEGIN`, `.env` contents, connection strings with embedded credentials). Redact or omit rather than guess — the summary becomes the agent's prompt and may be logged or displayed.
- Don't duplicate content already captured in other artifacts (PRDs, plans, ADRs, issues, commits, diffs). Reference them by path or URL in the References section instead of restating them.
- The `--name` value is a display label only — it doesn't change the working directory or the session ID. Don't rely on it to disambiguate jobs programmatically.
