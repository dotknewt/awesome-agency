## Project Memory

Durable project memory lives in `vault/` (Markdown + flat YAML frontmatter, Obsidian-compatible). Auto-memory is OFF: nothing about
this project is stored in user-global memory, and personal preferences never go into the vault (they belong in `~/.claude/`).

## Map — the `obsidian` MCP server is rooted at `vault/`: MCP path `kb/x.md` == native path `vault/kb/x.md`
- `vault/INDEX.md` — root map (≤150 lines). Injected at SessionStart. Start here, not from search.
- `vault/kb/` — atomic project knowledge (`kind: fact|convention|gotcha|pattern|concept`), `kb/decisions/adr-NNNN-*.md` (ADRs), `kb/moc-<area>.md` (hubs)
- `vault/docs/` — human-facing docs (`kind: howto|reference|explanation|tutorial`, Diátaxis)
- `vault/sources/` — one note per external source: provenance + verbatim excerpts + claims; excerpts immutable after capture
- `vault/reference/` (only if the project ingests a corpus) — generated, pipeline-owned notes; never hand-edit, never search, never
  `[[basename]]`-link; read by path via the corpus's index notes (skill `vault-conventions` §1a).
- `vault/plans/` (plan-mode output) · `vault/sessions/` (hook-generated session notes) · `vault/archive/` (retired notes) — HISTORY:
  never read them by default; when continuing prior work read only the last session note's curated sections + the active plan.
- Conventions (types, frontmatter, naming, links, lifecycle): skill `vault-conventions` (from the vault-memory plugin).
  It auto-loads when you touch `vault/kb|docs|sources|archive` with native tools; when writing through MCP tools, invoke/read it first.

## Protocol
1. Index first, then search. Before non-trivial work run `/vault-find "<one-sentence task goal> + 3–6 key terms"` (identifiers, file
   paths, error strings, domain nouns; add `--history` when continuing prior work) — the read-only `vault-librarian` returns a ≤40-line
   briefing. Read at most 3–5 notes yourself, partially where possible (`get_note_outline` → `read_note_lines`). Never bulk-read a folder.
2. Persist with `/vault-save` when: a decision among alternatives was made; a non-obvious repo fact/gotcha/coupling was learned
   (>5 min to rediscover); the user corrected you or repeated a clarification; a repeatable ≥3-step procedure emerged (done ≥2×);
   an external source shaped code or a decision. Search before create · update > create · supersede > overwrite · archive > delete.
3. Never persist: transient state, raw tool output, secrets/tokens/keys, personal preferences, other projects' knowledge,
   anything derivable from code in <1 min, speculation (unless `status: draft` + `confidence: unverified`).
4. Trust but verify: before acting on a kb fact, check its `evidence` (grep the cited path/symbol). Wrong → fix now or set
   `status: needs-review` + `review_note`. Never leave a wrong note silently.
5. Run `/vault-session` before `/compact`, before ending a substantial session, and after finishing a major sub-task.
6. Maintenance is user-run: when the SessionStart briefing reports notes past `review_after`, *mention* it and suggest the user runs
   `/vault-review due` (user-only skill). If asked to review in chat, delegate to the `vault-curator` subagent with the scope and
   whether to apply safe actions. Large sweeps: `/vault-audit` (workflow, proposes only); web research with provenance: `/vault-research`.
   Deletions always need user confirmation (`delete_note` prompts and only `trashMode:"local"` is allowed).
7. Delegate to keep context clean: `vault-librarian` (retrieval → briefing), `vault-researcher` (web → `sources/`),
   `vault-curator` (review/merge/archive). Subagents return digests and paths, never raw notes.
8. Budget: briefing ≤1.5k tokens + ≤4k tokens of note content per task; prefer 3 strong notes over 10 weak (distractors hurt).
9. When compacting, preserve: decisions made, open questions, next step, and the vault paths touched; drop tool outputs.

## Tools — which for what
- Ranked recall: `mcp__obsidian__search_notes {query, pathPrefix:"kb"|"docs"|"sources", excludePaths:["archive","sessions","plans","reference","_templates","_bases"], limit:15}`
  — substring-OR + BM25, no stemming → run 2–3 phrasings; `searchFrontmatter:true, searchContent:false` searches YAML text (tags/status/aliases).
- Exact strings, identifiers, backlinks (`\[\[basename`), enumeration (`Grep '^description:' vault/kb`, `Glob vault/**/*.md`): native Grep/Glob.
- Read: `get_frontmatter` (cheap triage), `read_multiple_notes` (≤10; `includeContent:false` = frontmatter only), `get_note_outline` + `read_note_lines`, `wiki_link`.
- Write: `write_note` (creates dirs; pass the `frontmatter` object; `overwrite` without it wipes YAML), `update_frontmatter {merge:true}` (arrays are
  replaced wholesale — read first, send the full list; keys can't be deleted), `patch_note` (exact unique string; sees YAML too), `move_note`
  (no link rewrite — patch referrers first), `delete_note` only `trashMode:"local"`. Never `manage_tags add/remove` (promotes body `#tokens`); `manage_tags list` is fine.
- Code, `.claude/**`, `AGENTS.md`, `.mcp.json`: native tools only (dot-paths and everything outside `vault/` are invisible to the MCP server).
- Lint the vault any time: `node ${CLAUDE_PLUGIN_ROOT}/hooks/vault-lint.mjs --all` (or `--all --json`). Hooks validate every write into `vault/`
  (hard violations are denied, schema issues are warned) — fix warnings immediately.
