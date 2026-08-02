---
name: mcp-integration
description: This skill should be used when the user asks to "add MCP server", "integrate MCP", "configure MCP in plugin", "use .mcp.json", "set up Model Context Protocol", "connect external service", mentions "${CLAUDE_PLUGIN_ROOT} with MCP", or discusses MCP server types (SSE, stdio, HTTP, WebSocket). Provides comprehensive guidance for integrating Model Context Protocol servers into Claude Code plugins for external tool and service integration.
metadata:
  version: 0.1.0
---

# MCP Integration for Claude Code Plugins

## Overview

Model Context Protocol (MCP) enables Claude Code plugins to integrate with external services and APIs by providing structured tool access. Use MCP integration to expose external service capabilities as tools within Claude Code.

**Key capabilities:**
- Connect to external services (databases, APIs, file systems)
- Provide 10+ related tools from a single service
- Handle OAuth and complex authentication flows
- Bundle MCP servers with plugins for automatic setup

## MCP Server Configuration Methods

Plugins can bundle MCP servers in two ways:

### Method 1: Dedicated .mcp.json (Recommended)

Create `.mcp.json` at plugin root:

```json
{
  "database-tools": {
    "command": "${CLAUDE_PLUGIN_ROOT}/servers/db-server",
    "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"],
    "env": {
      "DB_URL": "${DB_URL}"
    }
  }
}
```

**Benefits:**
- Clear separation of concerns
- Easier to maintain
- Better for multiple servers

### Method 2: Inline in plugin.json

Add `mcpServers` field to plugin.json:

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "mcpServers": {
    "plugin-api": {
      "command": "${CLAUDE_PLUGIN_ROOT}/servers/api-server",
      "args": ["--port", "8080"]
    }
  }
}
```

**Benefits:**
- Single configuration file
- Good for simple single-server plugins

## MCP Server Types

MCP servers connect via one of four transports. Full configuration options, lifecycle details, and troubleshooting for each live in **`references/server-types.md`** — read it before configuring anything non-trivial.

| Type | Transport | Best For | Auth |
|------|-----------|----------|------|
| stdio | Local process | Local tools, custom/NPM servers, servers bundled with the plugin | Env vars |
| HTTP | HTTP request/response (**recommended for remote servers**) | Hosted services, REST APIs, OAuth or token auth | OAuth or tokens |
| SSE | HTTP + Server-Sent Events — **deprecated**, use HTTP instead | Legacy hosted servers that haven't migrated off SSE yet | OAuth or tokens |
| ws | WebSocket | Real-time/streaming, low-latency, bidirectional push | Tokens |

**Quick picks:**
- Bundling a server with your plugin? Use **stdio** with `${CLAUDE_PLUGIN_ROOT}`.
- Connecting to a hosted/cloud service (including OAuth-based ones)? Use **HTTP** (`type: "http"`) — this is the current recommended transport for remote MCP servers. Only use `type: "sse"` for a server that hasn't migrated off the legacy transport.
- Need real-time push updates? Use **WebSocket** (`type: "ws"`).

**Minimal examples:**
```json
{
  "filesystem": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "${CLAUDE_PROJECT_DIR}"]
  },
  "api-service": {
    "type": "http",
    "url": "https://api.example.com/mcp",
    "headers": { "Authorization": "Bearer ${API_TOKEN}" }
  }
}
```

`type: "http"` also accepts `streamable-http` as an alias — the MCP spec's own name for this transport — so configs copied from third-party server docs work unmodified.

## Environment Variable Expansion

All MCP configurations support environment variable substitution:

**${CLAUDE_PLUGIN_ROOT}** - Plugin's own install directory (always use for portability). Appropriate for paths to files the plugin ships with, e.g. a bundled stdio server binary:
```json
{
  "command": "${CLAUDE_PLUGIN_ROOT}/servers/my-server"
}
```

**${CLAUDE_PROJECT_DIR}** - Root of the user's current project/repository. Appropriate when an MCP server should operate on the user's project files rather than plugin-bundled files, e.g. scoping a filesystem server to the project being worked on:
```json
{
  "args": ["-y", "@modelcontextprotocol/server-filesystem", "${CLAUDE_PROJECT_DIR}"]
}
```

**${CLAUDE_PLUGIN_DATA}** - Persistent per-plugin data directory that survives plugin updates. Appropriate for state the server needs to keep across upgrades — caches, local databases, downloaded assets — as opposed to `${CLAUDE_PLUGIN_ROOT}`, which points at the (replaceable) install directory:
```json
{
  "args": ["--db", "${CLAUDE_PLUGIN_DATA}/cache.sqlite"]
}
```

**User environment variables** - From user's shell:
```json
{
  "env": {
    "API_KEY": "${MY_API_KEY}",
    "DATABASE_URL": "${DB_URL}"
  }
}
```

**Best practice:** Document all required environment variables in plugin README. Run `scripts/validate-mcp-config.py` to flag any `${CLAUDE_*}` variable outside this documented set (see [Testing MCP Integration](#testing-mcp-integration)).

## MCP Tool Naming

When MCP servers provide tools, they're automatically prefixed:

**Format:** `mcp__plugin_<plugin-name>_<server-name>__<tool-name>`

**Example:**
- Plugin: `asana`
- Server: `asana`
- Tool: `create_task`
- **Full name:** `mcp__plugin_asana_asana__asana_create_task`

### Using MCP Tools in Commands

Pre-allow specific MCP tools in command frontmatter:

```markdown
---
allowed-tools: [
  "mcp__plugin_asana_asana__asana_create_task",
  "mcp__plugin_asana_asana__asana_search_tasks"
]
---
```

**Wildcard (use sparingly):**
```markdown
---
allowed-tools: ["mcp__plugin_asana_asana__*"]
---
```

**Best practice:** Pre-allow specific tools, not wildcards, for security.

## Lifecycle Management

**Automatic startup:**
- MCP servers start when plugin enables
- Connection established before first tool use
- Restart required for configuration changes

**Lifecycle:**
1. Plugin loads
2. MCP configuration parsed
3. Server process started (stdio) or connection established (SSE/HTTP/WS)
4. Tools discovered and registered
5. Tools available as `mcp__plugin_...__...`

**Viewing servers:**
Use `/mcp` command to see all servers including plugin-provided ones.

## Authentication Patterns

Three patterns cover most servers — full details, troubleshooting, and advanced flows (dynamic headers, JWT, HMAC signing) are in **`references/authentication.md`**:

- **OAuth** (HTTP, or legacy SSE): just supply `type` and `url` — Claude Code handles the browser consent flow and token refresh automatically. No credentials go in the config.
- **Token-based** (HTTP/ws headers): put the token in an env var and reference it, e.g. `"Authorization": "Bearer ${API_TOKEN}"`. Document the variable in your README.
- **Environment variables** (stdio): pass credentials via the `env` map, e.g. `"env": {"DATABASE_URL": "${DB_URL}"}`.

## Integration Patterns

### Pattern 1: Simple Tool Wrapper

Commands use MCP tools with user interaction:

```markdown
# Command: create-item.md
---
allowed-tools: ["mcp__plugin_name_server__create_item"]
---

