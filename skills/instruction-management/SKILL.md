---
name: instruction-management
description: Audit and improve AGENTS.md project instructions (and legacy CLAUDE.md). Use when the user asks to check, audit, update, improve, fix, restructure, or clean up AGENTS.md / CLAUDE.md, or mentions "agent memory", "project memory", "project instructions", "instruction file", "instruction maintenance", "instruction structure", or filenames like AGENTS.md, agents.md, CLAUDE.md. Scans the repo, evaluates quality against a rubric, prints a report, and proposes targeted edits. When the repo still uses CLAUDE.md only, also proposes migrating to AGENTS.md.
tools: Read, Glob, Grep, Bash, Edit, Write
---

# Instruction Management

Goal: keep instruction files complete enough that agents rarely need Explore subagents or ad-hoc Glob/Grep/Read searches to find what's already documented.

Audit, evaluate, and improve project instruction files (`AGENTS.md` by default; legacy `CLAUDE.md` is recognized) so any agent reading the repo has accurate, useful project context.

`AGENTS.md` (the agents.md convention) is portable across agent CLIs — Claude Code, Codex, Cursor, and others. `CLAUDE.md` is Claude Code's legacy filename; this skill keeps it working through migration.

**This skill writes to instruction files.** It always prints a quality report and proposes diffs before editing, and waits for user approval.

## Workflow

### Phase 1 — Discovery

Find every project instruction file under the working tree, ignoring noise dirs:

```bash
find . \( -name "AGENTS.md" -o -name "CLAUDE.md" -o -name ".claude.local.md" \) \
  -not -path '*/node_modules/*' -not -path '*/.git/*' \
  -not -path '*/.venv/*' -not -path '*/dist/*' -not -path '*/build/*' \
  2>/dev/null | sort
```

Group results by directory and classify each directory's state:

| State | Meaning | Action |
|---|---|---|
| **AGENTS.md only** | Canonical setup | Audit normally (Phase 2+) |
| **CLAUDE.md only** | Legacy setup | Audit, then run **Phase 1.5 — Migration** |
| **Both, CLAUDE.md is a stub** | Already migrated (CLAUDE.md contains only `@AGENTS.md` + header) | Audit AGENTS.md only |
| **Both, both have content** | Drift — two sources of truth | Audit both, flag drift, propose consolidation |
| **Neither** | No agent memory yet | Optionally offer to scaffold `AGENTS.md` |

**File types & locations:**

| Type | Location | Purpose |
|---|---|---|
| Project root | `./AGENTS.md` | Primary project context (checked into git) |
| Local overrides | `./.claude.local.md` | Personal/local settings (gitignored) |
| Global defaults | `~/.claude/CLAUDE.md` or `~/.codex/AGENTS.md` | User-wide defaults |
| Package-specific | `./packages/*/AGENTS.md` | Module-level context in monorepos |
| Subdirectory | Any nested location | Feature/domain-specific context |

Most agents auto-discover instruction files in parent directories, so monorepo nesting works automatically.

### Phase 1.5 — Migration (only when legacy `CLAUDE.md` is present)

See [references/migration.md](references/migration.md) for full recipes and rationale.

**You must present both options every time** — even if one feels obviously better for this repo. The trade-off depends on whether the user is still using Claude Code, which only they know. Picking unilaterally robs them of that decision.

When a directory has `CLAUDE.md` but no `AGENTS.md`:

- **(A) Migrate + stub** *(recommended)* — move content into `AGENTS.md`, then replace `CLAUDE.md` with a `@AGENTS.md` stub so Claude Code keeps auto-loading the same content. One source of truth, both worlds happy.
- **(B) Rename** — `git mv CLAUDE.md AGENTS.md`. Single file. Use when the user is moving off Claude Code or doesn't rely on Claude Code's auto-load of `CLAUDE.md`.

Show both. Explain the trade-off. **End with an explicit "Option A or B?" question** before doing anything.

Apply the user's choice across **all** legacy `CLAUDE.md` files in the repo consistently — do not mix strategies.

### Phase 2 — Quality Assessment

For each instruction file, score against the rubric. See [references/quality-criteria.md](references/quality-criteria.md) for the full rubric.

**Quick checklist:**

| Criterion | Weight | Check |
|---|---|---|
| Commands/workflows | High | Build / test / deploy / dev commands present? |
| Architecture clarity | High | Can a fresh agent grasp the codebase shape? |
| Non-obvious patterns | Medium | Gotchas and quirks documented? |
| Conciseness | Medium | No filler, no restating-the-obvious? |
| Currency | High | Matches current codebase state? |
| Actionability | High | Instructions executable, paths real? |

**Grades:** A (90–100), B (70–89), C (50–69), D (30–49), F (0–29).

### Phase 3 — Quality Report

**Always print the report before proposing edits.**

```
## Agent Memory Quality Report

### Summary
- Files found: X (AGENTS.md: N, CLAUDE.md: M)
- Average score: X/100
- Files needing update: X
- Legacy CLAUDE.md files needing migration: X

### File-by-File Assessment

#### 1. ./AGENTS.md (Project Root)
**Score: XX/100 (Grade: X)**

| Criterion | Score | Notes |
|---|---|---|
| Commands/workflows | X/20 | ... |
| Architecture clarity | X/20 | ... |
| Non-obvious patterns | X/15 | ... |
| Conciseness | X/15 | ... |
| Currency | X/15 | ... |
| Actionability | X/15 | ... |

**Issues:** ...
**Recommended additions:** ...

#### 2. ./packages/api/CLAUDE.md (Legacy — migration proposed)
...
```

