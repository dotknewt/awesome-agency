---
name: command-development
description: Use this skill for the legacy `.claude/commands/` file-based slash command format specifically — when the user asks to "create a slash command", "add a command", "write a custom command", "define command arguments", "use command frontmatter", "organize commands", "create command with file references", "interactive command", "use AskUserQuestion in command", or needs guidance on slash command structure, YAML frontmatter fields, dynamic arguments, bash execution in commands, user interaction patterns, or command development best practices for Claude Code. For the modern `.claude/skills/<name>/SKILL.md` format, use the skill-development skill instead.
metadata:
  version: "0.2.0"
---

# Command Development for Claude Code

> **Note:** The `.claude/commands/` directory is a legacy format. For new skills, use the `.claude/skills/<name>/SKILL.md` directory format. Both are loaded identically — the only difference is file layout. See the `skill-development` skill for the preferred format.

## Overview

Slash commands are frequently-used prompts defined as Markdown files that Claude executes during interactive sessions. Understanding command structure, frontmatter options, and dynamic features enables creating powerful, reusable workflows.

**Key concepts:**

- Markdown file format for commands
- YAML frontmatter for configuration
- Dynamic arguments and file references
- Bash execution for context
- Command organization and namespacing

## Command Basics

### What is a Slash Command?

A slash command is a Markdown file containing a prompt that Claude executes when invoked. Commands provide:

- **Reusability**: Define once, use repeatedly
- **Consistency**: Standardize common workflows
- **Sharing**: Distribute across team or projects
- **Efficiency**: Quick access to complex prompts

### Critical: Commands are Instructions FOR Claude

**Commands are written for agent consumption, not human consumption.**

When a user invokes `/command-name`, the command content becomes Claude's instructions. Write commands as directives TO Claude about what to do, not as messages TO the user.

**Correct approach (instructions for Claude):**

```markdown
Review this code for security vulnerabilities including:

- SQL injection
- XSS attacks
- Authentication issues

Provide specific line numbers and severity ratings.
```

**Incorrect approach (messages to user):**

```markdown
This command will review your code for security issues.
You'll receive a report with vulnerability details.
```

The first example tells Claude what to do. The second tells the user what will happen but doesn't instruct Claude. Always use the first approach.

### Command Locations

**Project commands** (shared with team):

- Location: `.claude/commands/`
- Scope: Available in specific project
- Label: Shown as "(project)" in `/help`
- Use for: Team workflows, project-specific tasks

**Personal commands** (available everywhere):

- Location: `~/.claude/commands/`
- Scope: Available in all projects
- Label: Shown as "(user)" in `/help`
- Use for: Personal workflows, cross-project utilities

**Plugin commands** (bundled with plugins):

- Location: `plugin-name/commands/`
- Scope: Available when plugin installed
- Label: Shown as "(plugin-name)" in `/help`
- Use for: Plugin-specific functionality

## File Format

### Basic Structure

Commands are Markdown files with `.md` extension:

```
.claude/commands/
├── review.md           # /review command
├── test.md             # /test command
└── deploy.md           # /deploy command
```

**Simple command:**

```markdown
Review this code for security vulnerabilities including:

- SQL injection
- XSS attacks
- Authentication bypass
- Insecure data handling
```

No frontmatter needed for basic commands.

### With YAML Frontmatter

Add configuration using YAML frontmatter:

```markdown
---
description: Review code for security issues
allowed-tools: Read, Grep, Bash(git:*)
model: sonnet
---

Review this code for security vulnerabilities...
```

## YAML Frontmatter Fields

### description

**Purpose:** Brief description shown in `/help`
**Type:** String
**Default:** First line of command prompt

```yaml
---
description: Review pull request for code quality
---
```

**Best practice:** Clear, actionable description (under 60 characters)

### allowed-tools

**Purpose:** Specify which tools command can use
**Type:** String or Array
**Default:** Inherits from conversation

```yaml
---
allowed-tools: Read, Write, Edit, Bash(git:*)
---
```

**Patterns:**

- `Read, Write, Edit` - Specific tools
- `Bash(git:*)` - Bash with git commands only
- `*` - All tools (rarely needed)

