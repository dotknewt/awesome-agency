---
name: vault-conventions
description: Authoritative schema and lifecycle rules for notes under vault/ — note types, folders, naming, frontmatter fields and allowed values, linking and tags, WHEN/WHAT/HOW to persist knowledge, how to find and rank notes, review/revise/supersede/archive/delete rules, anti-pollution rules. Load before creating, editing, reviewing or moving any vault note.
user-invocable: false
paths:
  - "vault/kb/**"
  - "vault/docs/**"
  - "vault/sources/**"
  - "vault/archive/**"
  - "vault/INDEX.md"
---
# Vault conventions (authoritative)

If a template, skill or agent prompt conflicts with this file, THIS file wins. Enforced mechanically by
`${CLAUDE_PLUGIN_ROOT}/hooks/vault-lint.mjs` (hard rules deny the write; soft rules warn). MCP paths omit the leading `vault/`
(MCP `kb/x.md` == native `vault/kb/x.md`).

## 1. Layout and ownership
| Path | Contains | Who writes | Loaded by default | In default search |
|---|---|---|---|---|
| `INDEX.md` | root MOC (`type: index`), ≤150 lines, one line per entry | `/vault-save`, `/vault-session`, curator, researcher (Sources line) | yes (SessionStart) | no (root file) |
| `kb/` | atomic knowledge (`type: kb`); `kb/decisions/` ADRs (`type: decision`); `kb/moc-*.md` hubs (`type: moc`) | `/vault-save`, curator, workflows | no | **yes** (`pathPrefix:"kb"`) |
| `docs/` | Diátaxis docs (`type: doc`) | `/vault-save`, curator | no | yes (`pathPrefix:"docs"`) |
| `sources/` | provenance notes (`type: source`) | vault-researcher, `/vault-save source` | no | research tasks only |
| `plans/` | plan-mode files (`type: plan`); frontmatter stamped by the Stop hook | plan mode; `/vault-session` updates status | no | **never** |
| `sessions/` | session notes (`type: session`) | Stop/PostCompact/SessionEnd hook (generated parts); `/vault-session` (curated parts) | pointer only | **never** |
| `archive/` | retired notes, same basename, flat under `archive/kb|docs|sources/` | curator; `/vault-save` on SUPERSEDE | no | only with `--history` |
| `_templates/`, `_bases/`, `.obsidian/`, `.trash/` | templates, dashboards, app config, local trash | humans / tools | no | never |

Hard rules (the lint hook denies): a `.md` at the vault root other than `INDEX.md`/`README.md`; a top-level folder outside this
list; more than 2 folder levels (`kb/decisions/x.md` and `archive/kb/x.md` are the maximum); non-kebab filenames; duplicate
basenames anywhere in the vault; a full write into `kb|docs|sources` without frontmatter or with an invalid `type`.
Default search exclusions: `excludePaths:["archive","sessions","plans","_templates","_bases"]` unless the task is history/continuation.

## 2. Naming
- Filenames: kebab-case `[a-z0-9-]`, `.md`, ≤60 chars, containing the key nouns (filename matches count in search; `t` = basename).
- **Basenames are unique across the whole vault** (`wiki_link` resolves `[[basename]]` by basename; duplicates resolve shallowest-first).
- kb: `kb/<claim-or-topic>.md` (e.g. `migrations-run-before-seeds.md`); the title is a declarative claim.
- decisions: `kb/decisions/adr-NNNN-<slug>.md` (4 digits; next = highest existing + 1, via `Glob vault/kb/decisions/adr-*.md`).
- docs: `docs/{howto,reference,explanation,tutorial}-<slug>.md` · sources: `sources/src-<domain-or-publisher>-<topic>.md`.
- mocs: `kb/moc-<area>.md` · sessions: `sessions/YYYY-MM-DD--<slug>.md` (hook-generated; never rename) · plans: name given by Claude Code (never rename).
- Moving/renaming does NOT update links (mcpvault has no link index): first `Grep "\[\[<basename>" vault/`, patch each referrer
  (`patch_note`), then `move_note`. Prefer stable names; rename rarely.

