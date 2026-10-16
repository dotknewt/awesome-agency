# Worked refactor and overlap review

Adapt example identities and addresses to the real tailnet. Treat these as
documentation examples, not policies validated against a live tailnet.

## Consolidate identical access intent

Start with a complete policy granting the same team two TCP services on one host:

```json
{
  "groups": {"group:ops": ["alice@example.com", "bob@example.com"]},
  "hosts": {"build": "100.64.0.8"},
  "acls": [
    {"action": "accept", "src": ["group:ops"], "proto": "tcp", "dst": ["build:22"]},
    {"action": "accept", "src": ["group:ops"], "proto": "tcp", "dst": ["build:443"]}
  ]
}
```

Keep the ACL style and combine only the destination ports. Add tests covering
intended ports, a forbidden port, and the protocol distinction:

```json
{
  "groups": {"group:ops": ["alice@example.com", "bob@example.com"]},
  "hosts": {"build": "100.64.0.8"},
  "acls": [
    {
      "action": "accept",
      "src": ["group:ops"],
      "proto": "tcp",
      "dst": ["build:22,443"]
    }
  ],
  "tests": [
    {
      "src": "alice@example.com", "proto": "tcp",
      "accept": ["build:22", "build:443"], "deny": ["build:5432"]
    },
    {
      "src": "bob@example.com", "proto": "tcp",
      "accept": ["build:22", "build:443"], "deny": ["build:5432"]
    },
    {
      "src": "alice@example.com", "proto": "udp",
      "deny": ["build:22", "build:443"]
    }
  ]
}
```

For an explicitly requested migration, replace the `acls` section with the
following `grants` section, preserving the other fields and tests:

```json
"grants": [
  {
    "src": ["group:ops"],
    "dst": ["build"],
    "ip": ["tcp:22", "tcp:443"]
  }
]
```

Do not change the ports to bare `"22"` and `"443"`: that would add UDP permission.

## Refuse a merge that invents new flows

Keep these distinct grants separate:

```json
{
  "grants": [
    {"src": ["alice@example.com"], "dst": ["192.0.2.10"], "ip": ["tcp:22"]},
    {"src": ["bob@example.com"], "dst": ["192.0.2.20"], "ip": ["tcp:443"]}
  ],
  "tests": [
    {
      "src": "alice@example.com", "proto": "tcp",
      "accept": ["192.0.2.10:22"],
      "deny": ["192.0.2.10:443", "192.0.2.20:22", "192.0.2.20:443"]
    },
    {
      "src": "bob@example.com", "proto": "tcp",
      "accept": ["192.0.2.20:443"],
      "deny": ["192.0.2.10:22", "192.0.2.10:443", "192.0.2.20:22"]
    }
  ]
}
```

Explain that combining both users, both destinations, and both ports in a single
grant produces eight allowed TCP combinations instead of two. Cite Alice →
`192.0.2.20:443` as one concrete new permission. Prefer two clear rules over a
one-rule policy that changes the access model.

## Demonstrate a posture restriction bypass

Review this complete policy against the stated intent: "Only Linux ops devices
may reach production, and only on SSH." Assume Alice and Bob are direct tailnet
members, both user-owned source devices exist, and production devices have the
declared tag.

```json
{
  "groups": {"group:ops": ["alice@example.com"]},
  "tagOwners": {"tag:prod": []},
  "postures": {
    "posture:linux": {"assertions": ["node:os == 'linux'"]}
  },
  "grants": [
    {
      "src": ["group:ops"],
      "dst": ["tag:prod"],
      "ip": ["tcp:22"],
      "srcPosture": ["posture:linux"]
    },
    {
      "src": ["autogroup:member"],
      "dst": ["tag:prod"],
      "ip": ["*"]
    }
  ]
}
```

Report the finding in concrete terms:

> `grants[1]` permits Alice on Windows to reach prod TCP/22 and permits Bob to
> reach prod TCP/5432. `grants[0]` adds a conditional allow; it cannot restrict
> `grants[1]`. Reordering them changes nothing. Removing or narrowing the broad
> grant would enforce the stated boundary, but changes existing permissions.

Propose these **intended-boundary** tests, expected to fail against the policy
above and pass after removing the broad grant:

```json
"tests": [
  {
    "src": "alice@example.com", "proto": "tcp",
    "srcPostureAttrs": {"node:os": "linux"},
    "accept": ["tag:prod:22"], "deny": ["tag:prod:5432"]
  },
  {
    "src": "alice@example.com", "proto": "tcp",
    "srcPostureAttrs": {"node:os": "windows"},
    "deny": ["tag:prod:22"]
  },
  {
    "src": "bob@example.com", "proto": "tcp",
    "srcPostureAttrs": {"node:os": "linux"},
    "deny": ["tag:prod:22", "tag:prod:5432"]
  }
]
```

For a readability-only refactor, retain the broad permission and explain the
finding. Record these currently permitted witness flows under `accept` in
regression tests instead; do not attach failing denial tests to a supposedly
validated permission-preserving output. Distinguish permission to reach port 22
from authorization to use Tailscale SSH.

Apply the same reasoning if the broad grant is instead an ACL such as
`{"action":"accept","src":["autogroup:member"],"dst":["tag:prod:*"]}`.
