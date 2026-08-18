#!/usr/bin/env bash
# SessionStart hook (sources: startup | resume | clear | compact | fork).
# Prints a budgeted vault briefing as PLAIN TEXT on stdout — Claude Code adds it to context (exit 0).
# Reads only: vault/INDEX.md (body, ≤150 lines), frontmatter of plans/sessions/kb/docs. Never dumps notes.
# Dates are local calendar dates (same basis as the .mjs hooks). bash 3.2 compatible.
set -u
ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
V="$ROOT/vault"
MAX_CHARS=8000
TODAY="$(date +%F)"
INPUT="$(cat 2>/dev/null || true)"

# field <key> — extract a top-level string field from the hook JSON without jq
field() { printf '%s' "$INPUT" | tr -d '\n' | sed -n "s/.*\"$1\"[[:space:]]*:[[:space:]]*\"\([^\"]*\)\".*/\1/p" | head -n1; }
SRC="$(field source)"; [ -n "$SRC" ] || SRC="startup"
SID="$(field session_id)"

if [ ! -f "$V/INDEX.md" ]; then
  echo "<vault-briefing status=\"missing\">vault/INDEX.md does not exist under $ROOT (launch claude from the repo root, or run /vault-init to scaffold the vault).</vault-briefing>"
  exit 0
fi

# section <file> <"## Heading"> [max] — print up to max lines of that section body
section() { awk -v h="$2" -v max="${3:-12}" 'index($0,h)==1{f=1;next} /^## /{f=0} f&&n<max{print;n++}' "$1"; }
# fmval <file> <key> — first frontmatter scalar value (outer quotes stripped, \" unescaped)
fmval()   { awk -v k="$2" 'NR==1&&/^---$/{fm=1;next} fm&&/^---$/{exit} fm&&index($0,k":")==1{sub("^"k":[ ]*","");gsub(/^"|"$/,"");gsub(/\\"/,"\"");print;exit}' "$1"; }
# fmscan <key> <files…> — one awk pass over many files: prints "<value>\t<file>" for the frontmatter key (value unquoted)
fmscan()  { local k="$1"; shift; [ "$#" -gt 0 ] || return 0; awk -v k="$k" 'FNR==1{fm=0} FNR==1&&/^---$/{fm=1;next} fm&&/^---$/{nextfile} fm&&index($0,k":")==1{v=$0;sub("^"k":[ ]*","",v);gsub(/^"|"$/,"",v);print v"\t"FILENAME;nextfile}' "$@" 2>/dev/null; }
count()   { find "$V/$1" -type f -name '*.md' 2>/dev/null | wc -l | tr -d ' '; }

