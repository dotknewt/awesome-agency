# Automatic OpenCode SDD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically install the supplied model-policy skill, worker, reviewer, and dispatcher with every nonempty OpenCode marketplace selection.

**Architecture:** Store native sources under `opencode/sdd/`. Render them as shared, transaction-owned runtime contributions and compose the dispatcher into the existing generated plugin. Keep the marketplace catalog authoritative for selectable entries.

**Tech Stack:** Python 3.10+, PyYAML, OpenCode 1.18.30 SDK, TypeScript, Node test runner.

**Spec:** `docs/superpowers/specs/2026-09-11-opencode-sdd-design.md`

## Global Constraints

- OpenCode's measured target is `1.18.30`; the installed binary has been checked.
- Default dispatch model: `openai/gpt-5.6-sol`; explicit dispatch overrides win.
- Installer `--model` applies to marketplace agents, not the automatic SDD default.
- Preserve native agent permissions and the source dispatch contract.
- Exactly one `subagent_dispatch` registration through `plugins/awesome-agency.js`.
- Installed files must work without the source checkout or global node_modules.
- Python install/update must not fetch dependencies or require Node.
- No model dispatch, credentials, Docker, or external MCP services in tests.
- Preserve staged additions plus working-tree deletions under `skills/subagent-model-policy/`.
- Do not stage or commit unless explicitly requested.
- Vault retrieval is unavailable: `vault/INDEX.md` does not exist in this checkout.

## File responsibilities

| File | Responsibility |
| --- | --- |
| `opencode/sdd/plugins/subagent-dispatch.ts` | Imported native dispatcher |
| `opencode/sdd/agents/sdd-worker.md` | Native worker role and denials |
| `opencode/sdd/agents/sdd-reviewer.md` | Native reviewer role and denials |
| `opencode/sdd/skills/subagent-model-policy/SKILL.md` | Shipped model-selection policy |
| `opencode/sdd/skills/subagent-model-policy/tests/dispatch.test.mjs` | Imported and expanded mocked-SDK tests |
| `opencode/package.json`, `opencode/package-lock.json` | Reproducible development SDK/TypeScript test dependencies |
| `opencode/agency/config.py` | Automatic artifact rendering and generated composition wrapper |
| `opencode/install.py` | Runtime/content collision protection |
| `opencode/tests/test_config.py` | Rendering and CLI lifecycle regression tests |
| `.github/scripts/check-opencode.py` | Automatic artifact validation and isolated discovery |
| `opencode/tests/test_check_opencode.py` | Checker regressions |
| `.github/workflows/validate.yml` | Dispatcher test execution in CI |
| `opencode/README.md` | Automatic support, dependencies, overrides, lifecycle |

## Task 1: Import and verify the native dispatcher package

**Consumes:** The four requested sources rooted at `/home/dotme/.config/opencode/`, including the skill's test subdirectory.

**Produces:** The source layout listed above; a factory taking OpenCode plugin context and returning `{ tool: { subagent_dispatch } }`.

- [ ] Copy the existing dispatcher test first to its corresponding `opencode/sdd/` path using `apply_patch`. Its existing `../../../plugins/subagent-dispatch.ts` URL will still resolve correctly. Run it before copying the plugin and verify the missing-plugin assertion fails.
- [ ] Add the four source files using `apply_patch`. Preserve the TS dispatcher and agent denials byte-for-byte initially. Adapt only policy prose: replace “This user's global preference” with “The shipped default”; replace the global implementation path with `awesome-agency/runtime/subagent-dispatch.ts` relative to the install target; document the repository test command below.
- [ ] Add reproducible development dependencies. Resolve exact available versions and commit them to the manifest/lockfile during implementation; `@opencode-ai/plugin@1.18.30` has already been confirmed published. Use `tsx` to run TS on CI's Node 20 instead of depending on local Node 26 type stripping:

```sh
npm install --prefix opencode --save-dev --save-exact @opencode-ai/plugin@1.18.30 tsx
node --import ./opencode/node_modules/tsx/dist/loader.mjs --test opencode/sdd/skills/subagent-model-policy/tests/dispatch.test.mjs
```

