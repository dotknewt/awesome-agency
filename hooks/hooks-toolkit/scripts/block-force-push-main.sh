#!/usr/bin/env bash
# PreToolUse(Bash): block git push --force targeting main or master.
set -euo pipefail

input=$(cat)
tool_name=$(echo "$input" | jq -r '.tool_name // ""')

[ "$tool_name" = "Bash" ] || exit 0

command=$(echo "$input" | jq -r '.tool_input.command // ""')

if echo "$command" | grep -qE 'git\s+push\s+.*(--force|-f\b|--force-with-lease)'; then
  if echo "$command" | grep -qE '\b(main|master)\b'; then
    echo "BLOCKED: force-push to main/master is not allowed. Use --force-with-lease on a non-main branch, or open a PR instead." >&2
    exit 2
  fi
fi

exit 0
