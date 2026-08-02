---
name: hook-development
description: This skill should be used when the user asks to "create a hook", "add a PreToolUse/PostToolUse/Stop hook", "validate tool use", "implement prompt-based hooks", "use ${CLAUDE_PLUGIN_ROOT}", "set up event-driven automation", "block dangerous commands", or mentions hook events (PreToolUse, PostToolUse, Stop, SubagentStop, SessionStart, SessionEnd, UserPromptSubmit, PreCompact, Notification). Provides comprehensive guidance for creating and implementing Claude Code plugin hooks, covering both prompt-based (LLM-evaluated) and command (bash) hooks, plus working example scripts and validation/testing/linting tooling for command hooks.
metadata:
  version: "0.1.0"
---

# Hook Development for Claude Code Plugins

## Overview

Hooks are event-driven automation scripts that execute in response to Claude Code events. Use hooks to validate operations, enforce policies, add context, and integrate external tools into workflows.

**Key capabilities:**
- Validate tool calls before execution (PreToolUse)
- React to tool results (PostToolUse)
- Enforce completion standards (Stop, SubagentStop)
- Load project context (SessionStart)
- Automate workflows across the development lifecycle

## Hook Types

### Prompt-Based Hooks (best for complex, context-dependent logic)

Use LLM-driven decision making for context-aware validation:

```json
{
  "type": "prompt",
  "prompt": "Evaluate if this tool use is appropriate: $TOOL_INPUT",
  "timeout": 30
}
```

**Supported events:** Stop, SubagentStop, UserPromptSubmit, PreToolUse

**Benefits:** context-aware decisions, no bash scripting required, better edge-case handling, easier to extend.

### Command Hooks

Execute bash commands for deterministic checks:

```json
{
  "type": "command",
  "command": "bash ${CLAUDE_PLUGIN_ROOT}/scripts/validate.sh",
  "timeout": 60
}
```

**Use for:** fast deterministic validations, file system operations, external tool integrations, performance-critical checks.

## Hook Configuration Formats

### Plugin hooks.json Format

**For plugin hooks** in `hooks/hooks.json`, use the wrapper format — a required `hooks` key wrapping the actual events, with an optional `description`:

```json
{
  "description": "Validation hooks for code quality",
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/hooks/validate.sh"
          }
        ]
      }
    ]
  }
}
```

This is the **plugin-specific format**. `scripts/validate-hook-schema.sh` auto-detects it.

### Settings Format (Direct)

**For user settings** in `.claude/settings.json`, events go directly at the top level — no wrapper, no `description`:

```json
{
  "PreToolUse": [...],
  "Stop": [...],
  "SessionStart": [...]
}
```

**Important:** The event structures shown throughout this file are what goes *inside* either format. For plugin `hooks.json`, wrap them in `{"hooks": {...}}`.

## Hook Events

| Event | Fires | Use for | Notes |
|-------|-------|---------|-------|
| **PreToolUse** | Before any tool runs | Approve, deny, or modify tool calls | Supports prompt hooks. Output: `hookSpecificOutput.permissionDecision` (`allow`\|`deny`\|`ask`), optional `updatedInput` |
| **PostToolUse** | After a tool completes | React to results, feedback, logging | Supports prompt hooks |
| **Stop** | Main agent considers stopping | Validate completeness before stopping | Supports prompt hooks. Output: `{"decision": "approve"|"block", "reason": "..."}` |
| **SubagentStop** | Subagent considers stopping | Validate subagent task completion | Same output shape as Stop |
| **UserPromptSubmit** | User submits a prompt | Add context, validate, or block prompts | Supports prompt hooks |
| **SessionStart** | Session begins | Load project context, set env vars | Can write to `$CLAUDE_ENV_FILE` (see below); see `examples/load-context.sh` |
| **SessionEnd** | Session ends | Cleanup, logging, state preservation | Command hooks only |
| **PreCompact** | Before context compaction | Preserve critical information | Command hooks only |
| **Notification** | Claude sends a notification | React to or log notifications | Command hooks only |

For full worked JSON examples of every event (prompt-based and command), see `references/patterns.md` and `references/migration.md`.

**Example (PreToolUse, prompt-based):**
```json
{
  "PreToolUse": [
    {
      "matcher": "Write|Edit",
      "hooks": [
        {
          "type": "prompt",
          "prompt": "Validate file write safety. Check: system paths, credentials, path traversal, sensitive content. Return 'approve' or 'deny'."
        }
      ]
    }
  ]
}
```

**Persisting environment variables from SessionStart:**
```bash
echo "export PROJECT_TYPE=nodejs" >> "$CLAUDE_ENV_FILE"
```

