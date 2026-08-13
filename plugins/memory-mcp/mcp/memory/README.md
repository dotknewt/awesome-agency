# Running memory-mcp with Docker + the Docker MCP Gateway

This packages the official MCP reference [Knowledge Graph Memory
Server](https://github.com/modelcontextprotocol/servers/tree/main/src/memory)
as a Docker image and runs it through the **Docker MCP Gateway**, which
launches the server in an isolated container and brokers stdio between your
AI client and the container. The server is fully local — no secrets, no
network calls — so the only config is where its knowledge-graph file lives,
which is fixed to a named Docker volume for persistence.

Files in this directory that make it work:

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage build → non-root stdio image (`node dist/index.js`) |
| `.dockerignore` | Keeps the build context clean / forces an in-image build |
| `memory-catalog.yaml` | A local "file catalog" the gateway reads directly |

Prerequisites: Docker Desktop with the MCP Toolkit (`docker mcp` CLI available).

> **Known limitation (Docker MCP Toolkit v0.43.3+):** the CLI now refuses
> any `file://` catalog reference — via `--catalog` *or*
> `docker mcp profile server add --server file://...` — that doesn't
> resolve inside `~/.docker/mcp/catalogs/`. `${CLAUDE_PLUGIN_ROOT}` can
> never point there, so on affected CLI versions this plugin's own
> `.mcp.json` will **not** auto-launch successfully — it fails with
> `reading catalog: local file path must resolve within Docker MCP
> catalogs directory`. This is a Docker Toolkit CLI restriction, not
> specific to this server (`ludus-toolkit`'s bundled MCP server hits the
> identical error on the same CLI version). Steps 1-5 below are a
> **manual workaround that is verified to work**: copy the catalog into
> the required directory once, then register the server with
> `claude mcp add` directly instead of relying on plugin auto-discovery.

---

## 1. Build the image

```bash
cd plugins/memory-mcp/mcp/memory
docker build -t memory-mcp:local .
```

Smoke-test that the image speaks MCP over stdio (optional — lists the 9 tools):

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | docker run -i --rm -v memory-mcp-data:/data -e MEMORY_FILE_PATH=/data/memory.jsonl memory-mcp:local
```

## 2. Copy the catalog into Docker's MCP catalogs directory, then attach it

Docker MCP Toolkit only accepts `file://` catalog references that resolve
inside `~/.docker/mcp/catalogs/` (see the limitation note above) — copy this
directory's catalog there once:

```bash
mkdir -p ~/.docker/mcp/catalogs
cp memory-catalog.yaml ~/.docker/mcp/catalogs/memory-catalog.yaml
```

No secrets or profile config needed — unlike a server with an external API,
this one has nothing to inject beyond the fixed `MEMORY_FILE_PATH` already
hardcoded in `memory-catalog.yaml`:

```bash
docker mcp profile create --name memory
docker mcp profile server add memory --server file://memory-catalog.yaml
```

## 3. Run the gateway with this profile

```bash
docker mcp gateway run --profile memory
```

The gateway loads the profile, runs `memory-mcp:local` from the attached
catalog, mounts the `memory-mcp-data` named volume at `/data`, and exposes
the 9 tools. `--profile` is mutually exclusive with
`--servers`/`--enable-all-servers`; the profile decides which servers are
enabled.

## 4. Wire it to a client

Add the gateway as a stdio MCP server in Claude Code so it uses exactly this
catalog. This is a separate, manual registration — do this even if you
installed `memory-mcp` as a plugin, since (per the limitation above) its
bundled `.mcp.json` cannot auto-launch on affected Docker MCP Toolkit
versions:

```bash
claude mcp add memory -- docker mcp gateway run --profile memory
```

## 5. Verify end-to-end

Ask the client to call `read_graph` — it should return an empty-but-valid
graph. Then call `create_entities` with a test entity, restart the
container (or the gateway), and call `read_graph` again: the test entity
must still be present. That proves the `memory-mcp-data` named volume is
actually persisting data across container restarts, not just the current
process.

---

## Reset

```bash
docker volume rm memory-mcp-data
```

Wipes the knowledge graph entirely — the next container start begins empty.

## Vendored from upstream

`index.ts`, `package.json`, `vitest.config.ts`, `__tests__/*.test.ts`, and
`LICENSE` are vendored verbatim from
[modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers),
`src/memory/`, pinned to commit
[`fd8248e5`](https://github.com/modelcontextprotocol/servers/commit/fd8248e56b822cc16a74b6610a88141fdfa09bd6)
(`@modelcontextprotocol/server-memory` 0.6.3, 2026-07-29).

Two files deliberately deviate from upstream, both because upstream builds
inside an npm-workspaces monorepo that this vendored copy is no longer part
of:

- **`tsconfig.json`** is flattened — upstream's leaf config extends a
  monorepo-root `tsconfig.json` two directories up, which doesn't exist
  here. This file inlines those root `compilerOptions` directly instead.
- **`package-lock.json`** is generated locally (`npm install` in this
  directory) rather than vendored — upstream has no per-package lockfile,
  only a monorepo-root one covering every workspace package.

Layout otherwise stays **flat** (no `src/` subdirectory), matching
upstream's own `src/memory/` tree exactly, since these files are vendored
rather than hand-authored the way `mcp/ludus/src/*.ts` was.