OUT="$(
  echo "<vault-briefing source=\"$SRC\" date=\"$TODAY\">"
  echo "Project memory = vault/ (MCP server 'obsidian' is rooted at vault/: MCP path 'kb/x.md' == native 'vault/kb/x.md'). Conventions: skill vault-conventions."
  echo "Protocol: INDEX below -> /vault-find \"<task goal + 3-6 key terms>\" before non-trivial work -> read <=5 notes -> /vault-save durable knowledge -> /vault-session before compact/stop. Never bulk-read sessions/, plans/, archive/."
  printf 'Counts:'
  for d in kb docs sources plans sessions archive; do printf ' %s=%s' "$d" "$(count "$d")"; done; echo

  # review queue - frontmatter-scoped, single awk pass per key
  KD="$(find "$V/kb" "$V/docs" -type f -name '*.md' 2>/dev/null)"
  due=0; nr=0
  if [ -n "$KD" ]; then
    # shellcheck disable=SC2086
    due="$(fmscan review_after $KD | awk -F'\t' -v t="$TODAY" '$1!="" && $1<=t {n++} END{print n+0}')"
    # shellcheck disable=SC2086
    nr="$(fmscan status $KD | awk -F'\t' '$1=="needs-review"{n++} END{print n+0}')"
  fi
  echo "Review: $due note(s) past review_after, $nr needs-review -> mention this to the user and suggest /vault-review due (user-run); do not run it unasked."

  # recently updated knowledge (5)
  if [ -n "$KD" ]; then
    # shellcheck disable=SC2086
    rec="$(fmscan updated $KD | sort -r | head -n5 | awk -F'\t' -v v="$V/" '{f=$2; sub(v,"vault/",f); printf "- %s — %s\n", f, $1}')"
    [ -n "$rec" ] && { echo "Recently updated (kb/docs):"; echo "$rec"; }
  fi

  # active plans (frontmatter status), newest first, max 5; unstamped plans listed separately
  PL="$(ls -1t "$V"/plans/*.md 2>/dev/null)"
  if [ -n "$PL" ]; then
    act=""; unst=""
    while IFS= read -r p; do
      [ -n "$p" ] || continue
      if ! head -n1 "$p" | grep -q '^---$'; then unst="$unst\n- vault/plans/$(basename "$p")"; continue; fi
      s="$(fmval "$p" status)"
      if [ "$s" = "draft" ] || [ "$s" = "approved" ] || [ "$s" = "in-progress" ]; then
        t="$(fmval "$p" title)"; act="$act\n- vault/plans/$(basename "$p")${t:+ — $t} ($s)"
      fi
    done <<< "$PL"
    if [ -n "$act" ]; then echo "Active plans (read only if continuing that work):"; printf '%b\n' "$act" | sed '/^$/d' | head -n5; fi
    if [ -n "$unst" ]; then echo "Plans without frontmatter yet (stamped by the Stop hook after plan mode ends; /vault-session can stamp them):"; printf '%b\n' "$unst" | sed '/^$/d' | head -n5; fi
  fi

  # current session note (compact/resume only) - quote-tolerant session_id match
  cur=""
  [ -n "$SID" ] && cur="$(grep -l -E "^session_id: *\"?${SID}\"?[[:space:]]*$" "$V"/sessions/*.md 2>/dev/null | head -n1)"
  if [ -n "$cur" ] && { [ "$SRC" = "compact" ] || [ "$SRC" = "resume" ]; }; then
    echo "Current session note: vault/sessions/$(basename "$cur") — curated state follows (everything else on demand):"
    for h in "## Summary" "## Decisions" "## Open questions" "## Next step"; do
      s="$(section "$cur" "$h" 8)"; [ -n "$s" ] && { echo "$h"; echo "$s"; }
    done
    lc="$(section "$cur" "## Checkpoints" 400 | grep '^- ' | tail -n1)"; [ -n "$lc" ] && echo "Last checkpoint: $lc"
  fi

  # last *other* session note (type: session, not this session, not review reports)
  last=""
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    [ "$(fmval "$f" type)" = "session" ] || continue
    sidf="$(fmval "$f" session_id)"
    [ -n "$SID" ] && [ "$sidf" = "$SID" ] && continue
    [ "$sidf" = "review" ] && continue
    if printf '%s' "$(basename "$f")" | grep -q -- '--review-'; then continue; fi
    last="$f"; break
  done <<< "$(ls -1r "$V"/sessions/*.md 2>/dev/null)"
  if [ -n "$last" ]; then
    echo "Last session: vault/sessions/$(basename "$last") — $(fmval "$last" title)"
    s="$(section "$last" "## Next step" 4)"; [ -n "$s" ] && { echo "  Next step:"; printf '%s\n' "$s" | sed 's/^/  /'; }
  fi

  if [ -f "$V/INDEX.md" ]; then
    body="$(awk 'NR==1&&/^---$/{fm=1;next} fm==1&&/^---$/{fm=2;next} fm!=1' "$V/INDEX.md")"
    n="$(printf '%s\n' "$body" | wc -l | tr -d ' ')"
    echo "--- vault/INDEX.md ---"
    printf '%s\n' "$body" | head -n 150
    [ "$n" -gt 150 ] && echo "(INDEX truncated: $n lines, showing 150 — read vault/INDEX.md for the rest and trim it to <=150 lines)"
  fi
)"
if [ "${#OUT}" -gt "$MAX_CHARS" ]; then
  printf '%s\n[... briefing truncated at %s chars — read vault/INDEX.md for the rest]\n' "${OUT:0:$MAX_CHARS}" "$MAX_CHARS"
else
  printf '%s\n' "$OUT"
fi
echo "</vault-briefing>"
exit 0
