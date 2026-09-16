# Libvirt toolkit design

## Approved scope

Provide an MCP server plus a workflow skill for VM lifecycle management from
OpenCode. The user approved linked clones, host-local server execution over
stdio (local) or SSH (remote), and powered-off snapshots. The first template is
`ubuntu-dev-template`; Debian 13 and Windows 11 preparation/support follow later.
Guest command execution, project copying, test execution inside guests, live
snapshots, migration, and remote disk transfer are outside v1.

The user also requested removal of the repository's fixed OpenCode 1.18.30
compatibility target. Compatibility is determined by checks against the installed
CLI, whose version is recorded in results. CI exercises the latest stable CLI.
Historical measurements remain evidence, not version requirements. SDK dependency
pins remain reproducible build dependencies, independent of runtime compatibility.

## Deployment

`libvirt-toolkit` is a canonical marketplace bundle projected into OpenCode by
the existing installer. Its `libvirt-vms` skill is bundle-bound because the MCP
server supplies the tools. The server source lives under
`plugins/libvirt-toolkit/mcp/libvirt/`; the skill lives in `skills/libvirt-vms/`
and is directory-symlinked into the bundle. Installation must remain usable when
the source checkout is absent.

Use Python 3.10+ for the lifecycle core, invoking `virsh` and `qemu-img` with
argument arrays and parsing XML/JSON instead of human tables. Use the official
Python MCP SDK for stdio transport, with a PEP 723 launcher runnable using `uv`.
Dependencies are declared by the shipped launcher; no native Python libvirt
binding or Docker service is required. Dependency acquisition is a documented
setup prerequisite. Tests do not connect to a user's libvirt session.

Each server process manages the local user's `qemu:///session`. Remote MCP
connections invoke the same server over `ssh -T`, as the remote VM owner.
OpenCode's configured MCP connection name selects the host. Paths and metadata
always belong to the server's host. Remote deployment and SSH authentication are
explicit setup steps; server startup never installs services or modifies SSH.

## Templates and working VMs

Publication takes an existing, prepared, powered-off domain and creates a
standalone flattened QCOW2 image, versioned template metadata, and sanitized
inactive domain XML in managed storage. The image is thereafter immutable to the
toolkit. The original template domain is independent and can be maintained.
Publication requires no managed-save state and rejects unsupported shared or
host-bound devices rather than blindly copying them.

V1 supports one writable file-backed QCOW2 disk per working VM, an optional
file-backed UEFI NVRAM store, ordinary virtual networking, and no TPM/passthrough
devices. Reject extra writable disks, shared filesystems, block/network storage,
and unsupported firmware/device state before creating resources. This deliberately
narrow storage contract makes rollback and ownership verifiable. Future OS
support can extend this contract with tests.

Creating a VM generates a fresh domain UUID, MAC addresses, an exclusive writable
QCOW2 overlay, and an independent NVRAM copy when present. Clone identity work
also removes source-specific generated runtime paths/identifiers. Preserve
compatible CPU/memory/device defaults; optional CPU and memory overrides must be
positive and internally consistent. Prepared guests must reset their own machine
identity at first boot; libvirt identity alone is insufficient. The Ubuntu recipe
documents preparation rather than silently modifying guest files.

Live domain state is authoritative from libvirt. Server-owned metadata records
template version, domain UUID, disk layers, snapshots, and operation state. Listing
can include unmanaged VMs, but mutations operate on server-managed working VMs
(template publication is the explicit source-domain operation). Storage roots are
configurable and default to a dedicated user-data directory. Paths are generated
from validated identifiers; symlink escapes and foreign ownership are rejected.

## Powered-off snapshots

All snapshot creation/restoration requires inactive shut-off state and absence of
managed-save state. It captures disk/configuration and supported writable firmware
state, never RAM. A force-stopped disk may be crash-consistent, not clean.

Use server-managed external layers: a named snapshot records the current immutable
disk layer, inactive domain definition, and NVRAM copy; the domain is redefined to
use a fresh writable overlay backed by that layer. Restore similarly creates a
fresh writable child of the selected snapshot, restores its configuration and
firmware, preserves the working VM's identity, and leaves the VM shut off.
Snapshots are toolkit-managed; do not present them as libvirt-native snapshot or
backup-checkpoint objects. Named snapshots persist across restoring another point.

Keep referenced ancestors; never commit changes into a template or snapshot base.
Deleting a working VM removes only its owned domain and storage; deleting a
published template fails while dependents exist. Snapshot pruning/compaction is
not needed for the initial API; storage usage is inspectable, and whole-VM cleanup
removes its snapshot layers. Template removal checks actual local domain backing
references as well as metadata, and refuses if dependency inspection is incomplete.

## Lifecycle and failure handling

Tools cover host capabilities, template list/publish/remove, VM list/inspect/create/
start/shutdown/force-stop/delete, and snapshot list/create/restore. SDK schemas
validate parameters, and errors return machine-readable codes and context.
Graceful shutdown has bounded waiting and never silently escalates to force-stop.
Start and shutdown are idempotent when already in their requested state. Use
bounded subprocess execution and retain diagnostics without treating timeouts as
proof that no side effect occurred.

Serialize mutating operations with a host-local process lock; multiple OpenCode
connections can start multiple server processes. Write metadata atomically and
journal multi-step changes before modifying domain/storage. Recover or clearly
report interrupted/partial operations. A disk switch must not lose the last known
domain/storage state when define, filesystem, or metadata writes fail. Compare
actual domain UUID and disk paths with ownership metadata before mutation; reject
external drift. Out-of-band libvirt changes are not covered by a toolkit lock, so
recheck domain inactivity before disk/config changes and use ordinary image locking.

## Packaging and verification

Ship a `1.0.0` manifest, release notes explaining why, README with native local
and SSH setup, the skill, and Ubuntu preparation reference. The generated catalog
is regenerated, never manually edited. Update expected entry count and host
compatibility evidence. Runtime discovery disables the new MCP connection so CI
never starts a real libvirt server or connects to VMs.

Core tests exercise disk graph transitions, identity sanitization, ownership,
power-state gates, conflicts, and injected failures with a fake command adapter.
When `qemu-img` is available, add temporary-file tests for actual backing chains
without launching VMs. MCP tests use the real SDK with a fake lifecycle adapter
and cover discovery, schema rejection, results, and stdio framing. Integration
tests verify the installed package retains its launcher and imports when the
checkout is absent. Existing OpenCode, catalog, host, reference, skill, manifest,
and release-note checks remain acceptance gates. A real VM lifecycle smoke test
requires a separately authorized disposable VM and is not implied by unit tests.

## Sources and implementation decisions

- https://www.libvirt.org/formatsnapshot.html — external snapshots preserve the
  old disk and place subsequent writes in a new layer; shut-off snapshots contain
  no memory state.
- https://www.qemu.org/docs/master/tools/qemu-img.html — QCOW2 backing images,
  conversion, JSON backing-chain inspection, and offline image modification.
- `opencode/agency/config.py` — existing bundle MCP projection and root rewriting.
- `plugins/ludus-toolkit/` — in-tree MCP packaging precedent.

Approved in conversation on 2026-09-16. The user selected SDD and explicitly chose
implementation in the current checkout with uncommitted changes.
