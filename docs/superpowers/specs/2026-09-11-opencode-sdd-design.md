# Automatic OpenCode SDD support

## Goal

Import the model-policy skill, dispatcher, worker, and reviewer from
`/home/dotme/.config/opencode/` and automatically include them in every
nonempty awesome-agency OpenCode installation. The user approved automatic
installation and the OpenCode-only managed-contribution architecture.

## Source layout

Keep these host-specific sources under `opencode/sdd/`, with `skills/`,
`agents/`, and `plugins/` subdirectories matching their original layout.
Include the skill's existing `tests/dispatch.test.mjs` and adapt its test
setup for reproducible repository execution. Preserve the dispatch behavior
and agent permissions. Replace references to one user's global preference
with the shipped policy default, and replace global-only implementation and
test paths with paths valid for project and global installations.

The canonical marketplace remains the catalog for selectable content. SDD is
OpenCode runtime support, not an additional marketplace entry. The existing
staged additions and working-tree deletions under
`skills/subagent-model-policy/` are pre-existing user work and must be
preserved.

## Rendering and registration

Extend `opencode/agency/config.py` to emit the policy skill and two agents
into the target's public `skills/` and `agents/` directories. Copy native
agent frontmatter without Claude conversion so its permission denials survive.

Keep the dispatcher implementation in the managed runtime area. The generated
`plugins/awesome-agency.js` imports its factory and the existing AwesomeAgency
factory, combining the dispatcher's tool contribution with the runtime hooks.
There must be exactly one registration of `subagent_dispatch`: do not also
emit an auto-discovered `plugins/subagent-dispatch.ts` entry. This refines the
approved path list to avoid registering the same factory twice.

Preserve the source plugin's use of the OpenCode SDK and schema helpers.
Establish the SDK dependency resolution and TypeScript-loading prerequisites
in the isolated test environment rather than relying on the importing user's
global node_modules. Installed artifacts must run without the source checkout.

## Ownership and lifecycle

SDD files are shared runtime contributions owned by every selected marketplace
entry. Install and update emit them automatically. Partial uninstall retains
them; uninstalling the last entry removes unmodified managed files through
the existing source-independent ownership mechanism. An empty update remains
a no-op.

Runtime contributions must reject incompatible collisions with rendered
marketplace files rather than overwrite them in the desired-file map. Existing
on-disk conflict detection and transactional writes apply to all new files.

## Model and permission behavior

The dispatcher defaults to `openai/gpt-5.6-sol`, with explicit dispatch model
overrides taking precedence. Resuming without a model preserves the child's
previous model. The installer `--model` option continues to apply to selected
marketplace agents; the SDD default is specified by its policy and dispatcher.

Validate model availability before creating a child, enforce direct-parent
ownership and consistent roles on resume, and verify the returned model ID.
Surface unavailable models and provider failures without silent fallback.
Workers and reviewers cannot delegate. Reviewers cannot edit or run shell
commands and return their reports to the controller.

## Validation

Use mocked SDK tests for defaults, overrides, resumes, role and parent checks,
model mismatch, unavailable models, provider errors, and cancellation.
Installer tests cover automatic inclusion, native permission preservation,
shared ownership, updates, collisions, dry runs, and final uninstall.
Extend projection validation to inspect the automatic public artifacts and
detect collisions with marketplace content. Isolated discovery should verify
the combined plugin loads and the skill and both agents are discoverable.
No test should dispatch a paid model or start an external MCP service.

Required checks:

```sh
python3 .github/scripts/check-opencode.py
python3 -m unittest discover -s opencode/tests -p 'test_*.py' -v
node --test opencode/tests/runtime.test.mjs
```

Run the adapted dispatcher suite and the pinned isolated runtime check as
well. `opencode --version` and `opencode --help` were inspected; the available
binary reports `1.18.30`.

## Documentation

Document automatic installation, the model default and override contract,
ownership lifecycle, and any runtime prerequisites in `opencode/README.md`.
Tell users to quit and restart OpenCode after installing or updating.
