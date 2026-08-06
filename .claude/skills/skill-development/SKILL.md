---
name: skill-development
description: This skill should be used when the user wants to "create a skill", "add a skill to plugin", "write a new skill", "improve skill description", "organize skill content", or needs guidance on skill structure, progressive disclosure, or skill development best practices for Claude Code plugins.
metadata:
  version: "0.1.0"
---

# Skill Development for Claude Code Plugins

This skill provides guidance for creating effective skills for Claude Code plugins.

## About Skills

See `references/skill-creator-original.md` for what skills are, their anatomy (SKILL.md plus optional `scripts/`, `references/`, `assets/` bundled resources), and the three-level progressive-disclosure loading model. That file is the original generic skill-creator guidance this skill adapts. The rest of this file covers what's specific to authoring skills as part of a Claude Code plugin in this repo.

## Skill Creation Process

Follow this process in order, skipping a step only when there's a clear reason it doesn't apply.

### Steps 1-2: Understand Usage, Then Plan Resources

Follow the general Steps 1 and 2 in `references/skill-creator-original.md`: gather concrete examples of how the skill will be used, then analyze each example to decide what `scripts/`, `references/`, and `examples/` content would help.

For Claude Code plugin skills specifically, this planning also covers the plugin components (hooks, commands, agents) the skill needs to explain. For example, a hooks-authoring skill needs a validation script (e.g. `validate-hook-schema.sh`) to check hooks.json, and a reference doc (e.g. `patterns.md`) for detailed hook patterns, so SKILL.md itself doesn't get bloated with every pattern.

### Step 3: Create the Skill Structure

Create the skill directory directly — plugin skills don't use the generic skill-creator's `init_skill.py`:

```bash
mkdir -p plugin-name/skills/skill-name/{references,examples,scripts}
touch plugin-name/skills/skill-name/SKILL.md
```

Create only the directories actually needed, and delete any unused ones. `assets/` (templates, images, data files copied into output) is also a valid optional resource type per the upstream Agent Skills spec — see `references/skill-creator-original.md` — but every skill in this repo's `.claude/skills/` uses `examples/` by convention instead. Prefer `examples/` unless the skill genuinely produces binary/template output that belongs in `assets/`.

### Step 4: Write SKILL.md

Write the entire body in **imperative/infinitive form** (verb-first), not second person:

```
Correct:   Validate settings before use.
Incorrect: You should validate settings before use.
```

**Frontmatter:** use third person and specific trigger phrases. `name` must be lowercase alphanumeric-and-hyphens (no spaces, no uppercase) and match the skill's parent directory exactly:

```yaml
---
# name must match this skill's parent directory exactly
name: my-skill-name
description: This skill should be used when the user asks to "specific phrase 1", "specific phrase 2", "specific phrase 3". Include exact phrases users would say that should trigger this skill. Be concrete and specific.
---
```

Good description:
```yaml
description: This skill should be used when the user asks to "create a hook", "add a PreToolUse hook", "validate tool use", "implement prompt-based hooks", or mentions hook events (PreToolUse, PostToolUse, Stop).
```

Bad description (wrong person, vague, no triggers):
```yaml
description: Use this skill when working with hooks.
```

To write the body, cover three things: the skill's purpose in a few sentences, when it should trigger (already captured by the description above), and — most importantly — how Claude should actually use each bundled resource in practice.

**Keep SKILL.md lean:** target 1,500-2,000 words and stay under 500 lines. Move detailed content to `references/` (patterns, advanced techniques, migration guides, API references) instead of inlining it, and point to it:

```markdown
## Additional Resources
- **`references/patterns.md`** - Common patterns
- **`examples/example-script.sh`** - Working example
```

Avoid duplication: information should live in either SKILL.md or a references file, not both.

### Step 5: Validate and Test

Run the bundled validator against the new SKILL.md for mechanical checks — name matches the parent directory, description is present and ≤1024 characters, body is under ~500 lines, and every relative file reference in the body resolves to a real file:

```bash
python3 .claude/skills/skill-development/scripts/validate_skill.py path/to/skill/SKILL.md
```

Run `scripts/validate_skill.py --help` for output format and exit codes.

Pair this automated check with the **skill-reviewer** agent for the qualitative review a script can't do — trigger-phrase strength, content organization, progressive-disclosure quality:

```
Ask: "Review my skill and check if it follows best practices"
```

Also confirm: writing style is imperative/infinitive throughout, examples are complete, scripts are executable, and referenced content isn't duplicated between SKILL.md and references/.

To test triggering reliability and output quality more rigorously, write `evals/evals.json` (task-level test cases) and `evals/eval_queries.json` (labeled trigger-phrase queries) following `docs/specs/skills/eval.md` and `docs/specs/skills/optimize.md` — repo context only, these specs live outside this skill's own package. This skill's own `evals/` directory is a worked example of both files.

### Step 6: Iterate

After testing, users may request improvements — often right after using the skill, with fresh context of how it performed.

1. Use the skill on real tasks
2. Notice struggles or inefficiencies
3. Identify how SKILL.md or bundled resources should change
4. Implement changes and re-test (re-run `scripts/validate_skill.py` and any evals)

