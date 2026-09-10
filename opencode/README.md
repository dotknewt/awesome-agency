# OpenCode installer

This installer projects the 75 entries in the Claude marketplace into an
OpenCode project or global configuration. It uses the current checkout as its
source; it never fetches, publishes, or edits the marketplace.

## Requirements

- Python 3.10 or newer
- `PyYAML` (frontmatter parsing) and `jsonschema` (schema checks):
  `python3 -m pip install -r opencode/requirements.txt`
- OpenCode 1.18.30 or newer for runtime use. CI measures 1.18.30.
- Node.js only for the runtime tests and vault helpers.
- Docker only when using the Ludus MCP gateway.

The installer does not need OpenCode, Node, Docker, an API key, or network
credentials. Runtime integration tests use a mocked SDK. The schema test is
separate from runtime integration and downloads only the public OpenCode
schema in CI.

## Install and select

From this repository, list entries and install one or more entries into a
project:

```sh
python3 opencode/install.py list
python3 opencode/install.py install vault-memory superpowers --project /path/to/project
```

Install globally instead:

```sh
python3 opencode/install.py install steward --global
```

Global files go to `$XDG_CONFIG_HOME/opencode`, or `~/.config/opencode` when
`XDG_CONFIG_HOME` is unset. Project files go to
`/path/to/project/.opencode`. Quit and restart OpenCode after installing or
updating; OpenCode does not hot-reload generated skills, agents, commands, or
plugins.

The catalog is the existing `.claude-plugin/marketplace.json`. Bundles and
micro-entries can be selected together. The installer detects incompatible
content collisions before writing; identical shared files are owned by both
entries and remain until the last owner is removed.

Agents retain their source model pin unless `--model` is supplied:

```sh
python3 opencode/install.py install ember-agent --project . --model openai/gpt-5.6-luna
```

The value is normalized to an OpenCode provider/model ID when necessary. The
override applies to entries named in that command, while existing selections
retain their persisted model.

Explicit-only skills (`disable-model-invocation: true`) also receive a
generated `.opencode/commands/<skill>.md` entry. This is an OpenCode command
projection, not a claim that OpenCode honors Claude frontmatter fields.

## Update, uninstall, and recovery

Update all entries already selected in the target from the current checkout, or
name installed entries explicitly:

```sh
python3 opencode/install.py update --project /path/to/project
python3 opencode/install.py update vault-memory --global
```

An unnamed update on an empty target is a no-op. Naming an entry that is not
already installed is rejected rather than installing it as a side effect.

Preview either mutation without writing files:

```sh
python3 opencode/install.py install vault-memory --project . --dry-run
python3 opencode/install.py uninstall vault-memory --project . --dry-run
```

Uninstall selected entries:

```sh
python3 opencode/install.py uninstall vault-memory superpowers --project /path/to/project
```

The managed state records owners, versions, models, modes, and hashes under
`.opencode/awesome-agency/`. Local edits to managed files are never silently
overwritten or deleted. An update or uninstall reports a conflict; save or
revert the local edit, then repeat the command. If another selected entry owns
the same file, removing one entry preserves it. If the marketplace catalog and
source pools are unavailable, uninstall still works from the persisted state
and managed runtime as long as `opencode/install.py` remains available. The
installer itself is not copied into the target, so removing the entire
repository also removes the executable used to invoke uninstall.

An interrupted write is rolled back. Do not remove only public files by hand:
that creates a missing-file conflict. To recover, restore the checkout, run
the same command again, and resolve the named conflict. For a deliberately
abandoned installation, uninstall the recorded entries before removing the
`.opencode/awesome-agency/` directory.

## Configuration and MCP

The installer does not rewrite `opencode.json` or `opencode.jsonc`. It preserves
comments and unrelated keys by leaving user configuration untouched, then
merges selected MCP contributions through the generated runtime plugin.
Competing config locations, malformed JSON/JSONC, a non-object `mcp` value, or
a conflicting server name fail before any content is written. Merge JSONC
manually when the installer reports that it cannot safely inspect it.

`ludus-toolkit` translates its local MCP definition to OpenCode's `local`
form. It requires Docker and an image named `ludus-mcp:local`, plus:

```sh
export LUDUS_URL=https://ludus.example
export LUDUS_API_KEY=replace-me
python3 opencode/install.py install ludus-toolkit --project .
```

The six Ludus skills remain available without Docker; only the MCP gateway
needs those prerequisites. `memory-mcp` likewise needs its documented Docker
gateway when that bundle's service is selected.

`vault-memory` uses the Obsidian `mcpvault` stdio server and binds it to the
active project's `vault/` directory. Install Node/npx and configure the vault
layout before using its MCP tools. The runtime also provides native OpenCode
tool checks and vault briefing/capture. No installer or CI check connects to
Ludus, Docker, Obsidian, mcpvault, or a model service.

## Lifecycle differences

OpenCode 1.18.30 was measured with `opencode debug startup` using an explicitly
configured generated local plugin. The
runtime adapter is tested with a mocked SDK, not by claiming live lifecycle
coverage. It maps chat/system transforms, `session.idle`,
`session.compacted`, `tool.execute.before`, and `tool.execute.after` to the
corresponding bundle behavior. Idle capture creates an open checkpoint; it is
not a verified Claude `SessionEnd` equivalent. `SessionEnd` therefore remains
an explicit documented limitation.

Native write/edit/apply-patch operations and Obsidian MCP write/move operations
are checked before execution. Native `apply_patch` cannot delete vault notes;
use `mcp__obsidian__delete_note` with `trashMode:"local"` after explicit
confirmation so the note remains recoverable. Post-tool validation expands
multi-file patches and appends warnings for each added, updated, or renamed
destination rather than fabricating a Claude hook result. Unrelated tools pass through. Explicit
commands are user-invoked; do not rely on Claude's
`disable-model-invocation` field being understood by OpenCode.

Idle and compaction capture refreshes the open session note when the SDK message
list changes, while unchanged duplicate events are deduplicated. Events that
arrive during an in-flight capture are coalesced so the newest message list is
not lost.

Run the checks locally:

```sh
python3 .github/scripts/check-opencode.py
python3 .github/scripts/check-opencode.py --runtime
python3 -m unittest discover -s opencode/tests -p 'test_*.py' -v
node --test opencode/tests/runtime.test.mjs
```

The projection check renders every marketplace entry individually, verifies
frontmatter and managed paths, checks explicit command generation, validates
hook/MCP fields against the matrix, and plans the complete joint install to
catch bundle plus micro-entry collisions. The runtime check uses temporary
HOME/XDG directories and an explicit local plugin list containing only the
generated plugin; it does not use global external plugins, starts no real MCP
service, and uses no credentials. It asserts that OpenCode's resolved config
lists the generated plugin and contains a synthetic disabled MCP server
injected by that plugin's config hook. It never edits a user's OpenCode config.
