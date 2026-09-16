# libvirt-toolkit

`libvirt-toolkit` provides provider and guest-access workflow skills plus a local
stdio MCP server for publishing immutable QCOW2 templates, managing isolated
working VMs in the server user's `qemu:///session` libvirt instance, and handing
project-in-VM requests into verified SSH access, transfer, and execution.

It is deliberately narrow: v1 supports one writable file-backed QCOW2 disk per
working VM and optional file-backed UEFI NVRAM in either libvirt's legacy text
form or its nested `type="file"` source form. Each VM gets an exclusive linked
overlay, fresh libvirt identity, and an independent NVRAM copy. Stateless,
block/network, and separate-varstore firmware are rejected.

Supported device XML is intentionally limited to file disks; ordinary
network/bridge/user interfaces; virtual controllers; pty serial/console;
sanitizable Unix channels; mouse/tablet/keyboard input; graphics, video,
SPICE-backed audio and USB redirection, ICH9 sound, reset-only iTCO watchdog,
virtio balloon, panic, and emulator declarations; and virtio RNG backed exactly
by `/dev/urandom`. A user-mode interface may use an unadorned passt backend with
bounded TCP forwards bound exactly to `127.0.0.1`. Fixed forwards are removed
when a new template or working VM is cloned, so every working VM must receive a
separately selected host port. Fixed read-only firmware loader references remain
in the configuration. Host-backed audio and alternate redirection transports
remain unsupported. Extra writable disks, block/network disks, host serial or
evdev, shared-memory devices (`shmem`) and memory devices, direct kernel/initrd boot, shared
filesystems, passthrough, TPM, and unrecognized device kinds are rejected before
publication creates owned resources. Windows guests that require TPM remain
unsupported until a follow-up adds and tests that ownership model.

CPU or memory overrides are accepted only when the source has no dependent
topology, pinning, per-vCPU, NUMA, maximum-memory, or memory-device configuration
that the narrow rewrite cannot update consistently. Without an override, valid
compatible source relationships are retained unchanged.

## Components

- `skills/libvirt-vms` — host-selection and lifecycle workflow, including an
  opt-in Ubuntu installation/preparation reference and existing Debian 13 and
  CachyOS source-template preparation references, provider networking, passt
  forwarding, and optional read-only QGA diagnosis.
- `skills/guest-access` — provider-neutral SSH trust, authentication, regular-user
  context, project transfer, execution, and stage-by-stage evidence.
- `mcp/libvirt/server.py` — PEP 723 launcher pinned to the official Python MCP
  SDK `mcp==2.2.0`.

The toolkit's powered-off snapshots are server-managed external QCOW2,
configuration, and NVRAM layers. They are not native `virsh` snapshot or backup
checkpoint objects, and they never include RAM.

## Ubuntu, Debian 13, and CachyOS templates

Compatibility is determined by domain storage and devices, not an OS allowlist.
Compatible `ubuntu-dev-template`, `debian13-dev-template`, and `CachyOS` domains
can be published and used for project VMs. An existing libvirt domain must be prepared
for independent guest identities and explicitly published before `vm_create`
can use it.

For an existing Debian 13 VM, follow
[`skills/libvirt-vms/references/debian-template.md`](skills/libvirt-vms/references/debian-template.md).
It covers preparing a disposable copy, first-boot machine-ID and SSH-key
regeneration without requiring cloud-init, publication, and project access.
The observed Debian configuration uses BIOS boot with no NVRAM, one QCOW2 disk,
and user-mode virtio networking. Default sizing is preserved when overrides are
omitted. The toolkit manages VM lifecycle; SSH access, guest commands, and
project-file transfer are separate operations.

For the existing CachyOS VM, follow
[`skills/libvirt-vms/references/cachyos-template.md`](skills/libvirt-vms/references/cachyos-template.md).
It covers a UEFI-aware preparation copy with independent NVRAM, Arch's
`openssh`/`sshd.service` and inspected host-key generation, publication, and
project access. The observed configuration has 8 vCPUs, 16 GiB RAM, file-backed
UEFI NVRAM, and memfd-backed RAM with shared access. That memory backing is
retained and is distinct from unsupported `shmem` devices; this does not imply
support for arbitrary memory-backing configurations.

