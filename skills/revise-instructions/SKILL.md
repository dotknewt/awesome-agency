---
name: revise-instructions
description: Update AGENTS.md (or legacy CLAUDE.md) with learnings from this session — discovered commands, patterns, gotchas, or configuration quirks worth capturing for future sessions. Use when the user asks to capture, save, remember, or record session learnings into project instructions, or after a session that surfaced non-obvious context a fresh agent would benefit from.
---

# Revise Instructions

Review this session for learnings about working with this codebase. Update the instruction file with context that would help future sessions be more effective.

This skill writes to `AGENTS.md` by default. If the repo only has `CLAUDE.md`, surface the migration option (see `../instruction-management/references/migration.md`) before adding new content there.

## Step 1: Reflect

What context was missing that would have helped the agent work more effectively?
- Bash commands that were used or discovered
- Code style patterns followed
- Testing approaches that worked
- Environment/configuration quirks
- Warnings or gotchas encountered
- Facts that required an Explore subagent or repeated Glob/Grep/Read calls to find

## Step 2: Find instruction files

```bash
find . \( -name "AGENTS.md" -o -name "CLAUDE.md" -o -name ".claude.local.md" \) \
  -not -path '*/node_modules/*' -not -path '*/.git/*' 2>/dev/null | sort
```

Classify what you find:

- **AGENTS.md present** → edits go here.
- **CLAUDE.md only** → mention migration to AGENTS.md as the recommended next step; if the user defers, edit `CLAUDE.md` for now.
- **CLAUDE.md is a `@AGENTS.md` stub** → **never edit the stub.** Edits go in `AGENTS.md`.
- **Neither** → offer to scaffold an `AGENTS.md`.

Decide where each addition belongs:
- `AGENTS.md` — team-shared (checked into git)
- `.claude.local.md` — personal/local only (gitignored)

## Step 3: Draft additions

**Keep it concise** — one line per concept. Instruction files ride along in the prompt, so brevity matters.

Format: `<command or pattern>` - `<brief description>`

Avoid:
- Verbose explanations
- Obvious information
- One-off fixes unlikely to recur

## Step 4: Show proposed changes

For each addition:

```
### Update: ./AGENTS.md

**Why:** [one-line reason]

\`\`\`diff
+ [the addition - keep it brief]
\`\`\`
```

## Step 5: Apply with approval

Ask before editing. Only apply changes the user approves.

## Step 6: Clear the nudge sentinel

After applying changes, run:

```bash
project_hash=$(printf '%s' "${CLAUDE_PROJECT_DIR:-.}" | md5sum | cut -c1-8)
rm -f "/tmp/revise-instructions-nudge/$project_hash"
```

This resets the stop-hook nudge counter so the hook can fire again if the session continues touching more files.
