# memory-mcp

Persistent knowledge-graph memory for Claude — packages the official MCP
reference [Knowledge Graph Memory Server](https://github.com/modelcontextprotocol/servers/tree/main/src/memory)
as a Docker image, run through the Docker MCP Gateway.

Components:
- MCP server: [`mcp/memory`](./mcp/memory) (vendored in this bundle)

# This is a "file catalog" attached to a profile and consumed by the gateway:
#   docker mcp gateway run --profile <profile-id>
#
# Before using it:
#   1. Build the image:  docker build -t memory-mcp:local .
#   2. Create a profile and attach this catalog. No secrets or profile config
#      needed — this server is fully local and makes no network calls:
#        docker mcp profile create --name memory
# 	     cp memory-catalog.yaml $HOME/.docker/mcp/catalogs/memory-catalog.yaml
#        docker mcp profile server add memory --server file://memory-catalog.yaml
#   3. Run the gateway:
#        docker mcp gateway run --profile memory
#
# Persistence: the knowledge graph is a JSONL file at MEMORY_FILE_PATH (set
# below to /data/memory.jsonl), which lives on the named Docker volume
# memory-mcp-data, so it survives container restarts and image rebuilds.

Install: `claude plugin install memory-mcp@awesome-agency`