**Use when:** Command requires specific tool access

### model

**Purpose:** Specify model for command execution
**Type:** String (sonnet, opus, haiku)
**Default:** Inherits from conversation

```yaml
---
model: haiku
---
```

**Use cases:**

- `haiku` - Fast, simple commands
- `sonnet` - Standard workflows
- `opus` - Complex analysis

### argument-hint

**Purpose:** Document expected arguments for autocomplete
**Type:** String
**Default:** None

```yaml
---
argument-hint: [pr-number] [priority] [assignee]
---
```

**Benefits:**

- Helps users understand command arguments
- Improves command discovery
- Documents command interface

### disable-model-invocation

**Purpose:** Prevent SlashCommand tool from programmatically calling command
**Type:** Boolean
**Default:** false

```yaml
---
disable-model-invocation: true
---
```

**Use when:** Command should only be manually invoked

## Dynamic Arguments

### Using $ARGUMENTS

Capture all arguments as single string:

```markdown
---
description: Fix issue by number
argument-hint: [issue-number]
---

Fix issue #$ARGUMENTS following our coding standards and best practices.
```

**Usage:**

```
> /fix-issue 123
> /fix-issue 456
```

**Expands to:**

```
Fix issue #123 following our coding standards...
Fix issue #456 following our coding standards...
```

### Using Positional Arguments

Capture individual arguments with `$1`, `$2`, `$3`, etc.:

```markdown
---
description: Review PR with priority and assignee
argument-hint: [pr-number] [priority] [assignee]
---

Review pull request #$1 with priority level $2.
After review, assign to $3 for follow-up.
```

**Usage:**

```
> /review-pr 123 high alice
```

**Expands to:**

```
Review pull request #123 with priority level high.
After review, assign to alice for follow-up.
```

### Combining Arguments

Mix positional and remaining arguments:

```markdown
Deploy $1 to $2 environment with options: $3
```

**Usage:**

```
> /deploy api staging --force --skip-tests
```

**Expands to:**

```
Deploy api to staging environment with options: --force --skip-tests
```

## File References

### Using @ Syntax

Include file contents in command:

```markdown
---
description: Review specific file
argument-hint: [file-path]
---

Review @$1 for:

- Code quality
- Best practices
- Potential bugs
```

**Usage:**

```
> /review-file src/api/users.ts
```

**Effect:** Claude reads `src/api/users.ts` before processing command

### Multiple File References

Reference multiple files:

```markdown
Compare @src/old-version.js with @src/new-version.js

Identify:

- Breaking changes
- New features
- Bug fixes
```

### Static File References

Reference known files without arguments:

```markdown
Review @package.json and @tsconfig.json for consistency

Ensure:

- TypeScript version matches
- Dependencies are aligned
- Build configuration is correct
```

## Bash Execution in Commands

Commands can execute bash commands inline to dynamically gather context before Claude processes the command. This is useful for including repository state, environment information, or project-specific context.

**When to use:**

- Include dynamic context (git status, environment vars, etc.)
- Gather project/repository state
- Build context-aware workflows

**Implementation details:**
For complete syntax, examples, and best practices, see `references/plugin-features-reference.md` section on bash execution. The reference includes the exact syntax and multiple working examples to avoid execution issues

## Interactive Commands (AskUserQuestion)

Some commands need a user decision that doesn't map cleanly to a positional argument — picking between options with trade-offs, multi-selecting features, or running an adaptive setup wizard. For these, have the command call the **AskUserQuestion** tool instead of parsing free-form arguments.

**Use AskUserQuestion when:** the choice needs explanation, there are multiple options to weigh, or the user should be able to select more than one item (`multiSelect: true`).

**Prefer arguments instead when:** the value is simple and already known (a file path, a number, a name), or the command needs to stay scriptable/fast.

```markdown
---
description: Interactive plugin setup
allowed-tools: AskUserQuestion, Write
---

Use the AskUserQuestion tool to ask:
- question: "Which deployment platform will you use?"
  header: "Deploy to"
  options: AWS, GCP, Azure, Local

Based on the answer, generate the matching configuration file.
```

