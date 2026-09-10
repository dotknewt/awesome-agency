# Install ludus-toolkit for OpenCode

This installer copies all seven Ludus skills into a consuming project's standard
`.opencode/skills/` directory and can add the bundled MCP definition to the
project-root `opencode.json`. The copies contain real files, including all skill
references, so they do not depend on this repository after installation.

## Prerequisites

- OpenCode
- Python 3.10 or newer for the installer
- Docker with a working daemon
- A reachable Ludus server and API key

## Build the MCP image

From the root of this repository:

```bash
docker build -t ludus-mcp:local plugins/ludus-toolkit/mcp/ludus
```

OpenCode launches this image directly over stdio. The Docker MCP Gateway is not
required for this installation method.

## Provide Ludus credentials

Set both variables in the environment that launches OpenCode:

```bash
export LUDUS_URL="https://198.51.100.1:8080"
read -rsp "Ludus API key: " LUDUS_API_KEY && printf '\n'
export LUDUS_API_KEY
```

Do not put the API key in `opencode.json`. The shipped fragment uses OpenCode's
`{env:VAR}` references, and the values are passed into the container at launch.

## Install

From this repository, install into an existing project and merge its config:

```bash
python3 plugins/ludus-toolkit/opencode/install.py /path/to/project --merge-config
```

The installer preserves unrelated configuration and MCP servers. Re-running it
with identical content is safe. It stops before writing if an installed skill or
`mcp.ludus` differs, or if the project uses `opencode.jsonc` or
`.opencode/opencode.json`; in those cases, merge the files manually rather than
discarding comments or creating competing configuration locations.

For a manual installation, copy the seven directories under
`plugins/ludus-toolkit/skills/` into `/path/to/project/.opencode/skills/` while
dereferencing symlinks, then merge the `mcp.ludus` object from
[`opencode.json`](./opencode.json) into the project's existing OpenCode config.
Copy the complete directories, not only their `SKILL.md` files.

Quit and restart OpenCode after installation; configuration and skills are
loaded only at startup.

## Container networking

- For a remote, LAN, or cloud Ludus server, set `LUDUS_URL` to its normal URL.
- For Docker Desktop and a Ludus server on the host, use
  `https://host.docker.internal:8080` instead of `127.0.0.1`.
- On Linux, if `host.docker.internal` is unavailable, add
  `"--add-host", "host.docker.internal:host-gateway"` before the image name in
  the config's `command` array.

The Ludus client accepts the server's self-signed TLS certificate.

## Verify

After restarting OpenCode:

1. Ask it to list Ludus MCP operations. This proves the image started, but the
   operation catalog is bundled and does not prove server connectivity.
2. Ask it to describe the read-only `index` operation.
3. Ask it to call `index`. A Ludus version response proves that `LUDUS_URL` is
   reachable and `LUDUS_API_KEY` authenticates successfully.
4. Ask a range configuration or Ludus CLI question and confirm the relevant
   installed skill is available.

## File uploads

Upload operations receive paths inside the container. Add a bind mount before
the image name in the config's `command` array, for example:

```json
"-v", "/absolute/host/path:/uploads:ro"
```

Then pass a container-side path such as `/uploads/role.tar.gz` to
`call_ludus_api`.
