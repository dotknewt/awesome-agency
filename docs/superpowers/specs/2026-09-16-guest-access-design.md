# Guest access and libvirt handoff

Accepted by the user on 2026-09-16 after brainstorming and the in-chat implementation plan.

## Goal and scope

Make project-in-VM requests continue from lifecycle operations through verified access,
transfer, and guest execution. Create a provider-neutral `guest-access` skill, independently
installable and bundled in `libvirt-toolkit`. Implement only the libvirt provider integration
in this iteration. Use existing CLI tools; defer an SSH MCP until behavioral evaluations
demonstrate an execution problem requiring structured tooling.

## Responsibilities

- `guest-access`: capability discovery, endpoint/host identity/authentication, regular-user
  execution context, transfer, command outcomes, and stage-by-stage evidence. Detailed SSH
  examples live in its own relative `references/ssh-workflow.md`.
- `libvirt-vms`: provider target/session, domain/network inspection, passt loopback forwarding,
  QEMU guest-agent diagnostics, and an explicit handoff for requests requiring guest access.
  Detailed provider guidance lives in `references/guest-access.md`.
- Existing libvirt MCP: lifecycle/storage operations only. Do not bypass its rejection or
  recovery rules with other tooling. Missing guest APIs do not prove missing host capabilities.

## Handoff and completion

Use a lightweight Markdown record with requested outcome, provider/host/owner/session/domain,
connection origin, candidate address/port and provenance, intended account/home, domain and
guest identity evidence, available tools, and per-stage progress. Unknown values stay unknown
until needed and investigated. Invoke the companion skill by name rather than assuming
cross-skill filesystem paths. Standalone guest-access must not depend on libvirt installation.

Keep lifecycle, guest prerequisites, SSH authentication, clone identity, transfer, and requested
execution separately marked `verified`, `failed`, `untested`, or `not applicable`. Report command,
execution location/account, exit status, and relevant output for execution claims. Lifecycle-only
requests do not trigger guest configuration; project-execution requests cannot end at boot.

Verify the endpoint from the connection origin and distinguish client, virtualization host,
and guest. Check routes before interpreting an advertised IP or refused connection. With passt,
cloning strips forwards: configure a fresh free unprivileged host-loopback forward while the
working clone is shut off; preserve graceful shutdown and ownership rules; verify after start.
For a remote host, explain how the client reaches that host's loopback endpoint.

Validate SSH host-key trust before authentication/project transfer. A scanned key alone is not
trusted identity. Verify clone identity where applicable and report unavailable source/sibling
comparisons honestly. Run setup as the intended guest user with the correct home and cwd.
An unavailable source/sibling comparison is disclosed as `untested`, not an automatic block
on independently trusted SSH access, transfer, or execution. Require that comparison to pass
only when the requested outcome or an applicable policy explicitly requires clone-uniqueness
proof. Mandatory endpoint trust and intended-account authentication are separate requirements.
QGA is a separate optional diagnostic path; discover supported commands, use bounded polling,
decode output, and distinguish process creation from completion. QGA commonly runs privileged;
its success does not verify SSH or the intended user's project workflow.

## Distribution

Ship `skills/guest-access/` as a normal micro-entry and symlink the directory into libvirt-toolkit.
Keep every relative reference self-contained after source removal. Update the bundle release
from inspected 1.0.6 to 1.0.7 with rationale-bearing notes and align the existing advertised MCP
version. Generate marketplace output. Document refresh/restart requirements for other projects.

## Evidence and validation

The motivating diagnostic report verified QGA execution, sshd, account, authorized-key match,
and rsync; SSH authentication, transfer, setup, and clone identity were untested. The prior
Ubuntu smoke test is separate evidence. Do not generalize either observation across OS images.

Evaluate three synthetic scenarios in fresh baseline/with-skill contexts: QGA available but
no passt forward; host-local reported IP; remote virtualization host with a project execution
request. Include positive access triggers and lifecycle-only negative triggers. Grade decisions,
not phrasing. Tests exercise installed-content survival and discovery, not prose substrings.
Run repository-required checks and independent task/final SDD reviews.

## Global Constraints

- Preserve existing modified and untracked source; review incremental changes against a captured dirty-checkout baseline.
- Use `openai/gpt-5.6-sol` for every delegated role; controller owns all dispatches and records actual model/task identity.
- Do not stage, commit, push, or refresh another project's installation.
- Do not perform live VM mutations, real SSH connections, repository transfers, or guest setup; use synthetic evidence and temporary installation projects.
- Keep libvirt MCP lifecycle-only and preserve rejection, recovery, ownership, and power-state rules.
- Keep standalone skill installations self-contained and regenerate marketplace output rather than hand-editing it.
- Report lifecycle, prerequisites, SSH authentication, clone identity, transfer, and execution separately using verified / failed / untested / not applicable.
- Preserve distinctions between QGA diagnostics, SSH authentication, and normal-user project execution, and between prior Ubuntu and CachyOS evidence.