Common improvements: strengthen trigger phrases, move long sections from SKILL.md to references/, add missing examples or scripts, clarify ambiguous instructions.

## Plugin-Specific Considerations

**Skill location:** plugin skills live in the plugin's `skills/` directory:

```
my-plugin/
├── .claude-plugin/
│   └── plugin.json
├── commands/
├── agents/
└── skills/
    └── my-skill/
        ├── SKILL.md
        ├── references/
        ├── examples/
        └── scripts/
```

**Auto-discovery:** Claude Code scans `skills/` for subdirectories containing SKILL.md, always loads each skill's metadata (name + description), and loads the SKILL.md body plus any `references/` or `examples/` content only when the skill triggers.

**No packaging needed:** plugin skills ship as part of the plugin, not as separate zip files — no `package_skill.py` step.

**Testing in plugins:** install the plugin locally and confirm the skill triggers on expected queries:

```bash
cc --plugin-dir /path/to/plugin
# Ask questions that should trigger the skill and verify it loads
```

## Examples Worth Studying

Study the other skills under `.claude/skills/` in this repo as examples of best practices — don't rely on stale word counts (they drift as skills evolve; check current counts with `wc -w`, or use `scripts/validate_skill.py` for the line-count check):

- **hook-development** — keeps SKILL.md lean by moving detailed patterns to `references/`; strong, specific trigger phrases naming hook events; pairs `examples/` with `scripts/` utilities for hook validation and testing.
- **agent-development** — focused SKILL.md with strong triggers ("create an agent", "agent frontmatter"); moves the AI generation prompt and detailed examples to `references/`.
- **plugin-settings** — specific triggers (".local.md files", "YAML frontmatter"); `references/` show real implementations; ships working parsing scripts.

Each demonstrates progressive disclosure and strong triggering.

## Validation Checklist

Before finalizing a skill, confirm all of the following. Run `scripts/validate_skill.py` first — it covers the items marked (auto).

**Structure**
- [ ] (auto) SKILL.md exists with valid YAML frontmatter containing `name` and `description`
- [ ] (auto) `name` is lowercase alphanumeric-and-hyphens and matches the parent directory
- [ ] (auto) Every relative file reference in the body resolves to a real file
- [ ] Only the needed resource directories exist (`references/`, `examples/`, `scripts/`, and `assets/` if truly needed)

**Description**
- [ ] (auto) Non-empty and ≤1024 characters
- [ ] Third person ("This skill should be used when...", not "Use this skill when...")
- [ ] Includes specific trigger phrases a user would actually say, not generic ones

**Content**
- [ ] (auto) Body is under ~500 lines; target 1,500-2,000 words
- [ ] Written in imperative/infinitive form throughout, not second person ("You should...")
- [ ] Detailed content lives in `references/`, not duplicated in SKILL.md
- [ ] Examples are complete and correct; scripts are executable and documented
- [ ] SKILL.md explicitly references every bundled resource it expects Claude to use

**Testing**
- [ ] Skill triggers on the queries in `evals/eval_queries.json` (see Step 5)
- [ ] Task-level evals in `evals/evals.json` pass (see Step 5)
- [ ] Reviewed with the skill-reviewer agent

## Quick Reference

**Minimal** — simple knowledge, no complex resources:
```
skill-name/
└── SKILL.md
```

**Standard** (recommended for most plugin skills):
```
skill-name/
├── SKILL.md
├── references/
│   └── detailed-guide.md
└── examples/
    └── working-example.sh
```

**Complete** — complex domains needing validation utilities:
```
skill-name/
├── SKILL.md
├── references/
│   ├── patterns.md
│   └── advanced.md
├── examples/
│   ├── example1.sh
│   └── example2.json
└── scripts/
    └── validate.sh
```

## Additional Resources

### Sibling Skills (repo context only)

These live alongside this skill under `.claude/skills/` — outside this skill's own package, so they are **not** bundled resources or resolvable relative skill references from this SKILL.md. Read them directly in the repo:

- `hook-development/` — progressive disclosure, utility scripts
- `agent-development/` — AI-assisted creation, references
- `mcp-integration/` — comprehensive references
- `plugin-settings/` — real-world examples
- `command-development/` — clear critical concepts
- `plugin-structure/` — good organization

### Reference Files

For the complete generic skill-creator methodology:
- **`references/skill-creator-original.md`** - Full original skill-creator content

### Validation Script

- **`scripts/validate_skill.py`** - Automated SKILL.md structural checks (see Step 5)

### External Resources

- **Extend Claude with skills**: https://code.claude.com/docs/en/skills
- **Agent Skills in the SDK**: https://code.claude.com/docs/en/agent-sdk/skills

## Cross-host caveat

Skills from this repo also install in GitHub Copilot CLI, which reads `name`, `description`,
`allowed-tools`, `license`, `compatibility`, and `metadata` — and **silently ignores**
Claude-only extensions. The one that changes behavior is `disable-model-invocation`: a skill
meant to be explicit-invocation-only becomes auto-invocable in Copilot. When you set it, also
state the constraint in the skill **body** so the model self-restricts. Check with
`python3 .github/scripts/check-host-compat.py`; see the `host-portability` skill.