Steps:
1. Gather item details from user
2. Use mcp__plugin_name_server__create_item
3. Confirm creation
```

**Use for:** Adding validation or preprocessing before MCP calls.

### Pattern 2: Autonomous Agent

Agents use MCP tools autonomously:

```markdown
# Agent: data-analyzer.md

Analysis Process:
1. Query data via mcp__plugin_db_server__query
2. Process and analyze results
3. Generate insights report
```

**Use for:** Multi-step MCP workflows without user interaction.

### Pattern 3: Multi-Server Plugin

Integrate multiple MCP servers:

```json
{
  "github": {
    "type": "http",
    "url": "https://api.githubcopilot.com/mcp/",
    "headers": {
      "Authorization": "Bearer ${GITHUB_PAT}"
    }
  },
  "jira": {
    "type": "http",
    "url": "https://mcp.jira.com/mcp"
  }
}
```

**Use for:** Workflows spanning multiple services. Note GitHub's official hosted MCP server (`https://api.githubcopilot.com/mcp/`) uses the HTTP transport with a personal-access-token bearer header, not SSE.

## Security Best Practices

**DO:**
- ✅ Use `${CLAUDE_PLUGIN_ROOT}` / `${CLAUDE_PROJECT_DIR}` / `${CLAUDE_PLUGIN_DATA}` instead of hardcoded absolute paths
- ✅ Use environment variables for tokens and credentials
- ✅ Document required environment variables and OAuth scopes in the plugin README
- ✅ Let OAuth flow handle authentication when available
- ✅ Use secure connections — HTTPS/WSS, never HTTP/WS
- ✅ Pre-allow specific MCP tools in `allowed-tools`, not wildcards
- ✅ Test MCP integration (`/mcp`, `scripts/validate-mcp-config.py`) before publishing
- ✅ Handle connection and tool-call errors gracefully

**DON'T:**
- ❌ Hardcode tokens or absolute paths in configuration
- ❌ Commit tokens/credentials to git or share them in documentation
- ❌ Use HTTP/WS instead of HTTPS/WSS
- ❌ Pre-allow all tools with wildcards (`mcp__plugin_x__*`)
- ❌ Skip error handling or forget to document setup

```json
✅ "url": "https://mcp.example.com/mcp"
❌ "url": "http://mcp.example.com/mcp"
```

```markdown
✅ allowed-tools: ["mcp__plugin_api_server__read_data", "mcp__plugin_api_server__create_item"]
❌ allowed-tools: ["mcp__plugin_api_server__*"]
```

## Error Handling

### Connection Failures

Handle MCP server unavailability:
- Provide fallback behavior in commands
- Inform user of connection issues
- Check server URL and configuration

### Tool Call Errors

Handle failed MCP operations:
- Validate inputs before calling MCP tools
- Provide clear error messages
- Check rate limiting and quotas

### Configuration Errors

Validate MCP configuration:
- Run `scripts/validate-mcp-config.py <path-to-.mcp.json>` to catch JSON syntax errors, missing required fields, insecure (`http`/`ws`) URLs, and undocumented `${CLAUDE_*}` variables before manual testing
- Test server connectivity during development
- Check required environment variables are documented

