# Project-Conventions Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a `project-conventions` skill (docs layout + Python CLI standards), bundle it into `instruction-management`, and migrate this repo's own root `TODO.md`/`STATE.md` to `docs/`.

**Architecture:** New skill in the `skills/` pool with two reference files, symlinked into the `instruction-management` bundle (auto-picked-up as a marketplace micro-entry by the generator). The repo migration is a `git mv` plus prose updates in 8 files; `marketplace.json` is regenerated once at the end to absorb both the new skill entry and the changed `state-keeper` description.

**Tech Stack:** Markdown skills, relative symlinks, `python3 .github/scripts/generate-marketplace.py`.

## Context

Approved spec: `docs/superpowers/specs/2026-08-02-project-conventions-design.md`. The author keeps re-explaining the same conventions (planning docs in `docs/TODO.md`/`docs/STATE.md`, user docs in `docs/user/`, uv+Typer for Python CLIs) project to project. This skill captures them once, distributably. Since this repo itself still uses root-level `TODO.md`/`STATE.md`, it migrates as part of the effort (dogfooding).

Exploration corrections to the spec:
- `README.md` has **no** TODO/STATE references (spec listed it) — verify-only, no edit expected.
- `docs/specs/agents/Agent-Specification.md:236` mentions "STATE.md upkeep" conceptually — left alone (not in spec's file list, still accurate).
- Historical spec docs under `docs/superpowers/specs/` are left untouched.

## Global Constraints

- `marketplace.json` is **generated** — never hand-edit; run `python3 .github/scripts/generate-marketplace.py` after pool/bundle changes. CI runs it with `--check`.
- Bundle versions live only in `plugins/<name>/.claude-plugin/plugin.json` — bump on any membership change. New member ⇒ `instruction-management` `1.5.3` → `1.6.0`.
- Skill symlink format: `plugins/<bundle>/skills/<name>` → `../../../skills/<name>` (directory symlink; picked up by default scan, no `plugin.json` listing needed — that's only for agent *file* symlinks).
- Skill `description:` frontmatter is the marketplace description (truncated at 200 chars at a word boundary — front-load the trigger language).
- CI validators that must stay green: `generate-marketplace.py --check`, `find plugins agents -xtype l` (empty), `hooks/hooks-toolkit/scripts/validate-skill-frontmatter.sh`, `hooks/hooks-toolkit/scripts/validate-plugin-json.sh`.
- Work on a feature branch off `main` (e.g. `feat/project-conventions`); commit per task.

---

### Task 0: Branch + persist the plan

**Files:**
- Create: `docs/superpowers/plans/2026-08-02-project-conventions.md` (copy of this plan)

- [ ] **Step 1: Create branch**

```bash
cd /home/dotme/Code/awesome-agency
git checkout -b feat/project-conventions
```

- [ ] **Step 2: Save this plan into the repo** (repo convention: dated docs under `docs/superpowers/`)

```bash
mkdir -p docs/superpowers/plans
cp /home/dotme/.claude/plans/superpower-implement-spec-docs-superpowe-bright-manatee.md docs/superpowers/plans/2026-08-02-project-conventions.md
git add docs/superpowers/plans/2026-08-02-project-conventions.md
git commit -m "docs: add project-conventions implementation plan"
```

---

### Task 1: Create the `project-conventions` skill

**Files:**
- Create: `skills/project-conventions/SKILL.md`
- Create: `skills/project-conventions/references/docs-layout.md`
- Create: `skills/project-conventions/references/cli-standards.md`

**Interfaces:**
- Produces: skill directory `skills/project-conventions/` with valid frontmatter (`name`, `description`) — Task 2 symlinks it, Task 4's generator reads `description` from it.
- Consumes: existing `state-keeper` agent (invoked by reference only — no code dependency).

- [ ] **Step 1: Write `skills/project-conventions/SKILL.md`**

````markdown
---
name: project-conventions
description: dotKnewt's cross-project conventions — planning docs in docs/TODO.md and docs/STATE.md, user docs in docs/user/, and uv + Typer standards for Python CLIs. Use when scaffolding a new project, asked where docs or backlog notes should live, adding a Python CLI command, or checking a project against these conventions.
---

# Project Conventions

Cross-project conventions: where planning and bookmark docs live, where
user-facing docs live, and how Python CLI tools get installed and
documented. Use this to scaffold a fresh project or as a standing
reference during ongoing work in any project that has it installed.

## Scaffold a project

When invoked to set up conventions on a project (fresh or existing):

1. Ensure `docs/` exists.
2. Create `docs/TODO.md` from the template in
   [references/docs-layout.md](references/docs-layout.md) if missing.
3. Create/maintain `docs/STATE.md` by invoking the `state-keeper` agent
   with path `docs/STATE.md`.
4. Note the `docs/user/` pattern — create the directory only if the
   project already has user-facing content to house there; otherwise
   just mention the convention for later.
5. If a Python CLI is detected (`pyproject.toml` with
   `[project.scripts]`), check its install docs, `--help` output, and
   completion setup against
   [references/cli-standards.md](references/cli-standards.md) and
   report gaps.

## Ongoing reference

- "Where should docs / backlog notes go?" →
  [references/docs-layout.md](references/docs-layout.md)
- Adding or changing a CLI command →
  [references/cli-standards.md](references/cli-standards.md)
- Wrapping up a session → invoke `state-keeper` with path
  `docs/STATE.md`; park backlog ideas in `docs/TODO.md`.
````

- [ ] **Step 2: Write `skills/project-conventions/references/docs-layout.md`**

````markdown
# Docs Layout Convention

## `docs/TODO.md` — backlog

Backlog notes, grouped by topic heading, bullet list per topic:

```markdown
# some-topic
- idea or task worth keeping
- another one

# another-topic
- ...
```

## `docs/STATE.md` — session bookmarks

Session bookmarks (What / How / WIP / ToDo / Completed / Decisions).
The schema is owned by the `state-keeper` agent — do not duplicate it
here. Create and maintain the file by invoking `state-keeper` with
path `docs/STATE.md`.

## `docs/user/*.md` — user-facing docs

User-facing docs: install, usage, tutorials, FAQ. Open-ended file set —
the convention establishes the location, not a fixed list of filenames.

Distinguish from:

- `docs/specs/` — architecture and contributor docs (owned by
  `docs-spec-maintainer`).
- Root `README.md` — short overview plus a pointer into `docs/user/`.
````

- [ ] **Step 3: Write `skills/project-conventions/references/cli-standards.md`**

````markdown
# Python CLI Standards

## Toolchain

- **Dev loop:** `uv sync` / `uv run` inside the repo during
  development.
- **End-user install:** `uv tool install <pkg>` for persistent
  installs, or `uvx <pkg>` for ephemeral runs. Do not document
  pip/pipx as the primary path.

## Framework

Recommend **Typer**: type-hint-driven command definitions,
auto-generated `--help`, and built-in `--install-completion` /
`--show-completion` (no separate `argcomplete` registration step;
pairs cleanly with a `uv tool install`-first story). Click/argparse
are acceptable fallbacks for constrained cases, not the default
recommendation.

## `--help` standard

- Every command and subcommand has a one-line summary.
- Every option has help text.
- Top-level `--help` lists the subcommands.
- The app's docstring includes a usage example (Typer renders it in
  help output).

## Completion standard

The README's install section documents `<tool> --install-completion`
as a one-time per-shell setup step.
````

- [ ] **Step 4: Validate frontmatter**

Run: `bash hooks/hooks-toolkit/scripts/validate-skill-frontmatter.sh`
Expected: exit 0, no complaints about `skills/project-conventions/SKILL.md`.

- [ ] **Step 5: Commit**

```bash
git add skills/project-conventions
git commit -m "feat: add project-conventions skill"
```

---

### Task 2: Bundle into `instruction-management`

**Files:**
- Create: symlink `plugins/instruction-management/skills/project-conventions` → `../../../skills/project-conventions`
- Modify: `plugins/instruction-management/.claude-plugin/plugin.json` (version only)

**Interfaces:**
- Consumes: `skills/project-conventions/` from Task 1.
- Produces: bundle membership Task 4's generator reflects in the `instruction-management` marketplace entry.

- [ ] **Step 1: Create the directory symlink** (same relative format as the bundle's existing skill links)

```bash
ln -s ../../../skills/project-conventions plugins/instruction-management/skills/project-conventions
```

- [ ] **Step 2: Bump bundle version** in `plugins/instruction-management/.claude-plugin/plugin.json`:

```json
"version": "1.6.0",
```

(was `1.5.3` — minor bump for new bundle member.)

- [ ] **Step 3: Verify no broken symlinks**

Run: `find plugins agents -xtype l`
Expected: no output.

Run: `bash hooks/hooks-toolkit/scripts/validate-plugin-json.sh`
Expected: exit 0.

- [ ] **Step 4: Commit**

```bash
git add plugins/instruction-management
git commit -m "feat: bundle project-conventions into instruction-management (1.6.0)"
```

---

### Task 3: Migrate `agency` itself to the new convention

**Files:**
- Move: `TODO.md` → `docs/TODO.md`, `STATE.md` → `docs/STATE.md`
- Modify: `AGENTS.md:54`
- Modify: `agents/state-keeper/state-keeper.md` (frontmatter description + body)
- Modify: `skills/instruction-management/SKILL.md:209,239`
- Modify: `skills/instruction-management/references/templates.md:123,129,160,207`
- Modify: `skills/instruction-management/references/update-guidelines.md:92`
- Modify: `docs/EXTENSIONS.md:83`
- Modify: `agents/docs-user-maintainer/docs-user-maintainer.md` (scope note)
- Verify-only: `README.md` (exploration found no TODO/STATE references)

**Interfaces:**
- Produces: changed `state-keeper` frontmatter `description` that Task 4's generator propagates into `marketplace.json`.
- Note: `plugins/instruction-management/agents/state-keeper.md` and `plugins/instruction-management/skills/instruction-management/` are symlinks into the pool — editing pool files covers both; do not edit through the plugin paths.

- [ ] **Step 1: Move the files**

```bash
git mv TODO.md docs/TODO.md
git mv STATE.md docs/STATE.md
```

- [ ] **Step 2: Update `AGENTS.md` line 54** (last bullet of "Repository layout"):

Old:
```markdown
- `TODO.md` — backlog notes; `STATE.md` — session bookmarks (stub unless an effort is active)
```
New:
```markdown
- `docs/TODO.md` — backlog notes; `docs/STATE.md` — session bookmarks (stub unless an effort is active)
```

- [ ] **Step 3: Update `agents/state-keeper/state-keeper.md`**

Frontmatter description, old first line:
```yaml
  Read STATE.md and maintain it: move completed items from WIP/ToDo into a
  timestamped Completed section, create STATE.md if absent, and surface
```
New:
```yaml
  Read docs/STATE.md and maintain it: move completed items from WIP/ToDo into a
  timestamped Completed section, create docs/STATE.md if absent, and surface
```

Body line 22, old:
```markdown
1. **Path to STATE.md** (usually `./STATE.md` relative to the project root)
```
New:
```markdown
1. **Path to STATE.md** (usually `docs/STATE.md` relative to the project root)
```

Leave the remaining bare `STATE.md` body mentions (L16, L28, L30, L60, L63) as-is — they refer to "the STATE.md file at the caller-supplied path", not to a location; only the default path and the description change per the spec.

- [ ] **Step 4: Update `skills/instruction-management/SKILL.md`**

Line 209, old fragment: `(AGENTS.md = north star for stable decisions, STATE.md = session bookmarks updated frequently)`
New fragment: `(AGENTS.md = north star for stable decisions, docs/STATE.md = session bookmarks updated frequently)`

Line 239, old: `- Memory vs. State (AGENTS.md = north star, STATE.md = session bookmarks)`
New: `- Memory vs. State (AGENTS.md = north star, docs/STATE.md = session bookmarks)`

- [ ] **Step 5: Update `skills/instruction-management/references/templates.md`** (4 spots)

Line 123, old: `Document the AGENTS.md / STATE.md split so agents know where to write durable vs. transient information.`
New: `Document the AGENTS.md / docs/STATE.md split so agents know where to write durable vs. transient information.`

Lines 129, 160, 207 (identical bullet in three templates), old:
```markdown
- **STATE.md** — session bookmarks and in-progress work (WIP, ToDo, recent Completed). Update every session or task switch; invoke the `state-keeper` subagent to keep it tidy.
```
New (all three, use `replace_all`):
```markdown
- **docs/STATE.md** — session bookmarks and in-progress work (WIP, ToDo, recent Completed). Update every session or task switch; invoke the `state-keeper` subagent to keep it tidy.
```

- [ ] **Step 6: Update `skills/instruction-management/references/update-guidelines.md` line 92** — same bullet text as Step 5, same replacement.

- [ ] **Step 7: Update `docs/EXTENSIONS.md` line 83**

Old: `- **Agent** `state-keeper` — read STATE.md and maintain it: move completed items into a timestamped Completed section, surface durable decisions as AGENTS.md candidates; runs on Haiku.`
New: `- **Agent** `state-keeper` — read docs/STATE.md and maintain it: move completed items into a timestamped Completed section, surface durable decisions as AGENTS.md candidates; runs on Haiku.`

- [ ] **Step 8: Update `agents/docs-user-maintainer/docs-user-maintainer.md` scope note** (spec's follow-on edit — name `docs/user/*.md` as the canonical audit target)

Old (in `## Scope`):
```markdown
If no scope list is provided, audit all user-facing docs: the root `README.md`,
`docs/` content addressed to users (installation, usage, tutorials, FAQs), and any
per-component READMEs.
```
New:
```markdown
If no scope list is provided, audit all user-facing docs: the root `README.md`,
`docs/user/*.md` (the canonical location for user-facing docs — installation,
usage, tutorials, FAQs), any other `docs/` content addressed to users, and any
per-component READMEs.
```

- [ ] **Step 9: Verify nothing was missed**

Run: `grep -rn --include='*.md' -E '(^|[^/a-z])(TODO|STATE)\.md' AGENTS.md README.md agents skills docs/EXTENSIONS.md hooks commands | grep -v docs/`
Expected: no hits pointing at root-level `TODO.md`/`STATE.md` (mentions of `docs/TODO.md`, `docs/STATE.md`, and generic "the STATE.md file" prose in state-keeper's body are fine). `README.md` should show no hits at all — the spec listed it, but it has no layout-table reference.

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "refactor: migrate TODO.md and STATE.md under docs/ per project-conventions"
```

---

### Task 4: Regenerate marketplace + full validation

**Files:**
- Regenerate: `.claude-plugin/marketplace.json` (new `project-conventions` micro-entry + updated `instruction-management` bundle description propagation + updated `state-keeper-agent` description)

**Interfaces:**
- Consumes: Task 1's skill `description`, Task 2's bundle membership, Task 3's `state-keeper` description.

- [ ] **Step 1: Confirm the manifest is stale (the "failing test")**

Run: `python3 .github/scripts/generate-marketplace.py --check`
Expected: exit 1, `marketplace.json is stale — run .github/scripts/generate-marketplace.py`

- [ ] **Step 2: Regenerate**

Run: `python3 .github/scripts/generate-marketplace.py`
Expected: `.claude-plugin/marketplace.json` rewritten. Sanity-check the diff: a new `project-conventions` micro-entry with `source: "./skills/project-conventions"`, and the `state-keeper-agent` entry's description now says `docs/STATE.md`.

- [ ] **Step 3: Full validation sweep**

```bash
python3 .github/scripts/generate-marketplace.py --check   # exit 0 now
find plugins agents -xtype l                              # no output
bash hooks/hooks-toolkit/scripts/validate-plugin-json.sh
bash hooks/hooks-toolkit/scripts/validate-skill-frontmatter.sh
claude plugin validate .
```
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add .claude-plugin/marketplace.json
git commit -m "chore: regenerate marketplace.json for project-conventions"
```

---

## Verification (end-to-end)

1. All Task 4 Step 3 commands pass (these are exactly what CI `.github/workflows/validate.yml` runs).
2. `jq '.plugins[] | select(.name=="project-conventions")' .claude-plugin/marketplace.json` returns the micro-entry.
3. `ls plugins/instruction-management/skills/` lists `project-conventions` and it resolves (`readlink -f`).
4. `test -f docs/TODO.md && test -f docs/STATE.md && ! test -f TODO.md && ! test -f STATE.md`.
5. Spot-check: skill's reference links resolve (`skills/project-conventions/references/{docs-layout,cli-standards}.md` exist).

## Out of scope (per spec)

- No fixed `docs/user/*.md` file list; no non-Python CLI coverage; no new agents; no migration of other repos.
- `docs/specs/agents/Agent-Specification.md` and historical `docs/superpowers/specs/*.md` mentions left untouched.
