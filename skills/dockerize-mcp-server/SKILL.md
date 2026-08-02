---
name: dockerize-mcp-server
description: >
  Package an existing MCP server repo (Node/TypeScript, Python, or other) as a Docker
  image runnable through the Docker MCP Gateway, and validate the resulting Docker
  artifacts. Use when a user wants to containerize an MCP server currently run via
  npx/node/python entrypoints, register it in a Docker MCP catalog, wire up secrets
  and config, and run it via `docker mcp gateway`. Also use to review or validate an
  existing Dockerfile, docker-compose.yml, catalog entry, environment variable
  wiring, network setup, or resource limits for an MCP server container.
---

# Dockerize an MCP Server

Goal: turn an MCP server that currently runs via a language-native entrypoint
(npx, node, python, etc.) into a container image that the Docker MCP Gateway can
launch and broker stdio to.

## Why containerize

- npm/pip-based MCP servers pull arbitrary transitive dependencies at install
  time — undesirable for supply-chain and reproducibility reasons.
- The gateway launches each MCP server in an isolated container and brokers
  stdio between the client and container, so config/secrets never touch the
  host process env directly.

## Workflow

1. **Write the Dockerfile.** Start from `references/dockerfile-templates.md`
   (Node/TypeScript and Python variants) and adapt it, applying the
   `multi-stage-dockerfile` skill (bundled in this plugin) for the
   builder/runtime split, base image pinning, non-root user, and layer
   caching. MCP-specific requirements on top of that:
   - The runtime stage's entrypoint must speak stdio (JSON-RPC) cleanly — no
     stdout logging from the app; send logs to stderr.
   - Don't bake secrets or connection URLs into the image. They arrive as env
     vars injected by the gateway at run time.
   - If the server reads bundled non-code assets (e.g. an OpenAPI spec) at a
     path relative to its own build output, keep that layout intact when
     copying from the builder stage into the runtime stage.
2. **Register a catalog entry** describing the image, tools, secrets, env
   vars, and config schema. See `references/docker-mcp-gateway.md` for the
   full catalog schema and a worked example.
3. **Wire secrets and config**:
   - Sensitive values (API keys, tokens) → `docker mcp secret set <name>` →
     surfaced as an env var via the catalog's `secrets:` block.
   - Non-secret connection details (URLs, hosts, ports) → profile config
     (`docker mcp profile config <profile> --set <name>=<value>`) → templated
     into an env var via `{{...}}` in the catalog's `env:` block.
4. **Attach the catalog to a profile and run the gateway** — see the reference
   doc for the exact CLI sequence.
5. **Wire the gateway into the client**, e.g.
   `claude mcp add <name> -- docker mcp gateway run --profile <profile>`.
6. **Verify end-to-end** — call a read-only tool through the client and
   confirm it reaches the real backend, not just that the container started.

## Validating existing Docker MCP artifacts

When asked to review or validate rather than create, check:

- **Dockerfile**: multi-stage (builder vs runtime), pinned base image tag,
  non-root `USER`, no dev deps/build tools leaking into the runtime stage, and
  an `ENTRYPOINT` that is the stdio process itself (not a shell wrapping other
  commands that write to stdout).
- **docker-compose.yml** (if present): service name matches the catalog's
  `image:`, no hardcoded secrets or URLs under `environment:`, and the
  restart/network policy is intentional, not a leftover default.
- **Environment variable references**: every env var the app code reads at
  runtime has a corresponding `secrets:` or `env:` entry in the catalog — flag
  any var that would silently fall back to a default in production.
- **Container network setup**: stdio servers need no inbound `EXPOSE`d ports;
  egress should be limited to what the API client actually calls — treat
  `--network=host` or unrestricted egress as a smell to question.
- **Resource limits/restrictions**: look for missing `read_only`, dropped
  capabilities, or memory/CPU limits where the compose/catalog format
  supports them; flag containers running as root or with `--privileged`
  unless there's a specific reason.

## Roadmap

`scripts/build-and-register.sh` — a single command that builds the image,
registers the catalog, and sets secrets — is planned for a later version and
not yet implemented.

## References

- `references/dockerfile-templates.md` — ready-to-adapt multi-stage
  Dockerfile templates (Node/TypeScript, Python) for stdio MCP servers.
- `references/docker-mcp-gateway.md` — full catalog YAML schema, the
  secrets-vs-profile-config distinction, and gateway/profile CLI commands.
- Uses the `multi-stage-dockerfile` skill (this plugin) for general
  Dockerfile best practices.
