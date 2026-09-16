# Libvirt Toolkit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the approved host-local libvirt MCP lifecycle server and skill, and remove the fixed OpenCode runtime target.

**Architecture:** A Python lifecycle core owns versioned template images and linked-clone storage. A stdio MCP SDK adapter exposes it locally or over SSH; the existing marketplace/OpenCode projection distributes the bundle.

**Tech Stack:** Python 3.10+, standard library, official Python MCP SDK, uv PEP 723 launcher, virsh, qemu-img, JSON/XML, unittest.

**Spec:** `docs/superpowers/specs/2026-09-16-libvirt-toolkit-design.md`

**Execution status:** Completed using SDD in the current checkout, uncommitted by
user choice. All five task reviews and final review approved after fixes. Fresh
final verification: 80 toolkit tests, 99 OpenCode Python tests, 22 runtime tests,
78-entry projection, OpenCode 1.18.31 isolated discovery, catalog drift,
plugin-root references, and release-note checks passed. No real VM or SSH host
was exercised. Skill application was checked with independent no-skill and
skill-enabled dry-run samples during review, rather than claimed as
pre-authorship behavioral TDD.

## Global Constraints

- Default libvirt URI is `qemu:///session`; server and storage operations run on the VM host.
- Initial guest is Ubuntu; Debian and Windows support are future work. No guest command execution.
- Linked clones use immutable published template versions and powered-off external snapshots.
- V1 supports one writable file-backed QCOW2 disk and optional file-backed UEFI NVRAM; unsupported storage/device state fails before side effects.
- Preserve ownership, check actual domain identity/state, serialize cross-process mutations, and journal partial operations.
- MCP uses the official SDK, stdio locally or carried by SSH; no HTTP service or Docker requirement.
- Keep installable artifacts self-contained after removing the source checkout; normal declared dependency setup remains required.
- Do not connect to real VMs, modify user config, commit, stage, push, or delegate further. Use apply_patch to edit files.
- Workers and reviewers use `openai/gpt-5.6-sol`; work occurs in the existing checkout by explicit user choice.
- Report exact test commands/results and concerns in each task report.

---

### Task 1: Behavior-based OpenCode runtime validation

**Files:** Modify `AGENTS.md`, `opencode/README.md`, `.github/host-compat.json`, `.github/scripts/check-opencode.py`, `.github/workflows/validate.yml`; test `opencode/tests/test_check_opencode.py` (use existing checker test location if equivalent).

**Interfaces:** Consumes host compatibility metadata; produces runtime discovery that accepts the installed CLI version and prints it, retaining behavior checks.

- [x] Add a focused regression test with a mocked CLI reporting a version other than the historical measurement; assert discovery proceeds to behavioral validation without `metadata["version"]`.
  ```python
  metadata = {"binary": "opencode"}
  # Mock command boundaries and installer artifacts; return a deliberately newer
  # version for --version and verify the real discovery path reaches startup.
  # A failing startup must still be rejected with the detected version in context.
  ```
- [x] Run the regression before implementation and record its failure.
- [x] Remove both OpenCode target-version fields and exact equality check; change pinned/target wording to installed CLI behavior. Historical measurements remain dated evidence. CI installs `opencode-ai@latest` and reports its version. Keep SDK/lockfile dependency pins as dependency versions.
  ```python
  version = subprocess.run([binary, "--version"], env=env, check=True,
                           capture_output=True, text=True).stdout.strip()
  # Continue into isolated startup/discovery assertions, without equality gating.
  ```
- [x] Run `python3 .github/scripts/check-opencode.py`, Python installer tests, runtime Node tests, and `python3 .github/scripts/check-opencode.py --runtime`. Investigate failures; report environmental blockers accurately.
- [x] Self-review and write the task report; leave changes uncommitted.

### Task 2: Managed templates and working-VM lifecycle core

**Files:** Create `plugins/libvirt-toolkit/mcp/libvirt/libvirt_mcp/{__init__,errors,commands,domain,store,lifecycle}.py`, tests under `plugins/libvirt-toolkit/mcp/libvirt/tests/`, and initial `plugins/libvirt-toolkit/.claude-plugin/plugin.json` plus `RELEASE-NOTES.md`. Modify `.github/scripts/generate-marketplace.py` to register the new bundle and regenerate the catalog so intermediate checks have a valid manifest.

