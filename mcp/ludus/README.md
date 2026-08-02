# Running ludus-mcp with Docker + the Docker MCP Gateway

This packages `ludus-mcp` as a Docker image and runs it through the
**Docker MCP Gateway**, which launches the server in an isolated container and
brokers stdio between your AI client and the container. Config (`LUDUS_URL`,
`LUDUS_API_KEY`) is injected by the gateway — no CLI args, no code changes.

Files in this directory that make it work:

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage build → non-root stdio image (`node build/index.js`) |
| `.dockerignore` | Keeps the build context clean / forces an in-image build |
| `ludus-catalog.yaml` | A local "file catalog" the gateway reads directly |

Prerequisites: Docker Desktop with the MCP Toolkit (`docker mcp` CLI available).

---

## 1. Build the image

```bash
cd /Users/dotme/Code/agency/mcp/ludus
docker build -t ludus-mcp:local .
```

Smoke-test that the image speaks MCP over stdio (optional — lists the 4 tools):

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  | docker run -i --rm -e LUDUS_URL=https://YOUR_HOST:8080 -e LUDUS_API_KEY=dummy ludus-mcp:local
```

## 2. Store your API key as a secret

The gateway maps the keychain secret `ludus-mcp.api_key` to the `LUDUS_API_KEY`
env var inside the container (see `secrets:` in `ludus-catalog.yaml`).

```bash
printf '%s' '<YOUR_LUDUS_API_KEY>' | docker mcp secret set ludus-mcp.api_key
```

## 3. Create a profile, attach the catalog, set the URL

Config and server selection now live in a **profile** (the old
`docker mcp config write` is gone). Create the profile, attach this file
catalog to it, then set the `url` value — the gateway resolves it into
`LUDUS_URL` via the `{{ludus-mcp.url}}` template in `ludus-catalog.yaml`:

```bash
docker mcp profile create --name ludus
docker mcp profile server add ludus --server file://ludus-catalog.yaml
docker mcp profile config ludus --set ludus-mcp.url=https://198.51.100.1:8080
docker mcp profile config ludus --get-all  # confirm the url is stored
```

- Remote / LAN / cloud Ludus host → normal URL, e.g. `https://198.51.100.1:8080`.
- Ludus on **this machine's** localhost → use `host.docker.internal`, e.g.
  `https://host.docker.internal:8080` (a container cannot reach the host via
  `127.0.0.1`). Self-signed certs are fine — the client skips TLS verification.

## 4. Run the gateway with this profile

```bash
docker mcp gateway run --profile ludus
```

The gateway loads the profile, runs `ludus-mcp:local` from the attached
catalog, injects the secret + URL, and exposes the 4 tools. `--profile` is
mutually exclusive with `--servers`/`--enable-all-servers`; the profile
decides which servers are enabled.

## 5. Wire it to a client

Add the gateway as a stdio MCP server in Claude Code so it uses exactly this
catalog:

```bash
claude mcp add ludus -- docker mcp gateway run --profile ludus
```

## 6. Verify end-to-end

Ask the client to run `list_ludus_operations`. A populated operation list proves
the container reached your Ludus server and the API key works. If it's empty or
errors with a connection failure, re-check the `url` config (`docker mcp profile
config ludus --get-all`; localhost → `host.docker.internal`) and that the
secret is set.

---

## File uploads (optional)

`call_ludus_api` multipart operations read file paths **from inside the
container**, not your host. To upload a local file, mount a host directory and
pass the container-side path. Uncomment and edit the `volumes:` block in
`ludus-catalog.yaml`:

```yaml
    volumes:
      - /absolute/host/path:/uploads
```

Then pass paths like `/uploads/role.tar.gz` to `call_ludus_api`.

## Reset

```bash
docker mcp secret rm ludus-mcp.api_key
```
