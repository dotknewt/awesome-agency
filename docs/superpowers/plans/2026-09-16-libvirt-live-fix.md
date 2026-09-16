# Libvirt live fork repair plan

> **For agentic workers:** Use subagent-driven-development for implementation and review. Leave changes uncommitted.

**Goal:** Repair the real Ubuntu template fork failure and demonstrate cloned-guest SSH development from `/home/dotme/Code/dotsource`.

**Architecture:** Retain the existing managed immutable-template/linked-overlay lifecycle. Correct domain compatibility using observed libvirt XML. Use host virt-clone/virt-customize for a control clone and guest preparation; verify the installed MCP through its real stdio transport.

**Tech Stack:** Python, official MCP SDK, qemu:///session, virt-clone, virt-customize, SSH, OpenCode installer.

**Spec:** User request in this session supersedes the previous plan's prohibition on live VM/config testing; existing design `docs/superpowers/specs/2026-09-16-libvirt-toolkit-design.md` supplies remaining lifecycle constraints.

**Execution status:** Completed through SDD, with task reviews and final review approved. Final bundle `1.0.4` installed in `/home/dotme/Code/dotsource`. Clean live official-MCP publication/linked clone/start/inspection/shutdown, key-based SSH, Python execution, pdb and SSH-tunneled HTTP all verified. Original source disk unchanged. Final controller checks: 88 libvirt tests, 99 OpenCode Python tests, 22 runtime tests, generator/release-notes/plugin-root checks, update dry-run and installed MCP inspection pass. Source changes remain uncommitted. Evidence is retained in `.superpowers/sdd/2026-09-16-libvirt-live-fix/`; dotsource README documents the retained shut-off VM and connection.

## Global Constraints

- Work in the existing checkout containing the uncommitted libvirt implementation, continuing the recorded in-place workflow. Preserve prior changes. Do not stage, commit, push, or spawn nested agents.
- All delegates use `openai/gpt-5.6-sol`.
- Operate only `qemu:///session`. Preserve ubuntu-dev-template and its original disk; customize newly created shut-off copies only. Never delete pre-existing VM/state resources.
- Preserve managed ownership, immutable published images, linked-clone semantics, mutation locks, and recovery journals. Do not weaken unsupported-host-resource rejection generically.
- Use the user's localuser account and public SSH key; do not copy private keys into guests or repository. Bind any test SSH forwarding only to loopback.
- `/home/dotme/Code/dotsource` does not currently exist; create it as the requested install/dev test target. No global OpenCode configuration changes.
- Guest execution is verified with SSH tooling, not a new unrestricted MCP shell tool.
- Bump bundle version with release notes in the same edit; regenerate marketplace after bundle changes.

### Task 1: Repair observed real-domain compatibility

**Files:** `plugins/libvirt-toolkit/mcp/libvirt/libvirt_mcp/domain.py`, associated domain/lifecycle fixtures and tests, bundle manifest/release notes, README as needed.

**Interface:** Preserve DomainSpec/from_xml, sanitize_clone_xml, Lifecycle public APIs.

- [ ] Capture the actual inactive XML via `virsh --connect qemu:///session dumpxml --inactive ubuntu-dev-template`. Initial reproduction returns unsupported_domain with audio, redirdev, sound, watchdog.
- [ ] Add a realistic scrubbed fixture and regression proving this domain parses and clones; assert regenerated domain/MAC/disk identity and retained benign devices. Cover serial/target/model nesting, which also occurs in the real XML.
- [ ] Add narrowly validated support for observed purely virtual device forms. Reject host-backed audio, redirection transports, unexpected children, and host paths. Preserve libvirt clone XML validity.
- [ ] Run red then green focused tests and full 80-test baseline suite using `uv run --isolated --python 3.13 --with 'mcp==2.2.0' python -m unittest discover -s plugins/libvirt-toolkit/mcp/libvirt/tests -p 'test_*.py' -v`.
- [ ] Verify actual source parsing without mutating source, bump version/notes, regenerate marketplace, report paths/evidence for review.

### Task 2: Real cloning, guest readiness, and installed development workflow

**Files:** New explicitly opt-in live verification helper under `plugins/libvirt-toolkit/mcp/libvirt/` if useful, targeted core/tests fixes justified by live failures, README and `skills/libvirt-vms/references/ubuntu-template.md` instructions as needed, bundle manifest/release notes. External target `/home/dotme/Code/dotsource`.

**Interface:** Consume Task 1 domain compatibility; install bundle using `python3 opencode/install.py install libvirt-toolkit --project /home/dotme/Code/dotsource` and subsequent update. Exercise MCP template_publish, vm_create, vm_start, vm_inspect through installed launcher with explicit host-local test state directory.

- [ ] Run `virt-clone --connect qemu:///session --original ubuntu-dev-template --name UNIQUE --file NEW_PATH` as the control/source preparation copy. Verify source remains shut off and original disk unchanged by file stat/hash evidence.
- [ ] Run `virt-customize --connect qemu:///session -d UNIQUE` while shut off to inject `/home/dotme/.ssh/id_ed25519.pub` for localuser and arrange usable SSH, fresh guest machine identity and host keys. Use offline commands; inspect actual image before guessing package/service layout.
- [ ] Establish loopback-only host-to-guest SSH on user networking using supported libvirt passt forwarding or an independently verified equivalent. Investigate any resulting plugin rejection with failing tests before minimal fixes. Never propagate a fixed forwarding port blindly into sibling clones.
- [ ] Install/update dotsource's plugin, launch copied server using official MCP SDK client, publish prepared template, create/start a managed clone. Verify backing chain and independent identity versus source. Capture machine-readable MCP results and libvirt error detail.
- [ ] Authenticate SSH as localuser with the existing private key on the host (or provided password), transfer/run a small Python project from dotsource, perform an actual debugger interaction and assert output. Verify remote service through SSH forwarding if practical.
- [ ] Report exact commands/results, VM names, state root, SSH endpoint, retained resources, installed version, and any remaining blockers. Update docs with measured boundaries, bump version/notes for content changes, regenerate catalog.

### Task 3: Validation and whole-change review

**Files:** Reports/ledger plus documentation corrections if required by reviewed evidence.

- [ ] Run required checks: `python3 .github/scripts/check-opencode.py`; `python3 -m unittest discover -s opencode/tests -p 'test_*.py' -v`; `node --test opencode/tests/runtime.test.mjs`; libvirt suite; generator drift, plugin-root references, release-notes audit, `git diff --check`.
- [ ] Obtain final independent review of fixes and live evidence. Apply substantive findings through worker and scoped review.
- [ ] Record final measured results and retained VM/project paths. Vault directory is absent, so report memory capture unavailable rather than creating a replacement vault.
