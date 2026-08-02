#!/usr/bin/env bash
# UserPromptSubmit: inject branch hygiene rules when the user mentions PRs or branching.
set -euo pipefail

input=$(cat)
prompt=$(echo "$input" | jq -r '.user_prompt // ""')

# Keyword match — case-insensitive
if ! echo "$prompt" | grep -qiE '\b(PR|pull request|branch|push|merge|stacked|squash)\b'; then
  exit 0
fi

cat <<'RULES'
{"systemMessage":"Branch hygiene reminder:\n- Sync main before branching: git checkout main && git pull --ff-only origin main && git checkout -b <branch>\n- One branch per initiative (not per file); multiple related changes belong on one branch.\n- Never add commits to a branch whose PR has already merged.\n- After a PR merges, delete the branch locally and on origin in the same step.\n- Check for open PRs that touch the same files before branching (squash-merge tangle risk).\n- Force-push to main/master is not allowed.\nSee AGENTS.md for full branch lifecycle rules."}
RULES

exit 0