Include `AskUserQuestion` in `allowed-tools` so the command is permitted to call it. Keep questions to 2-4 options with a short (max 12 char) header, and ask 1-4 questions per call.

For question-design guidelines, multi-stage and conditional question flows, and a full worked example, see `references/interactive-commands.md`.

## Command Organization

### Flat Structure

Simple organization for small command sets:

```
.claude/commands/
├── build.md
├── test.md
├── deploy.md
├── review.md
└── docs.md
```

**Use when:** 5-15 commands, no clear categories

### Namespaced Structure

Organize commands in subdirectories:

```
.claude/commands/
├── ci/
│   ├── build.md        # /build (project:ci)
│   ├── test.md         # /test (project:ci)
│   └── lint.md         # /lint (project:ci)
├── git/
│   ├── commit.md       # /commit (project:git)
│   └── pr.md           # /pr (project:git)
└── docs/
    ├── generate.md     # /generate (project:docs)
    └── publish.md      # /publish (project:docs)
```

**Benefits:**

- Logical grouping by category
- Namespace shown in `/help`
- Easier to find related commands

**Use when:** 15+ commands, clear categories

## Best Practices

### Command Design

1. **Single responsibility:** One command, one task
2. **Clear descriptions:** Self-explanatory in `/help`
3. **Explicit dependencies:** Use `allowed-tools` when needed
4. **Document arguments:** Always provide `argument-hint`
5. **Consistent naming:** Use verb-noun pattern (review-pr, fix-issue)

### Argument Handling

1. **Validate arguments:** Check for required arguments in prompt
2. **Provide defaults:** Suggest defaults when arguments missing
3. **Document format:** Explain expected argument format
4. **Handle edge cases:** Consider missing or invalid arguments

```markdown
---
argument-hint: [pr-number]
---

Check argument: !`test -n "$1" && echo "PROVIDED" || echo "MISSING"`

If the check above reports MISSING, reply only with:
"Please provide a PR number. Usage: /review-pr [number]"
and stop.

Otherwise, review PR #$1.
```

Note: there is no `$IF(...)` macro in Claude Code — arguments are substituted as plain text before Claude ever sees the prompt. Express conditionals as a bash check inside a `!` block followed by plain-language branching instructions, as shown above.

### File References

1. **Explicit paths:** Use clear file paths
2. **Check existence:** Handle missing files gracefully
3. **Relative paths:** Use project-relative paths
4. **Glob support:** Consider using Glob tool for patterns

### Bash Commands

1. **Limit scope:** Use `Bash(git:*)` not `Bash(*)`
2. **Safe commands:** Avoid destructive operations
3. **Handle errors:** Consider command failures
4. **Keep fast:** Long-running commands slow invocation

### Documentation

1. **Add comments:** Explain complex logic
2. **Provide examples:** Show usage in comments
3. **List requirements:** Document dependencies
4. **Version commands:** Note breaking changes

```markdown
---
description: Deploy application to environment
argument-hint: [environment] [version]
---

<!--
Usage: /deploy [staging|production] [version]
Requires: AWS credentials configured
Example: /deploy staging v1.2.3
-->

Deploy application to $1 environment using version $2...
```

For self-documenting command templates, help-text patterns, and changelog conventions, see `references/documentation-patterns.md`.

## Common Patterns

Complete, ready-to-copy pattern examples (review, testing, documentation generation, git status, deployment) live in `examples/simple-commands.md` and `examples/plugin-commands.md` rather than being duplicated here. For multi-step workflows — sequential steps, state-carrying commands across invocations, conditional branching — see `references/advanced-workflows.md`.

## Troubleshooting

**Command not appearing:**

- Check file is in correct directory
- Verify `.md` extension present
- Ensure valid Markdown format
- Restart Claude Code

**Arguments not working:**

- Verify `$1`, `$2` syntax correct
- Check `argument-hint` matches usage
- Ensure no extra spaces

**Bash execution failing:**

- Check `allowed-tools` includes Bash
- Verify command syntax in backticks
- Test command in terminal first
- Check for required permissions

**File references not working:**

- Verify `@` syntax correct
- Check file path is valid
- Ensure Read tool allowed
- Use absolute or project-relative paths

