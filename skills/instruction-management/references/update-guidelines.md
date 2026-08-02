# AGENTS.md Update Guidelines

Applies to `AGENTS.md` and to legacy `CLAUDE.md` files awaiting migration.

## Core Principle

Only add information that will genuinely help future agent sessions. The context window is precious — every line must earn its place.

## Placement Rule: Root vs. Subdirectory

Before adding content to root AGENTS.md, ask: **does this apply repo-wide, or only when working under a specific directory?**

| Content type | Where it goes |
|---|---|
| Repo layout, plugin format, global build commands | Root `AGENTS.md` |
| Commands/gotchas for one package or server | `<that-dir>/AGENTS.md` |
| Detail that only matters inside `mcp/ludus/` | `mcp/ludus/AGENTS.md` |

When a subdirectory has its own AGENTS.md, add a reference in root so agents know where to look:

```markdown
## Subdirectory context
- MCP servers: @mcp/ludus/AGENTS.md
- Skills: @skills/AGENTS.md
```

This defers loading the content until an agent opens files in that area — subdirectory-specific detail doesn't bloat sessions that don't need it.

## What TO Add

### 1. Commands/Workflows Discovered

```markdown
## Build

`npm run build:prod` - Full production build with optimization
`npm run build:dev` - Fast dev build (no minification)
```

Why: saves future sessions from rediscovering these.

### 2. Gotchas and Non-Obvious Patterns

```markdown
## Gotchas

- Tests must run sequentially (`--runInBand`) due to shared DB state
- `yarn.lock` is authoritative; delete `node_modules` if deps mismatch
```

Why: prevents repeated debugging sessions.

### 3. Package Relationships

```markdown
## Dependencies

The `auth` module depends on `crypto` being initialized first.
Import order matters in `src/bootstrap.ts`.
```

Why: architecture knowledge that isn't obvious from code.

### 4. Testing Approaches That Worked

```markdown
## Testing

For API endpoints: Use `supertest` with the test helper in `tests/setup.ts`
Mocking: Factory functions in `tests/factories/` (not inline mocks)
```

Why: establishes patterns that work.

### 5. Configuration Quirks

```markdown
## Config

- `NEXT_PUBLIC_*` vars must be set at build time, not runtime
- Redis connection requires `?family=0` suffix for IPv6
```

Why: environment-specific knowledge.

### 6. Memory vs. State Split

```markdown
## Memory vs. State

- **AGENTS.md** — project north star. Stable decisions, architecture, commands, conventions. Update infrequently, only when something durable changes.
- **STATE.md** — session bookmarks and in-progress work (WIP, ToDo, recent Completed). Update every session or task switch; invoke the `state-keeper` subagent to keep it tidy.
```

Why: makes the write-frequency boundary explicit so agents don't conflate durable instructions with transient task state.

## What NOT to Add

### 1. Obvious Code Info

Bad:
```markdown
The `UserService` class handles user operations.
```

The class name already tells us this.

### 2. Generic Best Practices

Bad:
```markdown
Always write tests for new features.
Use meaningful variable names.
```

This is universal advice, not project-specific.

### 3. One-Off Fixes

Bad:
```markdown
We fixed a bug in commit abc123 where the login button didn't work.
```

Won't recur; clutters the file.

### 4. Verbose Explanations

Bad:
```markdown
The authentication system uses JWT tokens. JWT (JSON Web Tokens) are
an open standard (RFC 7519) that defines a compact and self-contained
way for securely transmitting information between parties as a JSON
object. In our implementation, we use the HS256 algorithm which...
```

Good:
```markdown
Auth: JWT with HS256, tokens in `Authorization: Bearer <token>` header.
```

## Diff Format for Updates

For each suggested change:

### 1. Identify the File

```
File: ./AGENTS.md
Section: Commands (new section after ## Architecture)
```

### 2. Show the Change

```diff
 ## Architecture
 ...

+## Commands
+
+| Command | Purpose |
+|---------|---------|
+| `npm run dev` | Dev server with HMR |
+| `npm run build` | Production build |
+| `npm test` | Run test suite |
```

### 3. Explain Why

> **Why this helps:** the build commands weren't documented, causing
> confusion about how to run the project. This saves future sessions
> from needing to inspect `package.json`.

## Editing a legacy CLAUDE.md

If the repo hasn't migrated to `AGENTS.md` yet:
- Default to **proposing migration first** (see [migration.md](migration.md)).
- If the user defers the migration, edit `CLAUDE.md` directly with the same diff format above.
- Never edit a `CLAUDE.md` stub (one containing only `@AGENTS.md`). Stubs are intentionally empty — edit `AGENTS.md` instead.

## Validation Checklist

Before finalizing an update, verify:

- [ ] Each addition is project-specific
- [ ] Content is not more suited in a content-specific subdirectory AGENTS.md
- [ ] No generic advice or obvious info
- [ ] Commands are tested and work
- [ ] File paths are accurate
- [ ] Would a new agent session find this helpful — e.g. spare it an Explore subagent or ad-hoc Glob/Grep search?
- [ ] Is this the most concise way to express the info?
- [ ] Editing the correct file (AGENTS.md, not a CLAUDE.md stub)?
