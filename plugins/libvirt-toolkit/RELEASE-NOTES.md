# Libvirt Toolkit Release Notes

## v1.0.7 (2026-09-16)

### Guest access handoff

- **Project-in-VM requests now continue beyond a running domain into an explicit
  provider and guest-access handoff.** Earlier lifecycle guidance could stop at
  boot and leave SSH reachability, trusted host identity, intended-account
  authentication, clone identity, transfer, and requested execution untested.
  The provider recipe now preserves host/session/domain context, configures a
  collision-aware per-clone passt loopback forward, handles remote-host loopback
  without confusing trust identities, and keeps optional QGA evidence separate
  from normal-user SSH success.
- **The bundle now carries the provider-neutral `guest-access` skill as well as
  `libvirt-vms`.** Standalone and bundled selection use the installer's existing
  byte-identical shared-file ownership policy, and source-removal coverage keeps
  both skills and their references usable after installation. OS preparation
  references retain their distinct evidence boundaries while converging on the
  shared access workflow instead of duplicating generic SSH advice.
- **Unavailable source/sibling comparisons now remain visible without becoming
  an implicit access veto.** The original handoff wording did not define when
  clone-identity evidence was a required stage, so an agent could stop a project
  workflow despite independently trusted endpoint identity and intended-account
  authentication. Comparison remains mandatory when the user or policy requires
  clone-uniqueness proof; otherwise the uncertainty stays `untested` while
  authenticated transfer and execution can proceed.
- **Guest access now pins the verified guest identity through every transport,
  and passt forwarding fails before XML mutation when its backend is absent.**
  Effective SSH configuration can otherwise silently select a different trust
  store, alternate trust source, reused multiplexed session, or permissive
  host-key policy, while an unavailable passt executable may surface only at VM
  start. The workflow now inventories `ssh -G`, explicitly
  enforces the selected verified trust store as the sole guest trust source for
  SSH, SCP, and rsync without
  discarding identity/agent/jump routing, delays guest authentication until trust
  is established, and checks passt in the VM owner's host context first.

## v1.0.6 (2026-09-16)

### CachyOS templates

- **Existing `CachyOS` domains now have explicit preparation and project-clone
  guidance.** The Ubuntu/Debian references did not establish Arch's SSH package,
  service, or host-key regeneration assumptions, nor the NVRAM requirements of
  a UEFI preparation copy. The CachyOS reference covers those checks and clarifies
  that observed memfd-backed RAM is distinct from rejected shared-memory devices.
- **Observed CachyOS firmware and clone independence have regression coverage.**
  A sanitized domain fixture protects publication, independent linked disks and
  NVRAM, preserved sizing/firmware/memfd configuration, and powered-off restoration
  of saved configuration and firmware state. Packaging coverage requires the new
  reference after source removal so installed users retain the preparation path.
  No OS-specific lifecycle branch is needed; evidence is XML inspection and
  fake-host tests, not live CachyOS preparation, boot, or SSH verification.

## v1.0.5 (2026-09-16)

### Debian 13 templates

- **Existing `debian13-dev-template` domains now have explicit preparation and
  project-clone guidance.** The Ubuntu-only skill left Debian compatibility
  unclear even though the observed Debian XML already fits the lifecycle core.
  The Debian reference covers disposable-copy preparation, first-boot identity
  and SSH-key regeneration, publication, and separate project access without
  assuming Ubuntu's SSH socket or a cloud-init installation.
- **Observed Debian BIOS/no-NVRAM behavior is protected by regression coverage.**
  A sanitized real domain fixture checks publication, independent linked clones,
  split current/configured sizing, and powered-off snapshot/restore so Debian's
  firmware-free path remains usable. Installed-package coverage requires its
  preparation reference to survive source removal. Evidence is limited to XML
  inspection and mocked lifecycle tests; Debian guest boot remains unverified.

## v1.0.4 (2026-09-16)