**Interfaces:** `Lifecycle(root: Path, runner=None)` with methods `host_info()`, `template_list()`, `template_publish(source_vm, name, version)`, `template_remove(name, version)`, `vm_list()`, `vm_inspect(name)`, `vm_create(name, template, version, vcpus=None, memory_mib=None)`, `vm_start(name)`, `vm_shutdown(name, timeout_seconds=60)`, `vm_force_stop(name)`, `vm_delete(name)`. Return JSON-serializable dictionaries. `LifecycleError(code, message, details=None)` exposes fields. Runner uses argv lists with bounded subprocess execution and supports injection for tests. Store is schema-versioned and host-local; later task adds snapshot methods using these primitives.

- [x] Build fixture-driven tests for libvirt XML, qemu JSON, managed identity, and lifecycle transitions. Examples:
  ```python
  vm = service.vm_create("work-a", "ubuntu-dev-template", "v1")
  assert vm["uuid"] != source_uuid
  assert fake.backing_for(vm["disk"]) == published_image
  with self.assertRaises(LifecycleError):
      service.template_remove("ubuntu-dev-template", "v1")
  ```
  Cover source running/managed-save rejection, unsupported writable disks/TPM/passthrough, source disk/path sanitization, duplicate names, symlink escape, cross-process lock, publication flattening, UEFI independent writable state, CPU/memory override consistency, shutdown timeout without destroy, and foreign-domain deletion rejection.
- [x] Run tests and record the expected initial failure.
- [x] Implement focused modules: command execution/error mapping; domain XML inspection/sanitization; atomically persisted ownership registry/journal; lifecycle orchestration. Publication uses `qemu-img convert -O qcow2` to a new owned version path; clones use `qemu-img create -f qcow2 -F qcow2 -b ABS_BASE ABS_OVERLAY`; all virsh calls include explicit connection URI. Avoid automatic mutation recovery when actual state is ambiguous; return recovery-required details and retain reachable resources.
- [x] Ensure all mutation paths use the host lock and validate actual domain UUID/disk/NVRAM ownership before action. Template removal checks real backing dependencies and fails on incomplete inspection. No direct deletion of arbitrary source paths.
- [x] Add and run temporary-image integration tests if qemu-img is available; never start VMs. Run `python3 -m unittest discover -s plugins/libvirt-toolkit/mcp/libvirt/tests -p 'test_*.py' -v` and regenerate/check marketplace.
- [x] Write interface notes and test evidence in the report for the snapshot/MCP worker.

### Task 3: Offline external snapshots and rollback

**Files:** Create `plugins/libvirt-toolkit/mcp/libvirt/libvirt_mcp/snapshots.py` and `tests/test_snapshots.py`; update core modules only where needed for the snapshot integration.

**Interfaces:** Add `Lifecycle.snapshot_list(name)`, `Lifecycle.snapshot_create(name, snapshot, description="")`, `Lifecycle.snapshot_restore(name, snapshot)`. Use the same root, runner, store, lock, error type, and ownership checks from Task 2. Snapshot records include layer, domain XML, NVRAM copy, name, description, timestamp, and parent relationship.

- [x] Write tests for create/restore with a fake host and actual temporary backing images where available:
  ```python
  saved = service.snapshot_create("work-a", "before-upgrade")
  assert fake.backing_for(service.vm_inspect("work-a")["disk"]) == saved["disk"]
  service.snapshot_restore("work-a", "before-upgrade")
  assert service.vm_inspect("work-a")["state"] == "shut off"
  assert "before-upgrade" in snapshot_names(service.snapshot_list("work-a"))
  ```
  Include managed-save/running rejection, duplicate/missing snapshot errors, repeated restore, preservation of other snapshots and siblings, firmware restore, source identity drift, define failure, atomic metadata-write failure, interrupted-operation detection, and cleanup retaining all reachable layers.
- [x] Record failing tests, implement snapshot external-layer operations, then run tests. Use a fresh overlay on both create and restore; keep old reachable layers immutable. Save enough pre-operation state before define to either roll back safely or report an explicit recoverable pending operation. Do not label these libvirt-native snapshots/checkpoints.
- [x] Re-run lifecycle tests covering deletion and failed transitions. Write the report with exact public signatures and failure semantics for Task 4.

