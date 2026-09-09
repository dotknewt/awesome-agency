# ludus-toolkit

Ludus cyber-range toolkit — skills for the Ludus CLI, range configuration,
environment guidance, troubleshooting, and OS template maintenance, plus a
bundled MCP server for driving the Ludus API from Claude Code or OpenCode.

Components (shared pools in this repo):
- Skills: [`change-template-input-language`](../../skills/change-template-input-language), [`ludus-cli`](../../skills/ludus-cli), [`ludus-environment-guide`](../../skills/ludus-environment-guide), [`ludus-range-config`](../../skills/ludus-range-config), [`ludus-troubleshoot`](../../skills/ludus-troubleshoot), [`update-os-template`](../../skills/update-os-template)
- MCP server: [`mcp/ludus`](./mcp/ludus) (vendored in this bundle)

Claude Code install: `claude plugin install ludus-toolkit@awesome-agency`

OpenCode install: see [`opencode/README.md`](./opencode/README.md) for the
project-local skill installer, direct Docker MCP configuration, credentials,
networking, and verification.
