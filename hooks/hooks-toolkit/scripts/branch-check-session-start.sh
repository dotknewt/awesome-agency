#!/usr/bin/env bash
# SessionStart: warn if the current branch's PR has already merged.
set -euo pipefail

branch=$(git -C "${CLAUDE_PROJECT_DIR:-.}" branch --show-current 2>/dev/null || true)

[ -n "$branch" ] || exit 0
[ "$branch" != "main" ] && [ "$branch" != "master" ] || exit 0

# Check if gh is available and the branch has a merged PR
if ! command -v gh &>/dev/null; then
  exit 0
fi

merged=$(gh pr list --state merged --head "$branch" --json number,title --jq 'length' 2>/dev/null || echo 0)

if [ "${merged:-0}" -gt 0 ]; then
  pr_info=$(gh pr list --state merged --head "$branch" --json number,title --jq '.[0] | "#\(.number) \(.title)"' 2>/dev/null || true)
  echo "⚠️  Branch '$branch' has a merged PR ($pr_info). Do not add new commits here — branch from a freshly-pulled main instead." >&2
fi

exit 0
