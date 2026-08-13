# memory-mcp

Persistent knowledge-graph memory for Claude — packages the official MCP
reference [Knowledge Graph Memory Server](https://github.com/modelcontextprotocol/servers/tree/main/src/memory)
as a Docker image, run through the Docker MCP Gateway.

Components:
- MCP server: [`mcp/memory`](./mcp/memory) (vendored in this bundle)

Install: `claude plugin install memory-mcp@awesome-agency`