## 3. Frontmatter
Flat YAML only (no nested objects), LF line endings, `---` on line 1, dates `YYYY-MM-DD` unquoted (local calendar dates), wiki links
inside YAML **quoted** (`related: ["[[note-a]]"]`), `tags` a YAML list of lowercase kebab-case without `#`. Keys marked **required**
below are enforced by the lint hook (`ERR`); everything else is optional.

Common (every note in `kb/ docs/ sources/ archive/`, plus INDEX/moc):
| Field | Required | Values |
|---|---|---|
| `type` | yes | `kb` `decision` `moc` `doc` `source` `plan` `session` `index` |
| `title` | yes | string; kb: a declarative claim ("Migrations must run before seed scripts") |
| `description` | yes | ≤160 chars, one line, no markdown — the line INDEX/MOCs/briefings show |
| `status` | yes | per type below |
| `created`, `updated` | yes | dates; `updated` bumps on every meaningful edit (mtime is unreliable) |
| `tags` | yes | list, ≥1; reuse the `list_all_tags` vocabulary before inventing a tag |
| `related` | no | list of quoted `"[[basename]]"`; each gets a why-clause in `## Relations` |
| `aliases` | no | list of synonyms (searchable with `searchFrontmatter:true`) |

Per type:
- **kb** (required: `kind`, `importance`, `confidence`, `review_after`): `kind: fact|convention|gotcha|pattern|concept` · `status: draft|active|needs-review|superseded|archived` ·
  `importance: 1-5` (5 = forgetting it causes a wrong architectural choice) · `confidence: verified|likely|unverified`
  (verified = checked against code/source by the writer; likely = from a reliable source, not re-checked; unverified = assertion) ·
  `evidence: [...]` strings (`src/x.ts#symbol`, `cmd: npm test`, `"[[src-…]]"`, `"[[adr-…]]"`, `"[[2026-08-17--slug]]"`) ·
  `sources: ["[[src-…]]"]` · `reviewed` · `review_after` · `supersedes: ["[[…]]"]` · `superseded_by: "[[…]]"` (required when
  `status: superseded`) · `review_note` (why flagged).
- **decision** (MADR; required: `decided`, `review_after`): `status: proposed|accepted|rejected|deprecated|superseded` · `decided` (date) · `deciders: [user, agent]` ·
  `plan: "[[plan-basename]]"` · `supersedes` / `superseded_by` · `reviewed` · `review_after`. Never edited after `accepted`
  except `status`/`superseded_by`; write a new ADR instead.
- **doc** (required: `kind`, `review_after`): `kind: tutorial|howto|reference|explanation` · `audience: agent|human|both` · `status: draft|active|needs-review|outdated|archived` ·
  `verifies: ["cmd: …", "path: …"]` (re-checked at review) · `reviewed` · `review_after`.
- **source** (required: `url`, `retrieved`, `reliability`): `url` · `retrieved` (date) · `published` (date or `unknown`) · `author` · `publisher` ·
  `reliability: primary|official-docs|peer-reviewed|secondary|community|unknown` · `archived_url` (optional) ·
  `status: active|stale|dead-link|archived` · `used_by: ["[[kb-note]]"]`.
- **plan** (stamped by the Stop hook, updated by `/vault-session`): `session_id` · `slug` ·
  `status: draft|approved|in-progress|done|abandoned|superseded` · `outcome` · `produced: ["[[…]]"]`.
- **session** — hook-owned keys (never hand-edit; `status` becomes `closed` at SessionEnd): `session_id, slug, date, started, updated,
  ended, status: open|closed, model, cwd, git_branch, prompts, tools_used, files_touched, plans, tokens_in, tokens_out, tokens_cache_read`;
  curated keys: `description`, `outcome: success|partial|blocked`, `tags`, `related`, `promoted: true|false`.
- **moc**: `area` · `status: active|archived`. **index**: `status: active`.