Before releasing a command, run the validators in `scripts/` (`scripts/validate-command.sh` and `scripts/validate-frontmatter.sh`) — see `references/testing-strategies.md` for the full testing checklist and levels.

## Plugin-Specific Features

### CLAUDE_PLUGIN_ROOT Variable

Plugin commands have access to `${CLAUDE_PLUGIN_ROOT}`, an environment variable that resolves to the plugin's absolute path. Use it for every plugin-internal path — scripts, templates, configuration — instead of a relative or hardcoded path, since it's the only form that works across installations.

```markdown
---
description: Analyze using plugin script
allowed-tools: Bash(node:*)
---

Run analysis: !`node ${CLAUDE_PLUGIN_ROOT}/scripts/analyze.js $1`
Load template: @${CLAUDE_PLUGIN_ROOT}/templates/report.md
```

### Plugin Command Organization

Commands are auto-discovered from a plugin's `commands/` directory; subdirectories create `/help` namespaces (e.g. `plugin-name/commands/utils/helper.md` shows as `/helper` "(plugin:plugin-name:utils)"). Use descriptive action names and avoid generic ones (`test`, `run`) that collide with other plugins' commands.

Planning to distribute the plugin through a marketplace? See `references/marketplace-considerations.md` for naming, versioning, and configurability guidance specific to commands used by unfamiliar users.

For configuration-based, template-based, and multi-script plugin command patterns with full worked examples, see `references/plugin-features-reference.md` and `examples/plugin-commands.md`.

## Integration with Plugin Components

Commands can integrate with other plugin components:

- **Agents:** mention the agent by name and describe the task; Claude uses the Task tool to launch it. The agent must exist in `plugin/agents/`.
- **Skills:** mention the skill by name to hint that Claude should invoke it for specialized knowledge. The skill must exist in `plugin/skills/`.
- **Hooks:** commands can prepare state that hooks read, or document how to interpret hook output — hooks fire automatically on their configured event, commands cannot invoke them directly.

For worked examples of each integration type, plus multi-component workflows that combine scripts, agents, skills, and templates, see `references/plugin-features-reference.md#integration-with-plugin-components`.

## Validation Patterns

Commands should validate inputs and resources before processing — check arguments with a bash test inside a `!` block, then branch in prose ("If the check reports X... Otherwise..."), the same pattern shown under [Argument Handling](#argument-handling) above. Never use `$IF(...)` or any other macro syntax; it does not exist in Claude Code.

The full set of validation patterns (argument validation, file existence checks, plugin resource validation, output validation, graceful error handling) is documented once, in `references/plugin-features-reference.md#validation-patterns`, rather than duplicated here.

---

## Reference Files

This skill uses progressive disclosure: the sections above cover the fundamentals every command author needs. The following files go deeper on specific topics — load them when the task calls for it.

- `references/frontmatter-reference.md` — complete YAML frontmatter field specifications, validation rules, and common errors.
- `references/plugin-features-reference.md` — `${CLAUDE_PLUGIN_ROOT}`, plugin command patterns, and the full validation-patterns reference.
- `references/interactive-commands.md` — AskUserQuestion design guidance, multi-stage and conditional question flows, worked examples.
- `references/advanced-workflows.md` — multi-step command sequences, state-carrying workflows, command composition and chaining.
- `references/testing-strategies.md` — the seven testing levels, edge cases, and how to use the validators in `scripts/`.
- `references/documentation-patterns.md` — self-documenting command templates, help text, and changelog conventions.
- `references/marketplace-considerations.md` — naming, versioning, and configurability guidance for commands distributed to other users.
- `examples/simple-commands.md` and `examples/plugin-commands.md` — complete, ready-to-copy command examples.

## Cross-host caveat

GitHub Copilot CLI also installs bundles from this repo and has **no slash-command concept
at all** — skills fill that role there. Any capability shipped only as a command is
unreachable for Copilot users, so every command needs a skill counterpart or a declared
exception in `.github/host-compat.json`. This is an *error*, not a warning, in
`python3 .github/scripts/check-host-compat.py`. See the `host-portability` skill.
