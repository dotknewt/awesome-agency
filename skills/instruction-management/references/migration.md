# CLAUDE.md → AGENTS.md Migration

`AGENTS.md` is the cross-agent standard (agents.md). `CLAUDE.md` is Claude Code's legacy filename. When a repo only has `CLAUDE.md`, offer the user two migration paths. Apply the chosen path consistently across **every** legacy `CLAUDE.md` in the repo — mixed strategies create confusion.

## Decision: which option?

| Question | Lean toward |
|---|---|
| Does the team still use Claude Code? | **Option B** (stub) |
| Are they switching off Claude Code, or only using AGENTS.md-aware agents (Codex, Cursor, etc.)? | **Option A** (rename) |
| Is the team OK with two filenames in the repo as long as content stays in sync? | **Option B** |
| Do they want a single file at any cost? | **Option A** |

Default recommendation when unsure: **Option B**. It costs one extra two-line file and removes a foot-gun (Claude Code silently not loading `AGENTS.md`).

## Option A — Rename

Move the file, keep nothing behind.

```bash
git mv CLAUDE.md AGENTS.md
```

Repeat for every `CLAUDE.md` in the tree.

**Trade-off:** Claude Code does **not** currently auto-load `AGENTS.md`. After a rename, Claude Code sessions will start without the project context unless the user invokes `/init` or otherwise references it. Fine if Claude Code is no longer in the loop; painful otherwise.

## Option B — Migrate + stub *(recommended when Claude Code is in use)*

Move the content to `AGENTS.md`, leave a `CLAUDE.md` stub that `@`-references it.

```bash
git mv CLAUDE.md AGENTS.md
cat > CLAUDE.md <<'EOF'
<!-- DO NOT EDIT — see AGENTS.md -->
@AGENTS.md
EOF
```

Result:
- Claude Code auto-loads `CLAUDE.md` → inlines `AGENTS.md` via the `@` reference → same content.
- Codex / Cursor / other agents read `AGENTS.md` directly.
- One source of truth: edits happen in `AGENTS.md`.
- The `<!-- DO NOT EDIT -->` comment warns future contributors not to add content to the stub.

Repeat for every directory that has a `CLAUDE.md`.

### Stub contents

```markdown
<!-- DO NOT EDIT — see AGENTS.md -->
@AGENTS.md
```

Two lines, exactly. Anything more and the stub starts drifting.

## Mixed state: both files have real content

When a directory already has *both* `AGENTS.md` and `CLAUDE.md` and `CLAUDE.md` is **not** a stub, the repo has two sources of truth — flag it. Propose:

1. Diff the two files; surface conflicts to the user.
2. After they resolve, write the merged content to `AGENTS.md`.
3. Replace `CLAUDE.md` with the stub (Option B) or delete it (Option A equivalent).

Do not silently overwrite either file.

## What to tell the user after migrating

- "Edits go in `AGENTS.md` from now on. The `CLAUDE.md` stub is auto-loaded by Claude Code and just points at `AGENTS.md`."
- If they used `#` in Claude Code to capture learnings: it will still write to `CLAUDE.md`. After migration, that becomes a foot-gun — content ends up in the stub. Suggest editing `AGENTS.md` directly or removing the stub and accepting Option A's trade-off.

## Verification after migration

```bash
# Every CLAUDE.md should now be either a stub or absent.
find . -name "CLAUDE.md" -not -path '*/node_modules/*' -not -path '*/.git/*' \
  -exec sh -c 'head -5 "$1" | grep -q "@AGENTS.md" || echo "NOT A STUB: $1"' _ {} \;
```

Anything printed is a file that still has real content — investigate before considering the migration complete.