Enum values are non-substrings of each other, so `search_notes {query:"status: superseded", searchFrontmatter:true, searchContent:false}`
is a reliable pseudo-query. Review cadence (`review_after = reviewed + N days`, or `created + N` when not yet reviewed): gotcha 60 ·
fact 90 · doc 90 · pattern 120 · convention/concept/decision 180 · importance 5 → cap at 60.

## 4. Body shapes (templates: `vault/_templates/template-<type>.md` — Read the one you need)
- kb (≤120 lines, target ≤80): `# Title` → `## Statement` (2–6 sentences: the claim, why it matters, when it applies/doesn't) →
  `## Evidence` (bullets mirroring `evidence`, each saying how to re-verify) → `## Relations` (`- relates_to [[x]] — why`,
  `- part_of [[moc-y]]`, `- supersedes [[z]]`, `- contradicts [[w]] — resolved how`) → `## Review log`
  (`- YYYY-MM-DD verified by <agent|user> — how`). One claim per note; if you cannot state it in one sentence it is two notes.
- decision: Context and Problem Statement / Decision Drivers / Considered Options / Decision Outcome (+ Consequences, Confirmation) / Relations.
- doc: one purpose per doc; a heading at least every ~40 lines (agents read via `get_note_outline` + `read_note_lines`);
  commands verbatim; say what is out of scope.
- source: `## Summary` (≤5 lines) → `## Key claims` (`- [verified|likely|unverified] claim — location`) → `## Extracted to`
  (filled by the curator) → `## Excerpts` (verbatim `>` quotes with heading/section/page; **immutable after capture — append, never edit**).
- session: generated block between `<!-- generated:start -->` and `<!-- generated:end -->` (never edit) + curated `## Summary`,
  `## Decisions`, `## Knowledge written`, `## Open questions`, `## Next step`, `## Checkpoints` (hook-appended).
- Links: `[[basename]]` for vault notes (add `— why` on the same line); `[text](url)` for the web; `[[basename#Heading]]` allowed
  (mcpvault ignores the fragment). Every kb note has ≥1 outgoing link and ≥1 inbound link (a MOC/INDEX line counts); an unlinked note is a bug.
- No inline `#hashtags` anywhere in bodies (mcpvault `manage_tags add/remove` would promote every `#token` into YAML tags).
- Prose ≠ evidence: `confidence: verified` requires at least one `evidence` entry.

## 5. WHEN to persist and WHAT qualifies
Persist when ALL hold: durable ≥1 month · not rediscoverable in <1 min from code · specific to this project or its decisions ·
actionable or explanatory.
| Trigger | Where |
|---|---|
| A decision among alternatives (library, schema, convention, "we will not do X") | `kb/decisions/adr-NNNN-*.md` |
| Non-obvious repo fact that would cost >5 min to rediscover (build quirk, env var, hidden coupling, flaky-test cause) | `kb/` kind `fact` / `gotcha` |
| The user corrected the agent, or the same clarification was given twice | `kb/` kind `convention` (+ one AGENTS.md line only if it must apply every session) |
| A repeatable procedure (≥3 steps, done ≥2 times) | `docs/howto-*` (+ optionally a skill) |
| External material consulted and it influenced code or a decision | `sources/src-*` + a link from the kb/decision note |
| Something in the vault found wrong while working | fix now, or `status: needs-review` + `review_note` — never leave it silently wrong |
| End of session / before `/compact` / before `/clear` / after a major sub-task | `/vault-session` (curated sections, promotions, plan status, INDEX) |

Do NOT persist: transient state ("tests currently failing"), raw tool output, secrets/credentials, personal preferences
(user-global → `~/.claude/`), other projects' knowledge, file listings/dependency lists (derivable), speculation
(unless `status: draft` + `confidence: unverified`).
Salience filter before ADD: assign `importance` 1–5; search for near-duplicates; then choose **ADD / UPDATE** (same claim, more
detail) **/ SUPERSEDE** (claim changed) **/ NOOP**.

## 6. HOW to write (tool level)
- Create: `mcp__obsidian__write_note {path:"kb/<name>.md", frontmatter:{…}, content:"# Title\n…"}` (creates directories).
  Pass frontmatter ONCE (as the argument, not also in `content`). Never `mode:"overwrite"` without `frontmatter` (it wipes YAML).
  `append` inserts no newline — start appended text with `\n`.
- Update metadata: `mcp__obsidian__update_frontmatter {path, frontmatter:{updated:"…", …}, merge:true}` — arrays are replaced
  wholesale (read with `get_frontmatter`, send the full list); keys cannot be deleted with `merge:true` (use tombstone values).
- Edit body: `mcp__obsidian__patch_note {path, oldString, newString}` (exact, unique match; sees the YAML too) or native `Edit`.
- Tags: only via `update_frontmatter`; `manage_tags` only with `operation:"list"` (add/remove is denied by the lint hook).
- Move/archive: `mcp__obsidian__move_note {oldPath, newPath}` keeps the basename; patch referrers first (§2).
- Delete: only true duplicates/mistakes, only after the user confirms: `delete_note {path, confirmPath, trashMode:"local"}`
  (→ `vault/.trash/`, hidden from all tools; other trash modes are denied and every delete prompts the user) + one line in the session note.
- Always: bump `updated`; set `reviewed` + `review_after` when you verified the claim; search before create; then link the note
  into a MOC or INDEX (importance ≥4 → INDEX "Key notes"; decisions → INDEX "Recent decisions", keep 5; keep INDEX ≤150 lines).
- Do not write into `vault/` anything that is not this project's own work.

## 7. HOW agents find notes and judge relevance
1. **Frame** (no tools): 3–6 key terms (identifiers, file/module names, error strings, domain nouns) + 1–2 synonyms each.
   Horizon: current truth (default) or history (include archive/superseded).
2. **Index first**: INDEX (already in context for the main agent; the librarian must `read_note {path:"INDEX.md"}`) → the matching
   `kb/moc-*` note. Cheap enumeration: `Grep '^description:' vault/kb` lists every note's one-liner in one call.
3. **Recall**: `search_notes {query, pathPrefix:"kb", excludePaths:[defaults], limit:15}` for 2–4 lexical variants (substring-OR,
   no stemming, filename hits count); one pass `{searchFrontmatter:true, searchContent:false}` for tags/aliases/status; repeat with
   `pathPrefix:"docs"`, and `"sources"` for research tasks; one native `Grep` over `vault/` for exact symbols/error strings. Union by path.
4. **Triage cheaply**: `get_frontmatter` (or `read_multiple_notes {includeContent:false}`) on the top ≤10 → status, description,
   importance, confidence, updated, tags, review_after. Drop `superseded|archived|deprecated|rejected` unless history;
   deprioritise `needs-review` / `draft` / `unverified`.
5. **Score** 0–1: `0.5·R + 0.2·I + 0.15·C + 0.15·F` — R = 0.5·(BM25 rank: 1st = 1.0, −0.1 per rank) + 0.5·(term overlap in
   title/description/tags: 0 / .33 / .66 / 1); I = importance/5 (docs/sources 0.6); C = 1.0 if `reviewed|updated` <30 d, .6 <180 d,
   .3 <365 d, else .1; F = verified 1.0 / likely .7 / unverified .3 (sources: primary|official-docs 1, secondary .6, community .4).
   Ties → newer `updated`, then shorter note. Keep the top 3–5 (max 8). Prefer 3 strong notes over 8 weak ones — distractors hurt.
6. **Budget**: read the top 3–5 only (≤ ~4k tokens into the main context); large notes via `get_note_outline` → `read_note_lines`
   (`search_notes.ln` is body-relative — never feed it to `read_note_lines`). Never read sessions/plans unless the task is
   "continue previous work" (then: the last session note's curated sections + the active plan only).
7. **Expand one hop**: `related`/`evidence` links via `wiki_link`; backlinks via `Grep "\[\[<basename>" vault/`. Stop at one hop.
8. **Verify before relying**: for kb facts with code evidence, grep the cited path/symbol; if it is gone → do not act on it;
   report "STALE?" (librarian) or set `status: needs-review` + `review_note` (writer).
9. **Briefing** (≤40 lines / ≤1,500 tokens): path · type/kind · importance · confidence · updated · one-line takeaway · caveats;
   related-not-read; contradictions/staleness; gaps; ≤3 suggested reads (`path#Heading`, line range). Only the briefing enters
   the caller's context — never raw note bodies.

## 8. Review, revision, supersession, archive (lifecycle)
Cadence: `review_after` per §3; the SessionStart briefing reports the due count; `/vault-audit` (workflow) sweeps and proposes;
`/vault-review` (curator) verifies and applies safe actions; the librarian flags at read time.
| Condition | Action | Who |
|---|---|---|
| Still true, evidence verifies | bump `reviewed`, recompute `review_after`, add a Review-log line | curator / audit |
| True but incomplete/imprecise | REVISE in place, bump `updated`, keep the title if the claim is unchanged | anyone via `/vault-save` |
| Two+ notes make the same claim | MERGE into the better-titled note; other → `status: superseded`, `superseded_by`, move to `archive/<top>/` | curator |
| Contradicted by code/decision (was true once) | SUPERSEDE: new note (`supersedes`), old → `superseded` + `superseded_by`, patch referrers, move to `archive/<top>/` (ADRs too: new ADR, old → `archive/kb/`) | anyone via `/vault-save`; curator for sweeps |
| Doc references a removed feature/command | `status: outdated` → rewrite, or archive with a pointer to the replacement | curator |
| Source URL dead / content changed | `status: dead-link|stale`; re-verify dependent claims (`used_by`) | researcher / curator |
| Never true (misread) or exact duplicate | propose DELETE; only after user confirmation `delete_note {trashMode:"local"}`; fix derived notes; log in the session note | curator + user |
| Uncertain | `status: needs-review` + `review_note`; report to the user | anyone |
| Plan finished / dropped | `status: done|abandoned`, `outcome`, `produced`; INDEX lists only unfinished plans | `/vault-session` |
| An area exceeds ~8 kb notes | create `kb/moc-<area>.md`; INDEX links the MOC instead of the notes | `/vault-save` |
| INDEX >150 lines / kb note >120 lines | move detail into MOCs / split the note | curator |
Never delete: ADRs, sources with provenance, anything with backlinks (grep first). Contradiction detection: same-topic notes
(≥2 shared tags) with opposite statements; evidence paths that no longer exist; `superseded` notes still linked from active notes;
INDEX entries pointing at archived notes.

## 9. Anti-pollution
- Always-loaded = AGENTS.md + the SessionStart briefing (INDEX ≤150 lines + pointers, ≤8 KB) + skill/agent descriptions.
  Nothing else is imported; `@` imports of vault notes are forbidden.
- Sessions/plans/archive/sources are never read by default; subagents read, the main context receives briefings; pass paths, not contents.
- Auto-memory stays disabled; nothing user-global goes into `vault/`; nothing project-specific goes into `~/.claude/`.
- After compaction the SessionStart(compact) hook re-injects INDEX + this session's curated sections; skills re-invoke on demand.
- Session notes are redacted by the hook (secret patterns; `<private>…</private>` prompt spans are dropped) — but never paste
  secrets into prompts you want captured.

## 10. mcpvault 0.16.0 quirks (why the rules above exist)
`search_notes`: `.md` only, substring-OR per whitespace term + BM25 rerank, `limit` ≤20, excerpt ±21 chars, `ln` body-relative,
`pathPrefix`/`excludePaths` are directory prefixes, no index (full walk per call). `read_note` returns the body without frontmatter;
`get_frontmatter` = cheap metadata; `get_notes_info` = size + mtime, silently drops missing paths; `read_multiple_notes` ≤10 paths;
`wiki_link` is forward-only (backlinks = Grep); `list_directory` is single-level (`Glob vault/**/*.md` to enumerate); any dot-segment
path is invisible; `.trash/` is hidden; `write_note` mkdir -p; `update_frontmatter` replaces arrays and cannot delete keys;
`manage_tags add/remove` promotes body `#tokens`; `move_note` never rewrites links.
