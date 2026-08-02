#!/usr/bin/env bash
# PreToolUse(Write|Edit): block work-object status flips to in-review/approved
# unless check_preconditions.py passes for the affected work/<id>/ directory.
set -euo pipefail

input=$(cat)
tool_name=$(echo "$input" | jq -r '.tool_name // ""')

case "$tool_name" in
  Write)
    content=$(echo "$input" | jq -r '.tool_input.content // ""')
    old_content=""
    ;;
  Edit)
    content=$(echo "$input" | jq -r '.tool_input.new_string // ""')
    old_content=$(echo "$input" | jq -r '.tool_input.old_string // ""')
    ;;
  *) exit 0 ;;
esac

file_path=$(echo "$input" | jq -r '.tool_input.file_path // ""')
echo "$file_path" | grep -qE '(^|/)work/[^/]+/(spec|review)\.md$' || exit 0

target_status=$(echo "$content" \
  | grep -oE '^status:[[:space:]]*(in-review|approved)' \
  | head -n1 | sed -E 's/^status:[[:space:]]*//') || true
[ -n "$target_status" ] || exit 0

# Edit no-op guard: the replaced text already carried the same status,
# so this edit is not a transition.
if [ "$tool_name" = "Edit" ] && echo "$old_content" | grep -qE "status:[[:space:]]*${target_status}"; then
  exit 0
fi

# Fail open if the checker can't run in this environment.
command -v python3 >/dev/null 2>&1 || exit 0
[ -n "${CLAUDE_PLUGIN_ROOT:-}" ] || exit 0

work_dir=$(dirname "$file_path")
base_name=$(basename "$file_path")

# review.md writes get the in-review gate: the approved check requires
# review.md to exist and cite evidence, but this hook fires before the
# write creates it. The full approved gate fires when spec.md is flipped.
if [ "$base_name" = "spec.md" ] && [ "$target_status" = "approved" ]; then
  transition="approved"
else
  transition="in-review"
fi

if ! output=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/check_preconditions.py" "$work_dir" --transition "$transition" 2>&1); then
  echo "BLOCKED: work-object status '${target_status}' in '${file_path}' denied — checker failed for transition '${transition}':" >&2
  echo "$output" >&2
  exit 2
fi

exit 0
