---
description: Scaffold a new standalone skill directory with SKILL.md frontmatter, references/, and scripts/ stubs
argument-hint: "<skill-name> [<one-line description>]"
allowed-tools: ["Read", "Write", "Bash", "AskUserQuestion"]
---

# /create-skill

Scaffold a new standalone skill under `skills/` in the current repository.

**Arguments:** `$ARGUMENTS`

## Steps

1. **Parse arguments:**
   - First token: the skill name (kebab-case). If missing, ask.
   - Remaining tokens: optional one-line description seed.

2. **Validate the skill name:**
   - Must match `^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$`.
   - Must not already exist as a directory under `skills/`. If it does, stop and report.

3. **Draft a description:**
   - If a description seed was provided, expand it into a 2–4 sentence trigger description following the pattern: *"Use this skill when... Triggers on... Examples include..."*
   - If no seed, ask the user: "What should this skill do, and what user phrases or task types should trigger it?"

4. **Create the directory structure:**
   ```bash
   mkdir -p skills/<name>/references
   mkdir -p skills/<name>/scripts
   ```

5. **Write `skills/<name>/SKILL.md`** with this template:
   ```markdown
   ---
   name: <name>
   description: >
     <description>
   ---

   # <Title>

   <!-- Instructions for Claude go here. Use imperative form. -->
   <!-- Keep under 500 lines; move detailed content to references/ -->
   ```

6. **Write `skills/<name>/references/.gitkeep`** and **`skills/<name>/scripts/.gitkeep`** (empty files).

7. **Register in the marketplace** — run `.github/scripts/generate-marketplace.py`. It creates the skill's micro-entry automatically (`marketplace.json` is generated; never hand-edit it). If the skill must NOT ship standalone (it depends on a bundle's scripts/hooks), add it to `BUNDLE_BOUND_SKILLS` in that script instead.

8. **Bundle membership (optional):** if the skill should also ship inside a bundle, symlink `plugins/<bundle>/skills/<name> → ../../../skills/<name>` and bump that bundle's `plugin.json` version.

9. **Confirm** to the user:
   ```
   Created skills/<name>/
   ├── SKILL.md
   ├── references/
   └── scripts/
   Regenerated .claude-plugin/marketplace.json (micro-entry added).
   Next: fill in the SKILL.md body, then run the plugin-validator agent to check the structure.
   ```

## Quality reminders (from Skill-Specification.md)

- `description` is the primary trigger signal — make it specific, with concrete example phrases.
- Body must be written in **imperative form** (instructions for Claude, not the user).
- Keep `SKILL.md` under **500 lines**; move depth to `references/`.
- No `model` field — model is set at session/project level.
