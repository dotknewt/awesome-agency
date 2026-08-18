---
name: project-verify
description: Defines precise, measurable evaluation criteria and identifies any external signal that would prove success for an idea already spec'd out — the second of three spec-gap-closing layers, run before any code, docs, or planning. Writes specs/SLUG/verify.md. Use when invoked directly ("define done for X", "what would prove this works") or as the second step dispatched by project-manager, after project-spec has completed.
---

# project-verify

## Why this exists

"Define the criteria for a great result" is easy to say and easy to get wrong — "make the report look good" and "the report must have 3 sections, each ending with a recommendation" both sound like criteria, but only one can actually be checked. This skill's job is to force every evaluation criterion for the idea to be as concrete as the second example, and to make explicit whether anything outside the spec itself — a live system, a deployed service, a comparison to existing examples — could be consulted to verify success.

Read `references/checkpoint-protocol.md` before starting — the itemized claim test, load-bearing test, checkpoint timing, critic mechanism, and logging format are identical to project-spec's and are not repeated here.

## Standalone invocation and dependency check

This skill depends on `specs/SLUG/spec.md` existing with `status: complete` (or at least `spec` present in `layers_complete`). If it's missing or incomplete when you're invoked directly:

> "verify needs a signed-off Goal/Scope from project-spec to ground its criteria in. Run project-spec first, or proceed anyway knowing the criteria won't be grounded in an agreed goal?"

Render this as an explicit choice — never silently proceed and never silently refuse. If the user chooses to proceed ungrounded, note that explicitly in `verify.md`'s frontmatter rather than pretending the dependency was satisfied.

## Interview flow

### Evaluation Criteria

Ask the user what "great" looks like for this specific idea, and push every answer through the itemized claim test:

- Bad (fails the test): "make sure the feature works well"
- Good (passes the test): "the report must have 3 sections, each ending with a recommendation"

If the user has past examples of similar work they consider good, ask for them and use their structure as the format to match — cite specifically what about the example makes it a good match ("this one's criteria are measurable because X"), don't just gesture at "match this."

### External Signal

Ask explicitly, per idea, whether anything outside the spec document could be checked to verify success — a health-check endpoint, a comparison against a competitor's behavior, a specific log line, a metric dashboard. This is genuinely idea-dependent and cannot be templated in advance; do not invent a generic answer.

- If the user identifies a real external signal, record it as its own claim and run it through the itemized test too (a signal description needs to be specific enough to actually check later — "verify it works" is not a signal, "curl https://api/health returns 200" is).
- If no external signal applies to this idea, record `External Signal: N/A — <why>` explicitly. A silently omitted section is a gap; an explicitly justified N/A is not.

## Writing verify.md

```markdown
---
idea: "<working title>"
slug: <slug>
status: draft | in-progress | complete
depends_on: [spec.md]
layers_complete: [spec]
---

## Evaluation Criteria
<itemized, measurable claims>

## External Signal
<specific check, or "N/A — <reason>">
```

Restate (don't just link to) the specific Goal/Scope claims from spec.md that each evaluation criterion is grounded in, so this file is readable on its own without requiring the reader to open spec.md. Target 200-500 words. Append every checkpoint to `specs/SLUG/verify.decisions.log` per the protocol's logging format. Set `status: complete` and add `verify` to `layers_complete` only after both sections have explicit human approval logged.

## Handing off

When `verify.md` reaches `status: complete`, tell the user the Verification layer is done and `project-environment` is next.
