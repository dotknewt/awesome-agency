# vault/ — the project's memory

Plain Markdown + flat YAML frontmatter. Open this folder as an Obsidian vault, or let Claude Code agents read/write it
through the `obsidian` MCP server (rooted here) and native tools. Start at `INDEX.md`.

| Folder | What lives here | Who writes |
|---|---|---|
| `INDEX.md` | root map, one line per entry (≤150 lines) | agents (`/vault-save`, `/vault-session`), you |
| `kb/` | atomic project knowledge; `kb/decisions/adr-NNNN-*.md` = decisions; `kb/moc-*.md` = hubs | `/vault-save`, curator |
| `docs/` | how-tos, reference, explanations, tutorials (Diátaxis) | `/vault-save`, curator |
| `sources/` | one note per external source: provenance + verbatim excerpts + claims | `vault-researcher` |
| `plans/` | plan-mode output (Claude Code writes here) | plan mode; hook stamps frontmatter |
| `sessions/` | one note per Claude Code session (generated + curated sections) | Stop/PostCompact/SessionEnd hook, `/vault-session` |
| `archive/` | retired notes, same basename, flat under `archive/kb|docs|sources/` | curator |
| `_templates/` | note templates (Obsidian Templates folder) | you |
| `_bases/` | Obsidian Bases dashboards (`review-due.base`) | you |

The ten rules (full spec: `.claude/skills/vault-conventions/SKILL.md`):
1. Every note has frontmatter: `type, title, description (≤160 chars), status, created, updated, tags` + per-type keys.
2. Filenames are kebab-case and **unique across the whole vault**; link with `[[basename]] — why`.
3. `tags` is always a YAML list; **no inline `#hashtags`** in bodies.
4. One claim per kb note; the title is the claim; cite `evidence` you can re-verify.
5. Search before you create; update > create; supersede > overwrite; archive > delete.
6. Bump `updated` on every meaningful edit; set `reviewed`/`review_after` when you verified a claim.
7. ADRs are never rewritten after acceptance — write a new one and link `supersedes`/`superseded_by`.
8. Sources are provenance: verbatim excerpts are immutable after capture.
9. Sessions and plans are history, not knowledge — extract knowledge into `kb/`, keep the log.
10. Nothing personal, transient, secret, or from other projects goes in here.