Verify the selected tsx package exports/loader path before recording the command in docs and CI. Ignore `opencode/node_modules/` in `opencode/.gitignore`.

- [ ] Extend the existing harness with call recording for abort and configurable prior role. Add these independent failures and outcomes:

```js
test('resume refuses a different role', async () => {
  await assert.rejects(run({ task_id: 'child', role: 'reviewer' }), /role mismatch/i);
});
test('malformed model is rejected before child creation', async () => {
  await assert.rejects(run({ model: 'missing-provider' }), /provider\/model/);
});
```

Also test a pre-aborted controller (no session creation), cancellation during an in-flight prompt (child abort invoked), missing child ID, and missing prompt response. Use deferred promises to control cancellation timing; do not use arbitrary sleeps. Keep original tests for defaults, overrides, model identity, provider errors, and foreign parents.

- [ ] Run the entire dispatcher suite and verify all cases pass. If an imported behavior fails its contract, invoke systematic debugging before changing it and record the scoped fix.

## Task 2: Render and own automatic SDD artifacts

**Consumes:** Task 1 sources and existing `render_configuration(entries, target, project) -> dict[str, bytes]`.

**Produces:** Automatic public skill/agent files and `awesome-agency/runtime/subagent-dispatch.ts`, owned by every selected entry.

- [ ] Add a focused `ConfigTests` regression using `_entry` and the existing temporary-directory setup:

```python
def test_automatic_sdd_preserves_native_permissions(self):
    import yaml
    from agency.content import _parse_frontmatter
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        source = root / 'bundle'
        source.mkdir()
        result = render_configuration([_entry('bundle', source)], root / '.opencode', root)
    self.assertIn('skills/subagent-model-policy/SKILL.md', result)
    self.assertIn('awesome-agency/runtime/subagent-dispatch.ts', result)
    self.assertNotIn('plugins/subagent-dispatch.ts', result)
    for role in ('worker', 'reviewer'):
        front, _ = _parse_frontmatter(result[f'agents/sdd-{role}.md'].decode())
        self.assertEqual(front['model'], 'openai/gpt-5.6-sol')
        self.assertEqual(front['permission']['task'], 'deny')
        self.assertEqual(front['permission']['subagent_dispatch'], 'deny')
        if role == 'reviewer':
            self.assertEqual(front['permission']['edit'], 'deny')
            self.assertEqual(front['permission']['bash'], 'deny')
```

- [ ] Run `python3 -m unittest discover -s opencode/tests -p 'test_config.py' -v` and confirm the new test fails on absent SDD artifacts.
- [ ] Define a constant source-to-target map in `config.py`, reading only the four specified files. Translate read failures to `StateError`, consistent with runtime helper reads. Emit the map for nonempty selections; tests stay in the repository, not the installed skill.
- [ ] Replace `_PLUGIN` with a single exported factory:

```js
// Generated by awesome-agency. Do not edit; it is transaction-owned.
// Compose runtime config/lifecycle hooks with the model-aware dispatcher.
import { AwesomeAgency } from '../awesome-agency/runtime/agency.js'
import SubagentDispatch from '../awesome-agency/runtime/subagent-dispatch.ts'

export default async function (context) {
  const runtime = await AwesomeAgency(context)
  const dispatch = await SubagentDispatch(context)
  return { ...runtime, tool: { ...runtime.tool, ...dispatch.tool } }
}
```

Do not export the imported factories individually: OpenCode scans exported factories.

- [ ] Add collision checks before assigning each runtime contribution in `_apply_selection`:

```python
if rel in desired_all and desired_all[rel] != data:
    raise StateError(f'collision: runtime contribution disagrees on {rel}')
```

Keep the existing assignment of all selected entry names as runtime file owners.

