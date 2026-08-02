#!/usr/bin/env bash
# PreToolUse(Write|Edit): block writes containing likely secrets.
set -euo pipefail

input=$(cat)
tool_name=$(echo "$input" | jq -r '.tool_name // ""')

case "$tool_name" in
  Write)  content=$(echo "$input" | jq -r '.tool_input.content // ""') ;;
  Edit)   content=$(echo "$input" | jq -r '.tool_input.new_string // ""') ;;
  *)      exit 0 ;;
esac

hit=""

# AWS access key ID
if echo "$content" | grep -qE 'AKIA[0-9A-Z]{16}'; then
  hit="AWS access key ID (AKIA...)"
fi

# GitHub personal access token (classic or fine-grained)
if echo "$content" | grep -qE 'ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82}'; then
  hit="${hit:+$hit, }GitHub PAT"
fi

# PEM private key headers
if echo "$content" | grep -qE -- '-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----'; then
  hit="${hit:+$hit, }PEM private key"
fi

# Slack bot/app token
if echo "$content" | grep -qE 'xox[bpoa]-[0-9A-Za-z-]+'; then
  hit="${hit:+$hit, }Slack token"
fi

if [ -n "$hit" ]; then
  file_path=$(echo "$input" | jq -r '.tool_input.file_path // "(unknown)"')
  echo "BLOCKED: likely secret detected in '$file_path': $hit. Remove before writing." >&2
  exit 2
fi

exit 0
