---
name: vault-session
description: Curate the current session's note in vault/sessions (Summary, Decisions, Knowledge written, Open questions, Next step), promote unsaved durable learnings via /vault-save, update plan statuses and INDEX. Run before /compact, before ending a substantial session, after finishing a major sub-task, or when asked what was done.
argument-hint: "[outcome: success|partial|blocked]"
user-invocable: true
---
# /vault-session — curate the session note (runs in the main context)

Session id: `${CLAUDE_SESSION_ID}`. Arguments: $ARGUMENTS

1. Find the note: `Grep 'session_id: "${CLAUDE_SESSION_ID}"' vault/sessions`. If absent (the Stop hook has not fired yet), create
   `vault/sessions/<today>--<short-slug>.md` with native `Write`: frontmatter `type: session`, the exact line `session_id: "${CLAUDE_SESSION_ID}"`,
   `title, description: "", status: open, date, tags: [session], promoted: false`; body = `# <title>`, an empty generated block
   (`<!-- generated:start -->` / `<!-- generated:end -->` on their own lines) and the curated headings below. The Stop hook fills the
   block and hook-owned keys on the next turn.
2. Never touch the block between `<!-- generated:start -->` and `<!-- generated:end -->`, nor the hook-owned keys
   (`session_id, slug, date, started, updated, ended, status, model, cwd, git_branch, prompts, tools_used, files_touched, plans, tokens_*`).
3. Rewrite the curated sections (native `Edit` or `mcp__obsidian__patch_note`), each concise and self-contained — they are
   re-injected after compaction and on resume:
   - `## Summary` — ≤8 lines: goal, what was done, outcome.
   - `## Decisions` — `- <decision> — <why> (→ [[adr-…]] if recorded)`.
   - `## Knowledge written` — `- [[basename]] (ADD|UPDATE|SUPERSEDE)`; for any durable learning NOT yet saved add
     `- [ ] PROMOTE: <claim>` and run `/vault-save` for it now (unless the user declines).
   - `## Open questions` — unresolved items, each with what would resolve it.
   - `## Next step` — 1–3 concrete, actionable lines with file paths/commands. This is what the next session sees first.
4. Frontmatter (merge via `mcp__obsidian__update_frontmatter {path:"sessions/<file>", frontmatter:{…}, merge:true}`):
   `description` (≤160 chars), `outcome: success|partial|blocked`, `tags` (+ area tags), `related` (plans/ADRs touched, quoted
   `"[[…]]"`), `promoted: true` when nothing is left to promote.
5. Plans touched this session (`vault/plans/*.md` listed in the note's `plans:`): if a plan file has no frontmatter yet, prepend the
   plan block from the conventions (`type: plan, title, description, status, created, updated, tags: [plan], session_id, slug, outcome, produced`);
   then set `status` (`approved|in-progress|done|abandoned`), `outcome`, `produced` (`"[[…]]"` list) via `update_frontmatter`.
6. INDEX: make sure every note written this session is linked from INDEX or a MOC; under `## Active plans` add/refresh
   `- [[plan-basename]] — title (status)` for plans still `draft|approved|in-progress` and remove the line when done/abandoned/superseded
   (replace the `- (no active plans)` placeholder when adding the first); keep INDEX ≤150 lines.
7. Reply with the note path and the `## Next step` lines only. (`status` is hook-owned: it becomes `closed` at SessionEnd.)
Never paste tool output, code, or transcript text into the note.
