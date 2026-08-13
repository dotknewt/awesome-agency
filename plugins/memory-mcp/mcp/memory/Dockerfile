# syntax=docker/dockerfile:1

# ── Builder ───────────────────────────────────────────────────────────
FROM node:22-alpine AS builder
WORKDIR /app

# Install all deps (incl. dev) against the lockfile for a reproducible build.
# --ignore-scripts: package.json's "prepare" script runs the build, but the
# source isn't copied in yet at this point.
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts

# Build: tsc -> dist/, chmod entrypoint (via package.json's "build" script).
COPY tsconfig.json ./
COPY index.ts ./
RUN npm run build

# Drop dev dependencies so we copy a lean node_modules into the runtime stage.
RUN npm prune --omit=dev

# ── Runtime ───────────────────────────────────────────────────────────
FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY package.json ./

# Persistence: MEMORY_FILE_PATH is set to /data/memory.jsonl by the gateway
# catalog's env: block; /data is backed by the named volume memory-mcp-data
# (see memory-catalog.yaml's volumes:).
RUN mkdir -p /data && chown -R node:node /data

# Run as the image's built-in non-root user.
USER node

# stdio MCP server. Config (MEMORY_FILE_PATH) comes from an env var injected
# by the Docker MCP Gateway. Logs go to stderr; stdout is the JSON-RPC stdio
# transport.
ENTRYPOINT ["node", "dist/index.js"]
