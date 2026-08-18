---
name: vault-review
description: Review vault knowledge for staleness, contradictions and duplicates; verify evidence against code/sources; revise, supersede or archive safely and propose deletions. Use when the SessionStart briefing reports notes past review_after, when a note looks wrong while working, or on request. Runs in the vault-curator subagent; for more than 40 candidates use the /vault-audit workflow.
argument-hint: "[due|all|duplicates|contradictions|<vault-relative prefix e.g. kb/decisions>] [--apply]"
context: fork
agent: vault-curator
background: false
disable-model-invocation: true
user-invocable: true
---
Review request. Scope and flags: $ARGUMENTS
(default scope `due`; `--apply` performs SAFE actions, otherwise report proposals only.)

You have no conversation history: everything you need is above and in the vault. Follow your review procedure:
1. `Bash: node .claude/hooks/vault-lint.mjs --all --json` → structural issues, `summary.due`, `summary.needsReview`, `summary.duplicates`.
2. Select candidates by scope: `due` = past `review_after` OR `status: needs-review` OR lint ERR · `all` = every kb + docs note ·
   `duplicates` = same basename, or ≥3 shared tags with overlapping titles (confirm by reading descriptions) · `contradictions` =
   kb notes sharing ≥2 tags whose statements disagree · `<prefix>` = that folder. Cap at 40; beyond that stop after listing them
   and recommend `/vault-audit` with args `{scope, apply}`.
3. Verify each candidate: read it (outline + line ranges for large notes); re-check every `evidence` / `verifies` item (Grep the code
   path/symbol, run cheap read-only commands, open cited `[[src-…]]` notes); search 2–3 variants (`pathPrefix:"kb"|"docs"`, default
   excludes) for near-duplicates/contradictions.
4. Decide with the lifecycle table (skill vault-conventions §8): keep | revise | supersede | merge | archive | delete (propose) | needs-human.
5. Apply only when `--apply` and only safe actions: keep → bump `reviewed`/`review_after` + Review-log line; revise → edit + bump
   `updated`; supersede/merge/archive → write the replacement, set `status`/`superseded_by`, patch inbound `[[links]]` first
   (`Grep "\[\[<basename>" vault/` → `patch_note`), `move_note` to `archive/<top>/<same-basename>.md`, update MOC/INDEX lines.
6. Write the report to `vault/sessions/YYYY-MM-DD--review-<scope-slug>.md` (scope with `/` and other non `[a-z0-9-]` chars replaced by `-`, e.g. `review-kb-decisions`) (frontmatter `type: session, session_id: "review", title,
   description, status: closed, date, created, updated, tags: [session, review]`, sections `## Applied` / `## Proposed (needs
   confirmation)` with the exact tool calls / `## Verified OK` / `## Skipped`) and return the same report (≤60 lines).
Never delete anything; never touch files outside `vault/`; never rewrite generated session blocks or plan bodies.
