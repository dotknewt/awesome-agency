---
name: obsidian-vault
description: Search, create, and manage notes in the Obsidian vault with wikilinks and index notes. Use when user wants to find, create, or organize notes in Obsidian.
---

# Obsidian Vault

**Setup required before first use:** this skill needs to know where the user's Obsidian vault lives. Set the `OBSIDIAN_VAULT_PATH` environment variable to the vault's absolute path. Without it, workflows fall back to the original author's single-machine WSL path (see [Vault location](#vault-location)), which will not exist on most installs.

## Vault location

Resolve the vault path from the `OBSIDIAN_VAULT_PATH` environment variable, falling back to the author's original WSL path only as a last-resort example default:

```bash
OBSIDIAN_VAULT_PATH="${OBSIDIAN_VAULT_PATH:-/mnt/d/Obsidian Vault/AI Research/}"
```

Before running any workflow below, confirm the path actually resolves:

```bash
if [ ! -d "$OBSIDIAN_VAULT_PATH" ]; then
  echo "Vault not found at: $OBSIDIAN_VAULT_PATH" >&2
fi
```

If the directory doesn't exist — the WSL drive isn't mounted, you're on a different OS, or the vault folder was renamed or moved — do not keep guessing paths. Ask the user for their vault's actual path, use that directly for the rest of the session, and suggest they `export OBSIDIAN_VAULT_PATH=...` so future sessions don't need to ask again.

Mostly flat at root level.

## Naming conventions

- **Index notes**: aggregate related topics (e.g., `Ralph Wiggum Index.md`, `Skills Index.md`, `RAG Index.md`)
- **Title case** for all note names
- No folders for organization - use links and index notes instead

## Linking

- Use Obsidian `[[wikilinks]]` syntax: `[[Note Title]]`
- Notes link to dependencies/related notes at the bottom
- Index notes are just lists of `[[wikilinks]]`

## Workflows

### Search for notes

```bash
# Search by filename
find "$OBSIDIAN_VAULT_PATH" -name "*.md" | grep -i "keyword"

# Search by content
grep -rl "keyword" "$OBSIDIAN_VAULT_PATH" --include="*.md"
```

Or use Grep/Glob tools directly on `$OBSIDIAN_VAULT_PATH`.

### Create a new note

1. **Check for duplicates first**: `grep -ril "note title" "$OBSIDIAN_VAULT_PATH" --include="*.md"` (or `find "$OBSIDIAN_VAULT_PATH" -iname "*note title*.md"`). If a matching or near-matching note already exists, link to or update it instead of creating a new one — see [Gotchas](#gotchas).
2. Use **Title Case** for filename
3. Write content as a single unit of learning: one focused, self-contained concept per note rather than a running log or grab-bag of loosely related material — see [Gotchas](#gotchas) for what that looks like concretely.
4. Add `[[wikilinks]]` to related notes at the bottom
5. If part of a numbered sequence, use the hierarchical numbering scheme — see [Gotchas](#gotchas) for the pattern.

### Find related notes

Search for `[[Note Title]]` across the vault to find backlinks:

```bash
grep -rl "\\[\\[Note Title\\]\\]" "$OBSIDIAN_VAULT_PATH"
```

### Find index notes

```bash
find "$OBSIDIAN_VAULT_PATH" -name "*Index*"
```

## Gotchas

- **"Unit of learning" means one concept per note.** A note should stand on its own and explain a single idea, not accumulate everything tangentially related to a topic. E.g. `Retrieval Augmented Generation.md` explains what RAG is and how it works; a related-but-distinct idea like chunking strategy gets its own `RAG Chunking Strategies.md`, linked back with `[[Retrieval Augmented Generation]]` rather than appended to the same file.
- **Hierarchical numbering scheme**: when notes form an explicit ordered sequence (a course, a reading list, a multi-part topic), prefix the filename with `<section>.<step> Title.md` — e.g. `1.1 Introduction to Transformers.md`, `1.2 Attention Mechanisms.md`, `2.1 Fine-Tuning Basics.md`. Only apply this to notes that are genuinely sequential; most notes should not have a number prefix.
- **Always check for duplicates before creating a note.** Run `grep -ril "<title>" "$OBSIDIAN_VAULT_PATH" --include="*.md"` first. Titles are easy to duplicate under different phrasings (e.g. "RAG" vs "Retrieval Augmented Generation") — if a close match exists, prefer linking to or extending it over creating a near-duplicate note.
- **Never silently fall back to the example WSL path.** If `$OBSIDIAN_VAULT_PATH` doesn't resolve to a real directory, ask the user rather than writing to (or searching) a path that may not exist or may belong to someone else's vault.