## Hook Output Format

### Standard Output (All Hooks)

```json
{
  "continue": true,
  "suppressOutput": false,
  "systemMessage": "Message for Claude"
}
```

- `continue`: If false, halt processing (default true)
- `suppressOutput`: Hide output from transcript (default false)
- `systemMessage`: Message shown to Claude

### Exit Codes

- `0` - Success (stdout shown in transcript)
- `2` - Blocking error (stderr fed back to Claude)
- Other - Non-blocking error

**The two decision-output paths are not interchangeable — pick one per decision:**

- **Deny/block via exit 2:** Write a short plain-text reason to stderr, then `exit 2`. Claude Code surfaces stderr as plain text; it is **not** parsed as JSON, so don't put `hookSpecificOutput`/`permissionDecision` JSON here.
- **Structured decision (`allow`/`deny`/`ask`, `updatedInput`, `systemMessage`) via exit 0:** Write the JSON to **stdout**, then `exit 0`. This is the only path that gets parsed as structured output — it's also the only way to express `ask`, since exit 2 can only block.

See `examples/validate-bash.sh` and `examples/validate-write.sh` for both paths used correctly in the same script.

## Hook Input Format

All hooks receive JSON via stdin with common fields:

```json
{
  "session_id": "abc123",
  "transcript_path": "/path/to/transcript.txt",
  "cwd": "/current/working/dir",
  "permission_mode": "ask|allow",
  "hook_event_name": "PreToolUse"
}
```

**Event-specific fields:**

- **PreToolUse/PostToolUse:** `tool_name`, `tool_input`, `tool_result`
- **UserPromptSubmit:** `user_prompt`
- **Stop/SubagentStop:** `reason`

Access fields in prompts using `$TOOL_INPUT`, `$TOOL_RESULT`, `$USER_PROMPT`, etc. In command hooks, parse stdin JSON with `jq` (e.g. `jq -r '.session_id'`). Use `session_id` — never `$$` — to key any state shared across separate hook invocations; each invocation is its own bash process, so `$$` differs every time. See `references/advanced.md`.

## Environment Variables

Available in all command hooks:

- `$CLAUDE_PROJECT_DIR` - Project root path
- `$CLAUDE_PLUGIN_ROOT` - Plugin directory (use for portable paths)
- `$CLAUDE_ENV_FILE` - SessionStart only: persist env vars here
- `$CLAUDE_CODE_REMOTE` - Set if running in remote context

**Always use ${CLAUDE_PLUGIN_ROOT} in hook commands for portability:**

```json
{
  "type": "command",
  "command": "bash ${CLAUDE_PLUGIN_ROOT}/scripts/validate.sh"
}
```

Plugin `hooks/hooks.json` events merge with the user's own hooks and run in parallel.

## Matchers

### Tool Name Matching

- **Exact match:** `"matcher": "Write"`
- **Multiple tools:** `"matcher": "Read|Write|Edit"`
- **Wildcard (all tools):** `"matcher": "*"`
- **Regex patterns:** `"matcher": "mcp__.*__delete.*"` (all MCP delete tools)

**Note:** Matchers are case-sensitive.

### Common Patterns

```json
// All MCP tools
"matcher": "mcp__.*"

// Specific plugin's MCP tools
"matcher": "mcp__plugin_asana_.*"

// All file operations
"matcher": "Read|Write|Edit"

// Bash commands only
"matcher": "Bash"
```

## Security Best Practices

- **Validate all inputs** in command hooks — check that required fields aren't empty before using them.
- **Check path safety** — deny path traversal (`..`), system directories (`/etc`, `/sys`, `/usr`), and sensitive files (`.env`, `secret`, `credentials`).
- **Quote all bash variables**: `"$file_path"`, not `$file_path` — unquoted variables are an injection risk.
- **Set appropriate timeouts**: defaults are 60s for command hooks, 30s for prompt hooks.
- **Use the correct decision-output channel** (see Exit Codes above) — mixing up stdout/exit-0 JSON and stderr/exit-2 plain text is the single most common hook bug in practice.

See `examples/validate-write.sh` and `examples/validate-bash.sh` for complete, working implementations of these checks, and `references/advanced.md`'s Security Patterns section for rate limiting, audit logging, and secret detection.

## Performance Considerations

### Parallel Execution

All matching hooks run **in parallel** — they don't see each other's output, execution order is non-deterministic, and hooks should be designed for independence. Don't rely on one hook's side effects being visible to another hook in the same event.

### Optimization

