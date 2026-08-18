---
name: vault-save
description: Persist durable project knowledge into vault/ (kb note, ADR decision, doc, or source) with correct frontmatter, links and INDEX/MOC entries. Use when a decision among alternatives was made, a non-obvious repo fact or gotcha was learned, the user corrected you or repeated a clarification, a repeatable procedure emerged, or an external source shaped a decision. Search-before-create; update > create; supersede > overwrite.
argument-hint: "[kb|decision|doc|source] <one-line claim or title> [--url <url>]"
user-invocable: true
---
# /vault-save — capture procedure (runs in the main context: you know what was learned)

If the `vault-conventions` skill is not in context, invoke it (or Read `${CLAUDE_PLUGIN_ROOT}/skills/vault-conventions/SKILL.md`) first —
§3 frontmatter schema, §5 triggers, §6 tool rules, §8 lifecycle. MCP paths omit `vault/` (MCP `kb/x.md` == native `vault/kb/x.md`).

Arguments: $ARGUMENTS
Type is optional; infer it: **decision** = a choice among alternatives · **doc** = a human procedure/reference/explanation ·
**source** = an external URL/paper/repo · otherwise **kb** (`kind: fact|convention|gotcha|pattern|concept`).

## 1. Qualify (WHAT) — all must hold, otherwise stop and say why
- durable ≥1 month · not rediscoverable in <1 min from code · specific to this project or its decisions · actionable or explanatory
- NOT: transient state, raw tool output, secrets/tokens, personal preferences (→ `~/.claude/`), other projects' knowledge,
  speculation (unless saved as `status: draft` + `confidence: unverified`).

## 2. Search before create (mandatory; 2–4 calls, ≤20 results each)
- `mcp__obsidian__list_all_tags` once → reuse the vocabulary; do not invent near-duplicate tags.
- `mcp__obsidian__search_notes {query:"<key terms>", pathPrefix:"kb", excludePaths:["archive","sessions","plans","reference","_templates","_bases"], limit:10}`
  with 2–3 lexical variants (singular/plural, synonym, expected filename words); `Grep '^description:' vault/kb` for a one-call overview.
- `mcp__obsidian__get_frontmatter` on the top 3 hits → compare claim/description.
Decide: **NOOP** (already captured; at most bump `reviewed`) · **UPDATE** (same claim, add detail: `patch_note` the body, bump `updated`) ·
**SUPERSEDE** (claim changed: write the new note with `supersedes`; set the old note `status: superseded` + `superseded_by` via
`update_frontmatter`; then `Grep "\[\[<old-basename>" vault/` → `patch_note` each referrer → `move_note` old → `archive/<top>/<same-basename>.md`
and update its INDEX/MOC line; ADRs: write a new ADR and archive the old one the same way) · **ADD**.

## 3. Write (HOW / FORMAT)
- Path: kb `kb/<slug>.md` · decision `kb/decisions/adr-NNNN-<slug>.md` (NNNN = highest existing + 1: `Glob vault/kb/decisions/adr-*.md`) ·
  doc `docs/<kind>-<slug>.md` · source: **delegate** to the `vault-researcher` subagent ("ingest <url> as a source note for: <why>")
  and use the returned path — never fetch web pages in the main context.
- Basename must be unique: `mcp__obsidian__wiki_link {document:"<slug>"}` must return "No file found".
- `Read vault/_templates/template-<type>.md` and use its BODY only (replace `{{title}}` and every `<…>` placeholder with real text;
  never copy the template frontmatter — it holds `{{date}}` placeholders); pass frontmatter as the `frontmatter` argument with real dates.
  Then `mcp__obsidian__write_note {path, content:<body>, frontmatter:{…}}` with
  `type, title, description (≤160), status, created=updated=today, tags:[…]` + per-type keys (kb: `kind, importance, confidence,
  evidence, sources, related, reviewed=today if verified, review_after` per cadence — gotcha +60d, fact/doc +90d, pattern +120d,
  convention/concept/decision +180d, importance 5 → +60d). Dates as `YYYY-MM-DD` strings; wiki links inside YAML quoted.
- Body per §4 of the conventions: kb = Statement → Evidence (how to re-verify) → Relations (`- relates_to [[x]] — why`) → Review log.
  One claim per note. No inline `#hashtags`.

## 4. Link both ways, then index
- Patch each related note's `## Relations` list (`mcp__obsidian__patch_note`) so the graph is bidirectional.
- Add one line `- [[basename]] — description` to the matching `kb/moc-<area>.md` (create a MOC when an area exceeds ~8 notes and
  link it from INDEX "Areas"), or to `vault/INDEX.md`: "Key notes" if importance ≥4; decisions → "Recent decisions" (keep 5,
  drop the oldest); docs → "Docs"; sources → "Sources". Replace a section's `- (no … yet)` placeholder when adding its first entry
  (with `patch_note`, include the heading in `oldString` if the line is not unique). Keep INDEX ≤150 lines.

## 5. Record and report
- Append `- [[basename]] (ADD|UPDATE|SUPERSEDE)` under `## Knowledge written` of the current session note
  (`Grep 'session_id: "${CLAUDE_SESSION_ID}"' vault/sessions`; skip if it does not exist yet).
- If the vault-lint hook warns after the write, fix it immediately.
- Reply with: path · action taken · the one-line description. Nothing else.