## Prerequisites on every server host

- Python 3.10 or newer and [`uv`](https://docs.astral.sh/uv/)
- `virsh`, `qemu-img`, and a configured per-user `qemu:///session`
- Optional: `passt`, installed and executable by the VM owner, when using the
  per-VM loopback forwarding path documented below
- Network access on first launch, or a populated `uv` cache, for `mcp==2.2.0`
- Enough local storage for flattened templates, overlays, and retained snapshot
  ancestors

No Python libvirt binding, Docker service, system service, root libvirt session,
or guest agent is installed by the bundle. The VM owner running the server must
already have access to every configured absolute path.

## Local installation

For Claude Code:

```sh
claude plugin install libvirt-toolkit@awesome-agency
```

That bundle includes both `libvirt-vms` and `guest-access`. Install only the
provider-neutral skill when libvirt lifecycle support is unnecessary:

```sh
claude plugin install guest-access@awesome-agency
```

After this marketplace content changes, run
`claude plugin marketplace update awesome-agency`, uninstall/reinstall a cached
bundle when needed, and start a new Claude Code session so discovery is refreshed.

Claude Code loads the bundled `libvirt` connection with this canonical command:

```sh
uv run --script ${CLAUDE_PLUGIN_ROOT}/mcp/libvirt/server.py
```

For OpenCode, install the generated projection and restart OpenCode:

```sh
python3 opencode/install.py install libvirt-toolkit --project /path/to/project
```

The standalone OpenCode form is
`python3 opencode/install.py install guest-access --project /path/to/project`.
Selecting `libvirt-toolkit guest-access` together is supported: byte-identical
shared skill files use the installer's existing multiple-owner collision policy.
Run `update` for already selected entries after refreshing this checkout, then
quit and restart OpenCode. Installation does not refresh a running session.

The installer copies the launcher and core into managed storage and rewrites the
bundle-root placeholder to that installed package. It does not start the server
during installation. A user-defined MCP connection named `libvirt` takes
precedence over the managed local connection.

Copilot CLI does not automatically start bundle-local `.mcp.json` servers. Add
the same `uv run --script /absolute/installed/path/mcp/libvirt/server.py`
command manually in Copilot's MCP configuration after locating its materialized
plugin directory.

Managed state defaults to `$XDG_DATA_HOME/libvirt-toolkit`, or
`~/.local/share/libvirt-toolkit`. To share one toolkit state between clients of
the same VM owner, give every connection the same absolute `--state-dir` path on
the server host. Never share that directory between different users or hosts.

## Per-VM loopback SSH forwarding

Follow
[`skills/libvirt-vms/references/guest-access.md`](skills/libvirt-vms/references/guest-access.md)
for the complete provider handoff, collision checks across listeners and sibling
definitions, remote-host tunnel trust boundary, and optional QGA diagnosis. The
summary below describes only the accepted persistent XML shape.

For a guest using `<interface type="user">`, passt can expose SSH without a
libvirt network. Before any persistent XML change, verify `command -v passt` and
`passt --version` in the VM owner's environment on the virtualization host; if
it is absent or not executable, stop and arrange installation or authorization.
Then select an unused unprivileged host port for each powered-off working VM,
confirm it is not listening, and add this to that VM's interface in its
persistent libvirt definition:

```xml
<backend type="passt"/>
<portForward proto="tcp" address="127.0.0.1">
  <range start="57277" to="22"/>
</portForward>
```

Replace `57277`; never copy that example port into multiple VMs. The narrow
parser rejects wildcard/non-loopback binds, passt host-device selection,
unbounded forwarding, and additional backend attributes. Configure the forward
after `vm_create` and while the VM is shut off, then use `vm_start`. The toolkit
does not allocate ports or edit host networking. Its clone sanitizer deliberately
removes every `portForward`, including one present on a publication source, to
prevent a sibling clone from reusing an occupied or unexpectedly exposed port.

## Remote host over SSH

Copy the entire `mcp/libvirt/` directory to an absolute path on the libvirt host
owned by the same account that owns the VMs. Install the prerequisites there and
verify SSH authentication separately. The client does not deploy files, modify
SSH, or transfer VM disks.

Use a distinct connection name so prompts cannot confuse local and remote host
state. This OpenCode example runs the server as `vm-owner` on `libvirt-host`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "libvirt-lab": {
      "type": "local",
      "command": [
        "ssh", "-T", "vm-owner@libvirt-host",
        "uv", "run", "--script", "/ABS/INSTALLED/SERVER/server.py",
        "--state-dir", "/ABS/STATE/libvirt-toolkit"
      ]
    }
  }
}
```

The SSH process, `qemu:///session`, domain ownership, toolkit state, journals,
and all disk/NVRAM paths belong to the remote host and remote VM owner. Paths
from the client machine are never meaningful to that server.

