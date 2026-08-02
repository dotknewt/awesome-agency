#!/usr/bin/env bash
# Stop: nudge if the working tree has uncommitted changes.
set -euo pipefail

dirty=$(git -C "${CLAUDE_PROJECT_DIR:-.}" status --porcelain 2>/dev/null | wc -l | tr -d ' ')

if [ "${dirty:-0}" -gt 0 ]; then
  printf '{"decision":"approve","systemMessage":"Working tree has %s modified/untracked file(s). If this work is complete, commit and push before finishing."}\n' "$dirty"
else
  printf '{"decision":"approve"}\n'
fi

exit 0
