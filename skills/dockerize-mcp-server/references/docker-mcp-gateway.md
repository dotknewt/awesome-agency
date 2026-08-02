# Docker MCP Gateway Reference

The Docker MCP Gateway launches MCP servers in isolated containers and brokers
stdio between an AI client and the container. This reference covers the local
file-catalog format and the CLI workflow for wiring one up — no PR to
`docker/mcp-registry` or public repo required.

## Concepts

- **Catalog**: a YAML file describing one or more MCP server images under a
  `registry:` map. A "file catalog" is a local YAML file referenced by path
  (`file://...`), as opposed to a catalog published to a Docker MCP registry.
- **Profile**: the unit that binds a catalog, config values, and enabled
  servers together. Replaces the older `docker mcp config write` flow.
- **Secrets**: sensitive values, stored in the OS keychain via
  `docker mcp secret set`, injected into the container as env vars.
- **Profile config**: non-secret values (URLs, flags), set via
  `docker mcp profile config`, injected as env vars via `{{catalog-key.field}}`
  templating.

## Catalog file schema

```yaml
registry:
  <server-id>:
    description: <one-line description>
    title: <display name>
    type: server
    image: <image>:<tag>
    ref: ""
    source: <repo url>
    upstream: <repo url>
    icon: <icon url>
    tools:
      - name: <tool_name>
      - name: <tool_name>
    secrets:
      - name: <server-id>.<secret_name>
        env: <ENV_VAR_NAME>
        example: <placeholder>
    env:
      - name: <ENV_VAR_NAME>
        value: '{{<server-id>.<config_field>}}'
    config:
      - name: <server-id>
        description: <connection description>
        type: object
        properties:
          <field>:
            type: string
        required:
          - <field>
    # optional: mount host paths for file-upload style tools
    volumes:
      - /absolute/host/path:/container/path
    metadata:
      category: <category>
      tags: [<tag>, <tag>]
      license: <license>
      owner: <owner>
```

Key points:

- `secrets` entries map a keychain secret name to an env var — set with
  `docker mcp secret set <server-id>.<secret_name>`.
- `env` entries map a profile-config field to an env var via
  `{{server-id.field}}` templating — never hardcode connection details in the
  catalog itself.
- `config` describes the schema of the profile-config object referenced by the
  templating above; its `required` fields should match what the `env`
  templating actually consumes.
- `volumes` is optional and only needed when a tool operates on host files
  (e.g. a multipart upload) — the tool must be told to use container-side
  paths, not host paths.

## CLI workflow

```bash
# 1. Build the image
docker build -t <server-id>:local .

# 2. Store secrets
printf '%s' '<value>' | docker mcp secret set <server-id>.<secret_name>

# 3. Create a profile, attach the catalog, set config
docker mcp profile create --name <profile-id>
docker mcp profile server add <profile-id> --server file://<path-to-catalog.yaml>
docker mcp profile config <profile-id> --set <server-id>.<field>=<value>
docker mcp profile config <profile-id> --get-all   # confirm

# 4. Run the gateway
docker mcp gateway run --profile <profile-id>

# 5. Wire to a client (example: Claude Code)
claude mcp add <name> -- docker mcp gateway run --profile <profile-id>
```

`--profile` is mutually exclusive with `--servers`/`--enable-all-servers` —
the profile alone decides which servers are enabled. The older
`docker mcp config write` command is gone; use profile config instead.

## Gotchas

- **`localhost` from inside the container**: if the backend the MCP server
  talks to runs on the same host, use `host.docker.internal`, not
  `127.0.0.1` — the container can't reach the host's loopback interface
  directly.
- **stdio purity**: only JSON-RPC may go to stdout. Any logging, warnings, or
  print statements from the server or its dependencies must go to stderr, or
  the gateway will see corrupted stdio framing.
- **Relative asset paths**: if the app reads bundled files (OpenAPI specs,
  templates) via a path relative to its own build output directory, make sure
  the runtime stage's `COPY` preserves that directory layout next to
  `node_modules`/site-packages — don't flatten it.
- **Non-root by default**: run as the image's built-in non-root user (e.g.
  `USER node`) unless the entrypoint genuinely needs root.
- **Resetting**: `docker mcp secret rm <server-id>.<secret_name>` clears a
  stored secret.

## Worked example

`plugins/ludus-toolkit/mcp/ludus/` in this repo shows the catalog and gateway
side of this pattern working end to end:

- `ludus-catalog.yaml` — a local file catalog matching the schema above
- `README.md` — the full secret → profile → gateway → verify walkthrough

For the Dockerfile itself, start from
`references/dockerfile-templates.md` in this skill rather than that repo's
Dockerfile — the template here isn't tied to one server's specific build.
