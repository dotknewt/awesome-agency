# Policy semantics and review pitfalls

Use these notes as a review guide, not as a replacement for the full syntax.
Ground syntax decisions in the following official references, consulted
2026-10-16:

- [Tailnet policy-file syntax](https://tailscale.com/docs/reference/syntax/policy-file.md)
  — primary reference; ACLs, identities, SSH, automation, and tests.
- [Grants syntax](https://tailscale.com/docs/reference/syntax/grants.md)
  — union semantics, `ip`, `app`, and `via`.
- [Postures in access rules](https://tailscale.com/docs/features/device-posture/postures-in-access-rules.md)
  — alternatives, defaults, and source limitations.
- [ACL examples](https://tailscale.com/docs/reference/examples/acls.md)
  — explicit deny-all versus default allow-all.
- [Managing policies](https://tailscale.com/docs/features/tailnet-policy-file/manage-tailnet-policies)
  — current editing and validation workflows.

Recheck the relevant official page when encountering unsupported fields or
ambiguous details. Preserve HuJSON comments and trailing commas; do not use
strict JSON parsing failures as evidence that a policy is invalid. Do not strip
comments with regexes that can corrupt quoted strings.

## Evaluate network rules together

Treat each applicable rule as an additional allow. Combine permissions across
`acls` and `grants`; neither section has priority over the other. Use default
denial only when no applicable rule grants access in an explicitly defined
access policy. Never propose an ACL/grant `deny` action or a later restrictive
rule as a way to subtract permissions.

Compare the complete relation:

`source × destination × protocol/port × effective conditions`

For grants, include routing restrictions and application capabilities as
additional dimensions. Treat members of `src` and `dst` arrays as alternatives,
not paired entries or intersections. For example, `dst: ["tag:prod", "tag:db"]`
means prod **or** db, not databases in production. Account for devices with
multiple tags and users belonging to several groups.

To merge rules safely, hold every dimension except the combined one equivalent.
Combining destinations with different port sets in a grant creates extra
destination–port pairs; combining distinct sources and destinations creates
extra source–destination pairs. Retain separate rules when the compact form
cannot express the original relation clearly.

Treat overlap as redundancy only after proving full coverage. Do not infer
dynamic selector equivalence from a snapshot of today's membership. Keep
future intent visible when a currently redundant rule represents a distinct role.

### Distinguish the two network syntaxes

| Aspect | ACL | Grant |
| --- | --- | --- |
| Action | `"action": "accept"` | Implied accept; no `action` field |
| Endpoint | `"dst": ["tag:web:443"]` | `"dst": ["tag:web"]` |
| Protocol/port | `"proto": "tcp"` plus destination ports | `"ip": ["tcp:443"]` |
| Omitted protocol | TCP and UDP | Bare `"443"` permits TCP and UDP |
| Other capabilities | Network access | `app` and route selection with `via` |

Preserve TCP/UDP and documented ICMP implications during migration. Account for
ICMP permission associated with permitted network traffic; do not promise that
a TCP-only service rule necessarily blocks ping. Consult protocol-specific syntax
for non-port protocols. Use port `*` for those protocols, not fabricated service
ports. Preserve direction: permission to initiate A → B does not grant B → A;
do not add a reverse rule merely for response traffic.

Preserve an explicit `"acls": []` when it is the only network-access section.
Removing it can activate default allow-all behavior. Do not assume omitted and
empty sections are equivalent, or that an empty ACL list cancels nonempty grants.
Evaluate the complete policy before removing any empty access-control section.

## Review posture conditions

Distinguish three logical levels:

- Require all assertions inside a single posture.
- Treat multiple names in `srcPosture` as **OR** alternatives.
- Apply `defaultSrcPosture` when no per-rule condition is specified; treat an
  explicit condition as a replacement, not an extra requirement on top of it.

To require several conditions together, place them in the same posture's
assertions. Do not concatenate posture names expecting an AND. Prefer the
documented object syntax (`assertions`, optional `onFailure`) for new postures;
preserve supported legacy array syntax during a readability-only edit.

Check every alternative allow for effective posture requirements. A rule without
`srcPosture` might inherit a default, so do not automatically call it unrestricted.
Also check the documented default-posture limitation: shared nodes and devices
behind subnet routers lack the relevant local node attributes and are not
restricted by `defaultSrcPosture` when they match the IP conditions.

Read assertions rather than trusting names: `posture:managed` checking only
`node:os == 'linux'` establishes an OS condition, not device management.

## Keep identities and administrative powers distinct

| Construct | Meaning and review action |
| --- | --- |
| `groups` | Use named user sets; do not nest local groups. Treat SCIM membership as external state. |
| `hosts` | Use aliases for IPs/CIDRs, not DNS lookups or device identity assignments. |
| `tagOwners` | Determine who can assign a tag; neither assign the tag nor grant network access by declaring it. |
| Tags | Select tagged device identities; do not substitute them for user-owned devices as cosmetic cleanup. |
| `autogroup:self` | Match the source user's own user-owned devices; exclude tagged devices. |
| `autogroup:member` | Distinguish direct members from shared users and tagged identities; do not equate it with `*`. |
| `ipsets` | Name network sets; verify membership and selector support before replacing CIDRs. |

Keep empty tag-owner lists meaningful: `"tag:build": []` still permits
administrative assignment, including Admin and Network admin roles. Do not
describe it as a tag nobody can assign. Review broad tag delegation when tags
confer powerful source access, route approval, or application privileges.

Search all sections before deleting an apparently unused group, host, or tag.
For tags, account for deployed devices, enrollment/auth-key workflows, and
references from `autoApprovers`, SSH, routing, and node attributes. Do not infer
that an unused-in-ACL tag is operationally unused.

## Separate routing, application, and SSH behavior

**Routing:** Treat `autoApprovers` as approval of advertised routes/exit nodes,
not permission to send traffic. Treat router access and access to the subnet
behind it separately. Check the destination CIDR, including narrower routes
covered by auto-approval. Account for advertisements, approval, and forwarding
when explaining actual reachability. Do not imply grants inject routes.

Use `autogroup:internet` for exit-node internet access. For grants using `via`,
retain its tag-based router restrictions and inspect alternative matching grants
without that restriction. Do not claim an EU-only grant forces all access through
EU while another rule admits an unrestricted path. Verify actual route selection
separately from network authorization tests. Use IPv6 destinations for 4via6.

**Applications:** Preserve `app` objects and their association with source,
destination, and conditions. Treat application capabilities as additive, with
network connectivity also needed. Consult the application's capability schema:
Tailscale treats parameter objects as opaque JSON, so policy syntax validation
does not establish application-level correctness. Do not merge arbitrary payloads
or claim a network test proves an application role is restricted.

**SSH:** Require both network permission to TCP/22 and Tailscale SSH authorization.
Keep operating-system usernames separate from Tailscale identities. Apply SSH
`check` before `accept` for matching flows, regardless of order; do not reuse
network-union reasoning to claim `accept` bypasses a matching `check`.
Compare `users`, effective posture, `checkPeriod`, and `acceptEnv` before treating
SSH rules as duplicates. Preserve reauthentication and environment constraints.

Use valid SSH destination identities, such as tags or `autogroup:self` under its
source restrictions; do not add ports to SSH destinations. Treat
`autogroup:nonroot` as every non-root account, not just the caller's usual account.
Flag that expansion when changing a self-device rule to a shared server tag.
Do not use check mode for tagged-device sources. Verify SSH enablement and local
account existence separately from policy tests.

## Write assertions that test the intended boundary

Use native `tests` for ACL/network-grant outcomes and `sshTests` for SSH
authorization outcomes. Treat `deny` inside a test as an assertion, not an
enforcement rule. Adding a failing test prevents accepting that policy update;
it does not revoke access in the currently active policy.

- Set `proto` explicitly when distinguishing TCP and UDP; omitted `proto` checks
  for either and can conceal protocol mistakes.
- Use a concrete supported source and single numeric-port destinations such as
  `192.0.2.10:443` or `tag:web:443`. Do not put wildcard, CIDR, or port-range
  destinations in network tests. For a subnet, choose actual representative IPs
  and relevant boundary addresses. Use bracketed IPv6 endpoints.
- Use `srcPostureAttrs` with concrete attribute values for both passing and
  failing posture cases. Cover OR alternatives and default-replacement cases.
- For ICMP assertions, use `"proto": "icmp"` and destination port `0`.
- In `sshTests`, use `src`, a destination list, and OS usernames in `accept`,
  `check`, or `deny`. Keep network tests separate; SSH tests do not prove port 22
  is reachable or validate the exact reauthentication interval.

Run existing assertions and current-behavior regressions against both versions.
For an identified overbroad allow, show an intended-denial assertion expected to
fail before the access fix and pass afterward. Preserve the distinction between
syntax validation, sampled policy authorization, full equivalence reasoning, and
live connectivity. Report unexecuted validation plainly.