1. Use command hooks for quick deterministic checks
2. Use prompt hooks for complex reasoning
3. Cache validation results in temp files (keyed off `session_id`, not `$$`)
4. Minimize I/O in hot paths

## Temporarily Active Hooks

Hooks can activate conditionally by checking for a flag file or project configuration at the top of the script, exiting 0 immediately when disabled. See `references/patterns.md` (Pattern 9: Temporarily Active Hooks, Pattern 10: Configuration-Driven Hooks) for the full flag-file and config-driven implementations. Document the activation mechanism in your plugin README, and remember Claude Code must be restarted to pick up hook changes (see below).

## Hook Lifecycle and Limitations

### Hooks Load at Session Start

**Important:** Hooks are loaded when Claude Code session starts. Changes to hook configuration require restarting Claude Code.

**Cannot hot-swap hooks:**
- Editing `hooks/hooks.json` won't affect current session
- Adding new hook scripts won't be recognized
- Changing hook commands/prompts won't update
- Must restart Claude Code: exit and run `claude` again

**To test hook changes:**
1. Edit hook configuration or scripts
2. Exit Claude Code session
3. Restart: `claude` or `cc`
4. New hook configuration loads
5. Test hooks with `claude --debug`

### Hook Validation at Startup

Hooks are validated when Claude Code starts:
- Invalid JSON in hooks.json causes loading failure
- Missing scripts cause warnings
- Syntax errors reported in debug mode

Use `/hooks` command to review loaded hooks in current session.

## Debugging Hooks

**Enable debug mode:** `claude --debug` — look for hook registration, execution logs, input/output JSON, and timing information.

**Test command hooks directly:**
```bash
echo '{"tool_name": "Write", "tool_input": {"file_path": "/test"}}' | \
  bash ${CLAUDE_PLUGIN_ROOT}/scripts/validate.sh
echo "Exit code: $?"
```

**Validate JSON output:**
```bash
output=$(./your-hook.sh < test-input.json)
echo "$output" | jq .
```

Or use the bundled `scripts/test-hook.sh`, which does this plus timing, environment setup, and exit-code interpretation — see below.

## Additional Resources

### Reference Files

For detailed patterns, migration guidance, and a Quick Reference (event summary table, DO/DON'T checklist), consult:

- **`references/patterns.md`** - Common hook patterns (10+ proven patterns) and Quick Reference
- **`references/migration.md`** - Migrating from basic to advanced hooks
- **`references/advanced.md`** - Advanced use cases: state sharing via `session_id`, external integrations, security patterns

### Example Hook Scripts

Working examples in `examples/`:

- **`validate-write.sh`** - File write validation (deny + ask paths)
- **`validate-bash.sh`** - Bash command validation (deny + ask paths)
- **`load-context.sh`** - SessionStart context loading example

### Utility Scripts

Development tools in `scripts/` (each supports `-h`/`--help`):

- **`validate-hook-schema.sh`** - Validate hooks.json structure and syntax (auto-detects plugin vs. settings format)
- **`test-hook.sh`** - Test hooks with sample input before deployment
- **`hook-linter.sh`** - Check hook scripts for common issues, including the stdout/stderr decision-output bug

See `scripts/README.md` for full usage and a typical workflow.

### External Resources

- **Official Docs**: https://code.claude.com/docs/en/hooks
- **Automate actions with hooks (guide)**: https://code.claude.com/docs/en/hooks-guide
- **Routines**: https://code.claude.com/docs/en/routines
- **Scheduled tasks (`/loop`)**: https://code.claude.com/docs/en/scheduled-tasks
- **Desktop scheduled tasks**: https://code.claude.com/docs/en/desktop-scheduled-tasks
- **Testing**: Use `claude --debug` for detailed logs
- **Validation**: Use `jq` to validate hook JSON output

## Implementation Workflow

To implement hooks in a plugin:

1. Identify events to hook into (PreToolUse, Stop, SessionStart, etc.)
2. Decide between prompt-based (flexible) or command (deterministic) hooks
3. Write hook configuration in `hooks/hooks.json`
4. For command hooks, create hook scripts — lint with `scripts/hook-linter.sh`
5. Use ${CLAUDE_PLUGIN_ROOT} for all file references
6. Validate configuration with `scripts/validate-hook-schema.sh hooks/hooks.json`
7. Test hooks with `scripts/test-hook.sh` before deployment
8. Test in Claude Code with `claude --debug`
9. Document hooks in plugin README

Use prompt-based hooks for complex, context-dependent logic where the LLM's reasoning helps (see Hook Types above). Reserve command hooks for performance-critical or purely deterministic checks — and when you do, validate and lint them with the bundled `scripts/`.