### Phase 4 — Targeted Updates

**Default: run both sub-skills before proposing inline edits.**

After the report in Phase 3, invoke each sub-skill via the Skill tool (in order):

1. `revise-instructions` — capture anything new discovered this session.
2. `restructure-instructions` — move any misplaced content to its correct depth.

Then handle any residual updates inline as described below.

**Honor user skip phrases** — if the user's original prompt or a follow-up says "skip revise" / "no revision" / "don't capture learnings" (or the equivalent for restructure), omit that sub-skill and note the skip in the report. If the user says "audit only" or similar, skip both.

After the report, propose edits and ask for confirmation. Two kinds of changes:

1. **Content updates** — additions, corrections, deletions inside an instruction file.
2. **Migration edits** — `git mv CLAUDE.md AGENTS.md` and (option A only) writing the stub.

See [references/update-guidelines.md](references/update-guidelines.md) for what to add and what to skip.

**Diff format (content update):**

````markdown
### Update: ./AGENTS.md

**Why:** Build command was missing — fresh sessions had to inspect `package.json` to find it.

```diff
+ ## Commands
+
+ | Command | Description |
+ |---|---|
+ | `npm install` | Install deps |
+ | `npm run dev` | Dev server on port 3000 |
+ | `npm test` | Vitest suite |
```
````

**Diff format (migration — always present both options):**

````markdown
### Migrate: ./CLAUDE.md → ./AGENTS.md

**Why:** Switch to the cross-agent standard. Pick one strategy and apply it repo-wide.

**Option A — Migrate + stub** *(recommended)*

```bash
git mv CLAUDE.md AGENTS.md
```

Then write `CLAUDE.md`:

```markdown
<!-- DO NOT EDIT — see AGENTS.md -->
@AGENTS.md
```

Claude Code auto-loads the stub → `@`-references inline `AGENTS.md` → same content. Other agents read `AGENTS.md` directly.

**Option B — Rename only**

```bash
git mv CLAUDE.md AGENTS.md
```

Trade-off: Claude Code no longer auto-loads the file. Fine if you're moving off Claude Code; a foot-gun otherwise.

**Which option do you want?** (A or B)
````

### Phase 5 — Apply

After user approval, apply edits with `Edit` / `Write` / `Bash` (for `git mv`). Preserve existing content structure; do not reorder sections gratuitously.

## Templates

See [references/templates.md](references/templates.md) for `AGENTS.md` templates by project type.

## Common Issues to Flag

1. **Stale commands** — build/test commands that no longer work
2. **Missing dependencies** — required tools not mentioned
3. **Outdated architecture** — directory layout that's changed
4. **Missing environment setup** — required env vars not listed
5. **Broken test commands** — test scripts renamed/removed
6. **Undocumented gotchas** — non-obvious patterns not captured
7. **Legacy `CLAUDE.md` without `AGENTS.md`** — migration candidate
8. **Drift between `CLAUDE.md` and `AGENTS.md`** — two sources of truth
9. **Root AGENTS.md contains subdirectory-specific detail** — if content only applies when working under a specific directory (e.g. `mcp/`, `packages/api/`), it belongs in that directory's own AGENTS.md, not root. Root detail bloats every session regardless of task. Handled by the `restructure-instructions` sub-skill in Phase 4.
10. **Root AGENTS.md missing `@subdir/AGENTS.md` references** — when a subdirectory has its own AGENTS.md, root should reference it with `@subdir/AGENTS.md` so agents know where to look without loading the content until they're in that directory. Handled by the `restructure-instructions` sub-skill in Phase 4.
11. **Root AGENTS.md missing Memory vs. State callout** — if the root AGENTS.md has no `## Memory vs. State` section, suggest adding the standard snippet (AGENTS.md = north star for stable decisions, STATE.md = session bookmarks updated frequently).

## User Tips to Share

When presenting recommendations, remind the user:

- **`#` shortcut** (Claude Code): press `#` mid-session to have the agent auto-incorporate learnings into the instruction file.
- **Keep it concise.** Instruction files ride along in the prompt — dense beats verbose.
- **Actionable commands.** Every documented command should be copy-paste ready.
- **`.claude.local.md`** for personal preferences not shared with the team (gitignored).
- **Global defaults** live in `~/.claude/CLAUDE.md` or `~/.codex/AGENTS.md`.

## What Makes a Great AGENTS.md

**Key principles:**
- Concise and human-readable
- Actionable commands that can be copy-pasted
- Project-specific patterns, not generic advice
- Non-obvious gotchas and warnings
- **Right depth**: root AGENTS.md = orientation only. Detail that only applies under a subdirectory belongs in `<subdir>/AGENTS.md`. Root references subdirectories with `@subdir/AGENTS.md` — this defers loading until an agent actually works in that area.

**Recommended sections** (use only what's relevant):
- Commands (build, test, dev, lint)
- Architecture (directory structure)
- Key Files (entry points, config)
- Code Style (project conventions)
- Environment (required vars, setup)
- Testing (commands, patterns)
- Gotchas (quirks, common mistakes)
- Workflow (when to do what)
- Memory vs. State (AGENTS.md = north star, STATE.md = session bookmarks)
