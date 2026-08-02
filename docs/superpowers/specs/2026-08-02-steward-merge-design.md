# steward — merge maintainer-toolkit + instruction-management (design)

Date: 2026-08-02
Status: approved

## Problem

The marketplace shipped two complementary but fragmented plugins:

- `maintainer-toolkit` — the read side: four read-only drift-audit agents plus
  the `/maintain` orchestrator skill.
- `instruction-management` — the write side: skills that audit, revise, and
  restructure AGENTS.md, the `project-conventions` scaffolder, the
  `state-keeper` agent, and a Stop-hook nudge.

They already referenced each other ("if the instruction-management plugin is
installed, offer its skills…"), so the plugin boundary was artificial: users
had to install both to get the full audit → apply loop.

## Decision

Merge both into a single plugin bundle **`steward`** (v1.0.0) covering
maintenance of instructions, docs, specs, and schemas — reporters and fixers
together. Both old bundles are removed outright (no deprecation stubs); this
is our own marketplace and users re-install `steward@agency`.

This supersedes the boundary statement in
`2026-08-02-maintainer-toolkit-design.md` ("`instructions-maintainer` does not
duplicate the instruction-management plugin; recommends it for applying
fixes") — the maintainers now recommend steward's own bundled skills.

## Naming

Skills are renamed into a domain-grouped family; agents keep their names.

| Old | New |
|---|---|
| skill `maintain` | `maintain` (unchanged) |
| skill `instruction-management` | `instructions-audit` |
| skill `revise-instructions` | `instructions-revise` |
| skill `restructure-instructions` | `instructions-restructure` |
| skill `project-conventions` | `conventions` |
| agents (all 5) | unchanged |
| `hooks/instruction-management/` | `hooks/steward/` |
| `revise-instructions-nudge.sh` | `instructions-revise-nudge.sh` (sentinel `/tmp/instructions-revise-nudge`) |

Names considered for the bundle: `maintainer-toolkit` (kept), `custodian`,
`scribe`, `steward`. `steward` won: it covers both auditing and keeping things
in order, and a fresh name signals the merge is a new thing rather than one
plugin absorbing the other.

## Consequences

- One bundle entry (`steward`) replaces two in marketplace.json; the
  `instruction-management-skill` collision rename in the generator is obsolete
  (`SKILL_ENTRY_RENAMES = {}`).
- Old standalone skill micro-entries (`instruction-management-skill`,
  `revise-instructions`, `restructure-instructions`, `project-conventions`)
  are replaced by the renamed ones; `maintain` persists unchanged.
- All five skills and five agents remain individually installable
  micro-entries.
- `.claude/settings.json` enables `steward@agency` in place of the two old
  plugins.