## Failures and manual recovery

Expected failures return `code`, `message`, and `details`. Do not bypass rejected
storage/device/power-state checks or blindly retry mutations. Graceful shutdown
uses a bounded wait and never silently force-stops a VM; reinspect state and get
explicit authorization before a force-stop.

An external-command timeout keeps `side_effect_unknown: true` and includes
UTF-8-normalized, bounded partial `stdout` and `stderr` in its structured details.
Treat those diagnostics as recovery evidence, not proof that no change occurred.

An interrupted multi-step operation may return `recovery_required` and leave
`operation.json` in the server host's state directory. Stop all mutations. As
the VM owner, inspect the journal's operation, stage, resource paths, archived
XML, actual domain UUID/disk paths, and registry metadata. Reconcile every
listed resource manually, preserving the last known disk/configuration state;
remove the journal only after the domain, storage, and ownership record agree.
`vm_create` does not report success until it can read the inactive domain back
and match its name, UUID, disk, and NVRAM to the proposed owned resources. A
missing post-define domain is recovery evidence, not a reason to rerun `define`
or retry creation automatically. This recovery rule is separate from normal
per-VM preparation: adding a unique loopback passt forward to an already
verified, powered-off managed VM is an explicit operator configuration step.

If an SDK-launched stdio server and an interactive `virsh` disagree about which
domains exist, compare their environment before concluding that a domain is
missing. In the 2026-09-16 libvirt 12.7.0 test environment, the official Python
MCP SDK 2.2.0 stdio client omitted `XDG_RUNTIME_DIR` when no explicit child
environment was supplied. That selected a different `qemu:///session` daemon
from the desktop shell, and each daemon consistently saw a different domain
set. Forward the VM owner's actual runtime directory explicitly in the MCP
client environment when that is the intended session, then compare
`XDG_RUNTIME_DIR` and `virsh --connect qemu:///session list --all` on both sides
before attempting recovery. This is an observed version-specific failure mode,
not a claim that every SDK client, libvirt version, or host behaves this way.

## Verification boundary

Automated tests use fake command/lifecycle adapters, temporary files, protocol
framing, and (when available) temporary `qemu-img` backing chains. They do not
connect to libvirt, start a server against a user's session, or create/start/
stop a real VM. A live lifecycle smoke test requires separate authorization and
a disposable VM. On 2026-09-16, an authorized smoke test with libvirt 12.7.0,
QEMU 11.1.1, virt-clone 5.1.0, and guestfs 1.56.0 exercised the installed
OpenCode launcher through the official MCP client: flattened publication,
linked creation, inspection, passt loopback SSH, start/shutdown, key-based guest
access, Python execution, `pdb`, and an SSH-forwarded HTTP request. That measured
one local Ubuntu 26.04 image; it does not turn live virtualization into a CI
prerequisite or claim compatibility with arbitrary domain XML.

Debian 13 coverage uses an inactive XML definition inspected on 2026-09-16,
sanitized into a fixture. Parsing, publication, sibling linked clones, default
sizing preservation, and powered-off BIOS/no-NVRAM snapshot/restore are covered
with fake host-command adapters. Debian guest boot, preparation, SSH access,
and first-boot identity regeneration have not been live-tested.

CachyOS coverage uses an inactive XML definition inspected on 2026-09-16,
sanitized into a fixture. Fake-host lifecycle tests cover independent linked
disks and NVRAM copies, retained sizing/firmware/memfd configuration, and
powered-off snapshot/restore. CachyOS preparation, libguestfs guest access,
UEFI boot, SSH, and first-boot identity regeneration have not been live-tested.
