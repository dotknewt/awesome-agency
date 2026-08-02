#!/usr/bin/env bash
# Stop hook: suggest /revise-instructions when the session touched many files.
# Nudges at most once per session; re-nudges only if file count grows by
# INSTRUCTIONS_NUDGE_DELTA or more since the last nudge.
#
# Configurable env vars:
#   INSTRUCTIONS_NUDGE_THRESHOLD  — min files to trigger first nudge (default 5)
#   INSTRUCTIONS_NUDGE_DELTA      — additional files needed to re-nudge (default 5)
set -euo pipefail

threshold="${INSTRUCTIONS_NUDGE_THRESHOLD:-5}"
delta="${INSTRUCTIONS_NUDGE_DELTA:-5}"

project_dir="${CLAUDE_PROJECT_DIR:-.}"

# Bail out gracefully if we're not inside a git repository.
if ! git -C "$project_dir" rev-parse --git-dir &>/dev/null; then
  printf '{"decision":"approve"}\n'
  exit 0
fi

# Sentinel file per project dir — stores file count at last nudge.
sentinel_dir="/tmp/revise-instructions-nudge"
mkdir -p "$sentinel_dir"
project_hash=$(printf '%s' "$project_dir" | md5sum | cut -c1-8)
sentinel="$sentinel_dir/$project_hash"

# Count files changed: uncommitted + commits in the last 2 hours.
dirty=$(git -C "$project_dir" status --porcelain 2>/dev/null | wc -l | tr -d ' ' || echo 0)
recent=$(git -C "$project_dir" diff --name-only "@{2 hours ago}" HEAD 2>/dev/null | wc -l | tr -d ' ' || echo 0)
total=$((dirty + recent))

if [ "$total" -lt "$threshold" ]; then
  printf '{"decision":"approve"}\n'
  exit 0
fi

# Already nudged this session — only re-nudge if count grew by delta.
if [ -f "$sentinel" ]; then
  last_count=$(cat "$sentinel" 2>/dev/null || echo 0)
  if [ "$total" -lt $((last_count + delta)) ]; then
    printf '{"decision":"approve"}\n'
    exit 0
  fi
fi

printf '%s' "$total" > "$sentinel"
printf '{"decision":"approve","systemMessage":"This session touched ~%s file(s). Consider asking to capture key learnings in AGENTS.md (the revise-instructions skill) before finishing."}\n' "$total"

exit 0