### Task 4: Official SDK stdio MCP adapter

**Files:** Create `plugins/libvirt-toolkit/mcp/libvirt/server.py`, `libvirt_mcp/server.py`, `tests/test_mcp.py`, dependency metadata as needed, and server-local README. The launcher declares the official MCP SDK through PEP 723; resolve and pin an available SDK version.

**Interfaces:** MCP tools mirror Task 2/3 public operations using explicit typed parameters. Instantiate `Lifecycle` with `--state-dir` or a default under `$XDG_DATA_HOME/libvirt-toolkit` (fallback `~/.local/share/libvirt-toolkit`). Logs go to stderr. Error results retain code/message/details and use protocol error semantics; expected domain failures do not crash the process.

- [x] Write real-SDK tests that list tools, reject malformed input before mutation, exercise representative successful results and structured LifecycleError results, and perform an initialize/list-tools exchange over a subprocess stdio transport with a fake core. The test never opens real libvirt.
  ```python
  # With the SDK's in-memory or stdio test transport:
  tools = await client.list_tools()
  assert "vm_create" in {item.name for item in tools.tools}
  result = await client.call_tool("snapshot_create", {"name": "work-a", "snapshot": "base"})
  assert not result.isError
  ```
- [x] Implement thin SDK adaptation with validated typed inputs, bounded operations, machine-readable output, and no general shell-execution tool. Isolate imports so core tests run without installing MCP.
- [x] Validate the launcher's dependency resolution in a temporary environment, record the resolved SDK version, run protocol tests plus core regression tests, and write the report.

### Task 5: Bundle, skill, documentation, and host projection

**Files:** Create `skills/libvirt-vms/SKILL.md` and `references/ubuntu-template.md`, symlink bundle `skills/libvirt-vms`, create `plugins/libvirt-toolkit/.mcp.json`, bundle `README.md`; update bundle release notes, generator bundle-bound exclusions, `.github/host-compat.json`, `.github/scripts/check-opencode.py`, `.github/workflows/validate.yml`, `opencode/README.md`, relevant root catalog docs, and add `opencode/tests/test_libvirt_bundle.py`.

**Interfaces:** Canonical MCP name `libvirt`; launcher command `uv run --script ${CLAUDE_PLUGIN_ROOT}/mcp/libvirt/server.py`. Existing projection rewrites the bundle root. SSH example uses `ssh -T HOST uv run --script /ABS/INSTALLED/SERVER/server.py` and a distinct MCP connection name. Host state/configuration belongs to the server host.

- [x] Load writing-skills guidance and add focused skill scenario checks for host selection, shutdown wait, linked-clone independence, and rejection handling. The skill uses MCP operations and only offers the Ubuntu preparation recipe when requested. Source preparation covers the user's install parameters, CD-ROM removal after confirmed shutdown, named base snapshot, and guest identity preparation requirements.
- [x] Add projection tests that install/copy the bundle to a temporary target, make the source unavailable, and confirm the launcher and Python imports still work; inspect generated local MCP command and dependencies. Ensure no real server/libvirt is started by general runtime discovery.
  ```python
  # Inspect generated runtime.json and copied package tree after install:
  assert runtime["mcp"]["libvirt"]["command"][0] == "uv"
  assert copied_server.is_file()
  assert copied_core.is_dir()
  ```
- [x] Implement packaging and documentation; register `libvirt-vms` as bundle-bound, regenerate marketplace, update measured evidence and expected count to actual generated entries, disable `libvirt` in isolated runtime projects, and extend CI with core/protocol tests using explicit dependencies. Validate any OpenCode config examples against the public schema.
- [x] Run all required OpenCode checks plus catalog drift, host compatibility, plugin-root refs, manifest/frontmatter checks, release-note audit, and libvirt tests. Check symlinks and `git diff --check`. Document prerequisites and exact validation boundaries, including absence of real-VM testing.
- [x] Write report. Controller obtains task review and whole-change review; apply reviewed fixes through a worker. Leave work uncommitted as requested.
