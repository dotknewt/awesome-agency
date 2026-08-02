#!/usr/bin/env bash
# PostToolUse(Write|Edit): validate SKILL.md frontmatter after writing.
set -euo pipefail

input=$(cat)
tool_name=$(echo "$input" | jq -r '.tool_name // ""')

case "$tool_name" in
  Write|Edit) ;;
  *) exit 0 ;;
esac

file_path=$(echo "$input" | jq -r '.tool_input.file_path // ""')

if ! echo "$file_path" | grep -qE 'SKILL\.md$'; then
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! "$SCRIPT_DIR/validate-skill-frontmatter.sh" "$file_path" 2>&1; then
  exit 2
fi

exit 0
