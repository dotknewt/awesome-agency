# mcp/ludus

Node/TypeScript stdio MCP server wrapping the Ludus API. Build/test: `npm install && npm run build && npm test` (tests use node's built-in runner; `*.test.ts`).

## Config injection (Docker MCP Gateway)

`ludus-catalog.yaml` is the gateway **file-catalog** (`registry:` map; flat `secrets`/`env`/`config`, where `config` is an array of objects). Run with `docker mcp gateway run --catalog`. It does not hardcode connection details:

- `api_key` → **secret**: `docker mcp secret set ludus-mcp.api_key` → `LUDUS_API_KEY`
- `url` → **profile config**: `docker mcp profile config <profile-id> --set ludus-mcp.url=https://HOST:8080`, templated as `{{ludus-mcp.url}}` → `LUDUS_URL`

The old `docker mcp config write` is gone. The catalog is attached to a profile via `docker mcp profile server add <profile-id> --server file://ludus-catalog.yaml` and the gateway is run with `docker mcp gateway run --profile <profile-id>` (no `--catalog` flag needed; mutually exclusive with `--servers`).

## Gotcha

`build/openapi.yaml` is read relative to `build/` (`src/catalog.ts`), so the `build/` tree must stay intact next to production `node_modules` (see Dockerfile runtime stage).
