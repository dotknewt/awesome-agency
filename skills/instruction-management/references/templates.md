# AGENTS.md Templates

These templates apply to `AGENTS.md` (the canonical filename) and to legacy `CLAUDE.md` files that haven't been migrated yet. The structure is the same either way — only the filename differs.

## Key Principles

- **Concise**: dense, human-readable; one line per concept when possible
- **Actionable**: commands should be copy-paste ready
- **Project-specific**: document patterns unique to this project, not generic advice
- **Current**: all info should reflect actual codebase state

---

## Recommended Sections

Use only the sections relevant to the project. Not all sections are needed.

### Commands

Document the essential commands for working with the project.

```markdown
## Commands

| Command | Description |
|---------|-------------|
| `<install command>` | Install dependencies |
| `<dev command>` | Start development server |
| `<build command>` | Production build |
| `<test command>` | Run tests |
| `<lint command>` | Lint/format code |
```

### Architecture

Describe the project structure so agents know where things live.

```markdown
## Architecture

```
<root>/
  <dir>/    # <purpose>
  <dir>/    # <purpose>
  <dir>/    # <purpose>
```
```

### Key Files

List important files that agents should know about.

```markdown
## Key Files

- `<path>` - <purpose>
- `<path>` - <purpose>
```

### Code Style

Document project-specific coding conventions.

```markdown
## Code Style

- <convention>
- <convention>
- <preference over alternative>
```

### Environment

Document required environment variables and setup.

```markdown
## Environment

Required:
- `<VAR_NAME>` - <purpose>
- `<VAR_NAME>` - <purpose>

Setup:
- <setup step>
```

### Testing

Document testing approach and commands.

```markdown
## Testing

- `<test command>` - <what it tests>
- <testing convention or pattern>
```

### Gotchas

Document non-obvious patterns, quirks, and warnings.

```markdown
## Gotchas

- <non-obvious thing that causes issues>
- <ordering dependency or prerequisite>
- <common mistake to avoid>
```

### Workflow

Document development workflow patterns.

```markdown
## Workflow

- <when to do X>
- <preferred approach for Y>
```

### Memory vs. State

Document the AGENTS.md / STATE.md split so agents know where to write durable vs. transient information.

```markdown
## Memory vs. State

- **AGENTS.md** — project north star. Stable decisions, architecture, commands, conventions. Update infrequently, only when something durable changes.
- **STATE.md** — session bookmarks and in-progress work (WIP, ToDo, recent Completed). Update every session or task switch; invoke the `state-keeper` subagent to keep it tidy.
```

---

## Template: Project Root (Minimal)

```markdown
# <Project Name>

<One-line description>

## Commands

| Command | Description |
|---------|-------------|
| `<command>` | <description> |

## Architecture

```
<structure>
```

## Gotchas

- <gotcha>

## Memory vs. State

- **AGENTS.md** — project north star. Stable decisions, architecture, commands, conventions. Update infrequently, only when something durable changes.
- **STATE.md** — session bookmarks and in-progress work (WIP, ToDo, recent Completed). Update every session or task switch; invoke the `state-keeper` subagent to keep it tidy.
```

---

## Template: Project Root (Comprehensive)

```markdown
# <Project Name>

<One-line description>

## Commands

| Command | Description |
|---------|-------------|
| `<command>` | <description> |

## Architecture

```
<structure with descriptions>
```

## Key Files

- `<path>` - <purpose>

## Code Style

- <convention>

## Environment

- `<VAR>` - <purpose>

## Testing

- `<command>` - <scope>

## Gotchas

- <gotcha>

## Memory vs. State

- **AGENTS.md** — project north star. Stable decisions, architecture, commands, conventions. Update infrequently, only when something durable changes.
- **STATE.md** — session bookmarks and in-progress work (WIP, ToDo, recent Completed). Update every session or task switch; invoke the `state-keeper` subagent to keep it tidy.
```

---

## Template: Package/Module

For packages within a monorepo or distinct modules.

```markdown
# <Package Name>

<Purpose of this package>

## Usage

```
<import/usage example>
```

## Key Exports

- `<export>` - <purpose>

## Dependencies

- `<dependency>` - <why needed>

## Notes

- <important note>
```

---

## Template: Monorepo Root

```markdown
# <Monorepo Name>

<Description>

## Packages

| Package | Description | Path |
|---------|-------------|------|
| `<name>` | <purpose> | `<path>` |

## Commands

| Command | Description |
|---------|-------------|
| `<command>` | <description> |

## Cross-Package Patterns

- <shared pattern>
- <generation/sync pattern>
```

---

## Template: Claude Code stub (Option B migration)

When migrating from `CLAUDE.md` to `AGENTS.md` while keeping Claude Code auto-load, the `CLAUDE.md` stub is exactly:

```markdown
<!-- DO NOT EDIT — see AGENTS.md -->
@AGENTS.md
```

Two lines. No content. See [migration.md](migration.md).

---

## Update Principles

When updating any memory file:

1. **Be specific**: use actual file paths, real commands from this project
2. **Be current**: verify info against the actual codebase
3. **Be brief**: one line per concept when possible
4. **Be useful**: would this help a new agent session understand the project?
