# syntax=docker/dockerfile:1

# ── Builder ───────────────────────────────────────────────────────────
FROM node:22-alpine AS builder
WORKDIR /app

# Install all deps (incl. dev) against the lockfile for a reproducible build.
COPY package.json package-lock.json ./
RUN npm ci

# Build: tsc -> build/, copy openapi.yaml into build/, chmod entrypoint.
COPY tsconfig.json ./
COPY src ./src
RUN npm run build

# Drop dev dependencies so we copy a lean node_modules into the runtime stage.
RUN npm prune --omit=dev

# ── Runtime ───────────────────────────────────────────────────────────
FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production

# The bundled OpenAPI spec is read relative to build/ (src/catalog.ts), so
# the build/ tree must stay intact next to the production node_modules.
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/build ./build
COPY package.json ./

# Mount point for file-upload operations (call_ludus_api multipart). Optional;
# only used when a host dir is mounted here via the gateway's run.volumes.
RUN mkdir -p /uploads && chown -R node:node /uploads

# Run as the image's built-in non-root user.
USER node

# stdio MCP server. Config comes from LUDUS_URL / LUDUS_API_KEY env vars,
# injected by the Docker MCP Gateway. Logs go to stderr; stdout is the
# JSON-RPC stdio transport.
ENTRYPOINT ["node", "build/index.js"]