## Performance Considerations

### Lazy Loading

MCP servers connect on-demand:
- Not all servers connect at startup
- First tool use triggers connection
- Connection pooling managed automatically

### Batching

Batch similar requests when possible:

```
# Good: Single query with filters
tasks = search_tasks(project="X", assignee="me", limit=50)

# Avoid: Many individual queries
for id in task_ids:
    task = get_task(id)
```

## Testing MCP Integration

### Local Testing

1. Configure MCP server in `.mcp.json`
2. Install plugin locally (`.claude-plugin/`)
3. Run `/mcp` to verify server appears
4. Test tool calls in commands
5. Check `claude --debug` logs for connection issues

### Validation Checklist

- [ ] `scripts/validate-mcp-config.py` passes with no errors
- [ ] MCP configuration is valid JSON
- [ ] Server URL is correct and accessible
- [ ] Required environment variables documented
- [ ] Tools appear in `/mcp` output
- [ ] Authentication works (OAuth or tokens)
- [ ] Tool calls succeed from commands
- [ ] Error cases handled gracefully

## Debugging

### Enable Debug Logging

```bash
claude --debug
```

Look for:
- MCP server connection attempts
- Tool discovery logs
- Authentication flows
- Tool call errors

### Common Issues

**Server not connecting:**
- Check URL is correct
- Verify server is running (stdio)
- Check network connectivity
- Review authentication configuration

**Tools not available:**
- Verify server connected successfully
- Check tool names match exactly
- Run `/mcp` to see available tools
- Restart Claude Code after config changes

**Authentication failing:**
- Clear cached auth tokens
- Re-authenticate
- Check token scopes and permissions
- Verify environment variables set

## Quick Reference

### MCP Server Types

| Type | Transport | Best For | Auth |
|------|-----------|----------|------|
| stdio | Process | Local tools, custom servers | Env vars |
| HTTP | REST (**recommended for remote servers**, incl. OAuth) | Hosted services, cloud APIs, API backends | OAuth or tokens |
| SSE | HTTP — **deprecated**, use HTTP instead | Legacy hosted services not yet migrated | OAuth or tokens |
| ws | WebSocket | Real-time, streaming | Tokens |

### Configuration Checklist

- [ ] Server type specified (stdio/HTTP/ws; avoid SSE for new integrations)
- [ ] Type-specific fields complete (`command` for stdio, `url`+`type` for HTTP/SSE/ws)
- [ ] Authentication configured
- [ ] Environment variables documented
- [ ] HTTPS/WSS used (not HTTP/WS)
- [ ] `${CLAUDE_PLUGIN_ROOT}` / `${CLAUDE_PROJECT_DIR}` / `${CLAUDE_PLUGIN_DATA}` used for paths, as appropriate
- [ ] `scripts/validate-mcp-config.py` passes

See [Security Best Practices](#security-best-practices) above for the DO/DON'T list.

## Additional Resources

### Reference Files

For detailed information, consult:

- **`references/server-types.md`** - Deep dive on each server type
- **`references/authentication.md`** - Authentication patterns and OAuth
- **`references/tool-usage.md`** - Using MCP tools in commands and agents

### Example Configurations

Working examples in `examples/`:

- **`stdio-server.json`** - Local stdio MCP server
- **`http-server.json`** - REST APIs and hosted services over HTTP, including the official GitHub MCP server
- **`sse-server.json`** - Legacy SSE servers (deprecated transport — prefer HTTP for new integrations)

### Scripts

- **`scripts/validate-mcp-config.py`** - Validates a `.mcp.json`/`mcpServers` block: JSON syntax, required fields per type, insecure URLs, and undocumented `${CLAUDE_*}` variables. Run with `--help` for usage.

### External Resources

- **Official MCP Docs**: https://modelcontextprotocol.io/
- **Claude Code MCP Docs**: https://code.claude.com/docs/en/mcp
- **MCP Quickstart**: https://code.claude.com/docs/en/mcp-quickstart
- **Managed MCP (org-level control)**: https://code.claude.com/docs/en/managed-mcp
- **MCP SDK**: @modelcontextprotocol/sdk
- **Testing**: Use `claude --debug` and `/mcp` command

## Implementation Workflow

To add MCP integration to a plugin:

1. Choose MCP server type — stdio for local/bundled servers, HTTP for hosted/remote servers (including OAuth), ws for real-time; avoid SSE except for legacy servers that require it
2. Create `.mcp.json` at plugin root with configuration
3. Use ${CLAUDE_PLUGIN_ROOT} / ${CLAUDE_PROJECT_DIR} / ${CLAUDE_PLUGIN_DATA} for all file references, as appropriate
4. Document required environment variables in README
5. Run `scripts/validate-mcp-config.py` and test locally with `/mcp`
6. Pre-allow MCP tools in relevant commands
7. Handle authentication (OAuth or tokens)
8. Test error cases (connection failures, auth errors)
9. Document MCP integration in plugin README

Focus on stdio for custom/local servers, HTTP for hosted services (including OAuth-based ones).
