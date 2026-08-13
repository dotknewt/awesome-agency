# mcp/memory

Node/TypeScript stdio MCP server, vendored verbatim from the official
[modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers)
`src/memory/` (pinned commit `fd8248e5`) — see `README.md`'s "Vendored from
upstream" section before editing `index.ts` or any vendored file directly.
Build/test: `npm install && npm run build && npm test` (vitest; `__tests__/*.test.ts`).

## Config injection (Docker MCP Gateway)

`memory-catalog.yaml` is the gateway **file-catalog** (`registry:` map).
Run with `docker mcp gateway run --catalog` or, via a profile,
`docker mcp gateway run --profile <profile-id>`. Unlike `mcp/ludus`, there
are no `secrets:` or `config:` blocks — `MEMORY_FILE_PATH` is a hardcoded
literal in the catalog's `env:` block (`/data/memory.jsonl`), backed by the
named volume `memory-mcp-data:/data`, because this server has no external
connection to configure.

## Gotcha

If `MEMORY_FILE_PATH` is ever removed from the catalog's `env:` block, the
server silently falls back to a path next to its own compiled entrypoint
inside the container (`dist/memory.jsonl`) — writes would then vanish on
container removal unless the volume mount is also changed to cover
`/app/dist` instead of `/data`.
