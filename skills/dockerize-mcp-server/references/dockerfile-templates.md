# MCP Server Dockerfile Templates

Ready-to-adapt multi-stage Dockerfiles for turning a stdio MCP server into a
container image. Both follow the `multi-stage-dockerfile` skill's
builder/runtime split; pick the template matching the server's language, then
work through the customization checklist below.

## Node/TypeScript

```dockerfile
# syntax=docker/dockerfile:1

# ── Builder ───────────────────────────────────────────────────────────
FROM node:22-alpine AS builder
WORKDIR /app

# Install all deps (incl. dev) against the lockfile for a reproducible build.
COPY package.json package-lock.json ./
RUN npm ci

# Build: compile to build/ (adjust for your build tool/output dir).
COPY tsconfig.json ./
COPY src ./src
RUN npm run build

# Drop dev dependencies so only production node_modules is copied forward.
RUN npm prune --omit=dev

# ── Runtime ───────────────────────────────────────────────────────────
FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/build ./build
COPY package.json ./

# node:*-alpine ships a built-in non-root "node" user — use it.
USER node

# stdio MCP server: JSON-RPC on stdout, logs on stderr. Config arrives as env
# vars injected by the Docker MCP Gateway — no CLI args, no baked-in secrets.
ENTRYPOINT ["node", "build/index.js"]
```

## Python

```dockerfile
# syntax=docker/dockerfile:1

# ── Builder ───────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

COPY . .

# ── Runtime ───────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime
WORKDIR /app

COPY --from=builder /install /usr/local
COPY --from=builder /app .

# python:*-slim has no built-in non-root user — create one.
RUN useradd --create-home --uid 1000 mcp
USER mcp

# stdio MCP server: JSON-RPC on stdout, logs on stderr. Config arrives as env
# vars injected by the Docker MCP Gateway — no CLI args, no baked-in secrets.
ENTRYPOINT ["python", "-m", "your_package.server"]
```

## Customization checklist

- **Base image**: swap the tag for the runtime version the server actually
  needs, and pin it exactly (no floating `latest`/`slim` without a version).
- **Build step**: replace `npm run build` / the Python `COPY . .` with
  whatever the server's real build process is (webpack, poetry build, etc.).
- **`ENTRYPOINT`**: point it at the server's actual stdio entrypoint module or
  script.
- **Relative-path assets**: if the app reads bundled files (an OpenAPI spec, a
  templates dir) via a path relative to its own build output, copy that
  directory intact into the runtime stage next to the dependency tree — don't
  flatten it.
- **File uploads**: only if a tool needs to read host files (e.g. a multipart
  upload operation), add a writable mount point (`RUN mkdir -p /uploads &&
  chown -R <user>:<user> /uploads`) and document that it's populated via the
  catalog's `volumes:` block — see `references/docker-mcp-gateway.md`.
- **No `EXPOSE`**: stdio servers don't listen on a port; don't add one.
- **No secrets or connection URLs in the image**: those are injected as env
  vars by the gateway at run time (see `references/docker-mcp-gateway.md`),
  never `COPY`'d or `ARG`'d in at build time.
