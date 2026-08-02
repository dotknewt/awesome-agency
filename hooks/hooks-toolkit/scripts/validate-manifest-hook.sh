#!/usr/bin/env bash
# PostToolUse(Write|Edit): validate plugin.json or marketplace.json after writing.
set -euo pipefail

input=$(cat)
tool_name=$(echo "$input" | jq -r '.tool_name // ""')

case "$tool_name" in
  Write|Edit) ;;
  *) exit 0 ;;
esac

file_path=$(echo "$input" | jq -r '.tool_input.file_path // ""')

# Only act on plugin.json and marketplace.json
if ! echo "$file_path" | grep -qE '(plugin\.json|marketplace\.json)$'; then
  exit 0
fi

# Run the shared validator
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! "$SCRIPT_DIR/validate-plugin-json.sh" "$file_path" 2>&1; then
  # PostToolUse: stderr goes back to Claude as a system message
  exit 2
fi

exit 0