### Measured lifecycle guidance

- **The Ubuntu preparation reference now separates the untested original
  installer command from the lifecycle that was actually exercised.** The
  measured offline recipe includes the image-specific SSH socket enablement and
  a caller-selected preparation hostname so operators do not mistake an
  incomplete excerpt or test-specific identity for a portable recipe.
- **Troubleshooting now records the observed stdio environment boundary because
  two valid per-user libvirt daemons can otherwise look like a lost domain.** It
  tells operators to forward and compare the VM owner's runtime environment
  before attempting recovery, while limiting the claim to the tested libvirt
  12.7.0 and official Python MCP SDK 2.2.0 combination.

## v1.0.3 (2026-09-16)

### Verified domain creation

- **A successful `virsh define` exit is no longer treated as sufficient proof
  that a working VM exists with the intended ownership boundary.** Creation now
  reads the inactive domain back and verifies its name, UUID, disk, and NVRAM
  before committing registry metadata or clearing the operation journal. A
  missing or inconsistent domain returns `recovery_required` with retained
  resources so operators investigate the boundary instead of blindly retrying.

## v1.0.2 (2026-09-16)

### Live lifecycle compatibility

- **Authorized installed-client testing now covers the real Ubuntu development
  workflow instead of relying only on fixtures.** Managed-save absence accepts
  libvirt 12.7.0's current diagnostic wording, allowing a confirmed shut-off
  source to publish while other inspection failures still stop safely.
- **Per-VM SSH access on user networking no longer requires an unsafe wildcard
  or a cloned fixed port.** The domain parser narrowly accepts bounded TCP passt
  forwarding on `127.0.0.1`, rejects host-device and unbounded forms, and strips
  every forward during cloning so operators must select a unique port for each
  working VM.
- **The Ubuntu preparation recipe records the measured offline identity and SSH
  workflow because deleting keys without arranging first-boot regeneration can
  leave an otherwise valid clone unreachable.** It also calls out guest fstab
  aliases that can block libguestfs inspection rather than recommending a
  validation bypass.

## v1.0.1 (2026-09-16)

### Domain compatibility

- **Ordinary virt-manager Ubuntu guests can now be published without weakening
  host-resource isolation.** The parser accepts the observed SPICE audio and USB
  redirection devices, ICH9 sound, reset-only iTCO watchdog, and nested ISA
  serial model emitted by libvirt while continuing to reject host-backed audio,
  alternate redirection transports, host paths, and unrecognized child shapes.

## v1.0.0 (2026-09-16)

### Lifecycle Core

- **Managed templates and working VMs use a deliberately narrow, verifiable
  storage contract.** Flattening publication into immutable owned QCOW2 images,
  creating linked working overlays with independent UEFI state, and rejecting
  host-bound devices avoids cloning source identities or deleting arbitrary
  source files. Host locking, ownership checks, bounded commands, and retained
  partial-operation journals make concurrent or interrupted mutations fail
  safely instead of guessing whether external side effects occurred.

### MCP adapter

- **The official Python MCP SDK is pinned in a self-contained PEP 723 launcher
  so local and SSH stdio installs remain reproducible after the marketplace
  checkout is removed.** Typed schemas reject malformed requests before the
   lifecycle core runs, worker-thread dispatch keeps protocol handling responsive
   during bounded blocking commands, and structured tool errors preserve safe
   recovery details for clients.

### Packaging and workflow

- **A bundle-bound workflow skill and generated OpenCode projection keep host
  selection and destructive recovery decisions visible instead of hiding them
  behind generic VM automation.** The bundle now ships the pinned launcher,
  local MCP registration, Ubuntu source-preparation reference, local/SSH setup,
  powered-off snapshot boundaries, and manual journal-recovery guidance so an
  installed copy remains usable without the marketplace checkout and operators
  do not confuse toolkit layers with native libvirt snapshots.