- [ ] Update the exact-file-set assertion in `test_unrelated_user_config_and_mcp_are_not_owned` to include the explicit new paths while still excluding user configuration files.
- [ ] Add CLI lifecycle coverage using `ConfigTests._repo` and `installer.main`: install `one` and `two`; check SDD owners are `['one', 'two']`; uninstall `one`; assert files remain with owner `two`; remove the fixture source repo; uninstall `two`; assert the unmodified automatic files disappear. Run each CLI operation with `--repo`, `--project`, and a temporary isolated XDG directory.
- [ ] Add regressions for install `--dry-run` leaving no target files, empty update remaining a no-op, update introducing SDD into an old installation fixture, and a conflicting user agent refusing installation without mutating other files. Mock `installer.render_entry` to return incompatible bytes for `agents/sdd-worker.md` and verify the runtime/content collision path fails before writing.
- [ ] Run the full Python suite:

```sh
python3 -m unittest discover -s opencode/tests -p 'test_*.py' -v
```

## Task 3: Verify installed discovery and SDK resolution

**Consumes:** Task 2 renderer and Task 1 native dispatcher.

**Produces:** Reproducible installed-artifact validation and documented runtime dependency evidence.

- [ ] Extend `check_projection()` to call `check_public_files('automatic-runtime', contribution)` on `render_configuration()` output. Before merging it into `desired`, reject differing bytes at any existing path. Add a regression that supplies a conflicting rendered SDD agent and expects failure.
- [ ] Extend isolated discovery to require `subagent-model-policy` in `debug skill` and run `debug agent sdd-worker` and `debug agent sdd-reviewer`. Parse/assert the returned model and permission data according to measured CLI output, not substring presence alone.
- [ ] Run `python3 .github/scripts/check-opencode.py --runtime` with the pinned CLI. The generated wrapper must load its TS import and resolve `@opencode-ai/plugin/tool` in temporary HOME/XDG directories. This is the acceptance gate for host-managed SDK dependency resolution; repository dev dependencies must not mask the result.
- [ ] If the pinned host does not resolve its SDK automatically, stop and report the measured failure before expanding the installer dependency model. Do not emit an unmanaged npm install, write user package.json, or silently rely on the original global configuration.
- [ ] Add an integration test that materializes the actual generated wrapper and helpers into a temporary target, loads it with the same TS test runtime as Task 1, invokes the factory with a mocked client, and asserts:

```js
assert.equal(typeof hooks.config, 'function');
assert.equal(typeof hooks['tool.execute.before'], 'function');
assert.deepEqual(Object.keys(hooks.tool), ['subagent_dispatch']);
```

Call the generated tool with the dispatcher harness and verify the selected SDK model and returned task ID. Dispose the runtime after the test. The test target must contain copied helper files, not symlinks or absolute source-checkout imports.
- [ ] Wire npm dependency installation (`npm ci --prefix opencode`) and the dispatcher/integration test command into the OpenCode CI job. Keep existing Node 20 coverage and required runtime tests.
- [ ] Document automatic SDD behavior, `openai/gpt-5.6-sol`, explicit model overrides, installer `--model` scope, partial/final uninstall, SDK startup prerequisites as measured, repository test commands, and quit/restart requirements in `opencode/README.md`. No marketplace or bundle version changes are needed for OpenCode-only support files.
- [ ] Run final verification:

```sh
python3 .github/scripts/check-opencode.py
python3 -m unittest discover -s opencode/tests -p 'test_*.py' -v
node --test opencode/tests/runtime.test.mjs
node --import ./opencode/node_modules/tsx/dist/loader.mjs --test opencode/sdd/skills/subagent-model-policy/tests/dispatch.test.mjs
python3 .github/scripts/check-opencode.py --runtime
git diff --check
git status --short
```

Include the composition integration test in the recorded Node test command once its file is added. Review final changes against the spec, including the original staged/deleted skill files, and report exact test outcomes and any runtime limitations.

## Self-review

- Source import and model/permission contract: Task 1.
- Automatic rendering, single registration, ownership, conflicts, and uninstall: Task 2.
- Self-contained SDK loading, projection checks, discovery, CI, and docs: Task 3.
- Dependency resolution is an explicit measured gate, not a claimed fact.
- No execution commits are authorized by this plan.
