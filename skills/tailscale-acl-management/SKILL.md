---
name: tailscale-acl-management
description: Use when asked to write, simplify, refactor, or review Tailscale ACLs, grants, or tailnet HuJSON policies; make access rules leaner or easier to read; investigate overlapping permissions or bypassed posture requirements; audit SSH and tag access; or migrate ACLs to grants.
---

# Tailscale ACL Management

Optimize for an understandable access model, not the fewest lines. Preserve
effective permissions during cleanup; identify proposed access changes explicitly.

**Evaluate network permissions as a union across all matching ACLs and grants.**
Treat neither rule order nor specificity as an override. A narrow rule cannot
subtract access allowed by a broader one elsewhere.

## Establish the policy and intent

1. Read the complete policy and existing tests when available. For a supplied
   fragment, identify conclusions that depend on omitted rules or defaults.
2. Identify the requested mode: new policy, readability refactor, access review,
   or migration. Preserve the existing ACL/grant style during cleanup; prefer
   grants for new policies, following Tailscale's recommendation.
3. Map intended flows as source → destination → protocol/port → conditions.
   For new policies, obtain missing identities and required flows rather than
   inventing group membership, tags, or broad access.
4. Read [the policy review reference](references/policy-review.md) before assessing
   semantics, and [the worked examples](references/examples.md) when rewriting
   rules or proposing tests. Consult the linked official documentation for fields
   outside that reference, changing syntax, or uncertain behavior.

## Review effective access

Trace overlapping selectors through groups, tags, hosts, IP sets, CIDRs, and
autogroups. Account for effective posture defaults, protocols, application
capabilities, and `via`. Distinguish known membership from assumptions about
device ownership, external sharing, SCIM groups, or deployed tag assignments.

For each apparent restriction, find every other rule that can authorize the same
flow. Give a concrete witness: source identity/device, destination, protocol/port,
posture state, and the rule that admits it. Cite rule indices or nearby comments.
Describe a broad allow as an alternative authorization path, not a later override.

Prioritize demonstrated access beyond the stated intent, then unclear ownership
or administration boundaries, then readability. Explain why a broad rule is
questionable in context; avoid calling every wildcard a defect. Evaluate SSH
separately using its own `check`/`accept` semantics.

## Simplify deliberately

| Change | Required reasoning |
| --- | --- |
| Remove exact duplicates | Preserve useful intent comments. |
| Merge rules | Hold all dimensions but one identical; prove no new source–destination–permission combinations. |
| Remove a covered rule | Prove coverage including conditions, not just matching text. Explain any restrictive-looking intent it concealed. |
| Introduce groups/hosts | Preserve membership/address meaning; add an abstraction only when it improves comprehension or reuse. |
| Replace hosts with tags | Treat device identity and assignment changes as access changes. |
| Narrow ports, CIDRs, or selectors | Label as a permission change, even when desirable. |

Use descriptive role/resource names, short HuJSON arrays, consistent indentation,
and comments explaining purpose or exceptions. Group rules by access purpose.
Prefer a few readable rules over a dense matrix. Preserve unrelated sections and
meaningful empty fields. Keep ACL-to-grant migration separate from cosmetic edits.

## Verify the result

Preserve existing tests. Add explicit-protocol positive and negative assertions
for affected flows, forbidden cross-combinations, and relevant posture pass/fail
states. Distinguish **current-behavior regression tests** from **intended-boundary
tests**: show a boundary test expected to fail under an identified broad allow,
then explain which proposed permission change would make it pass. Never present
that failing assertion as a passing test for an unchanged policy.

Use a HuJSON-aware parser for syntax and Tailscale's policy validation/test
facility for policy semantics. Use an existing repository validation workflow
when available; otherwise consult current admin-console or API documentation.
Do not invent a `tailscale acl validate` command. Report tests as proposed until
actually run; distinguish sampled authorization checks from equivalence proof and
live connectivity. Follow the user's requested edit/deployment scope.

## Return a useful result

Lead with the most important effective-access finding. Include:

- **Findings:** rule locations, concrete consequence, and a clearer alternative.
- **Cleanup:** a readable policy or focused diff, with permission impact stated.
- **Access recommendations:** affected flows and the reason to change them.
- **Verification:** assertions, actual results, and unresolved membership assumptions.

Keep the response proportional to the policy. Use the bundled
[task evals](evals/evals.json) and [trigger cases](evals/eval_queries.json) when
maintaining this skill.
