#!/usr/bin/env bash
# Validate a SKILL.md file's frontmatter.
# Usage: validate-skill-frontmatter.sh <file-path>
# Exits 0 on success, 1 on validation failure.
set -euo pipefail

file="${1:-}"

if [ -z "$file" ]; then
  echo "Usage: validate-skill-frontmatter.sh <file-path>" >&2
  exit 1
fi

if [ ! -f "$file" ]; then
  echo "ERROR: file not found: $file" >&2
  exit 1
fi

errors=0

# Extract frontmatter block (between first pair of ---)
frontmatter=$(awk '/^---$/{c++; if(c==2) exit} c==1{print}' "$file")

if [ -z "$frontmatter" ]; then
  echo "ERROR [$file]: missing YAML frontmatter (no --- delimiters found)" >&2
  exit 1
fi

# Required: name field
name=$(echo "$frontmatter" | grep -E '^name:' | sed 's/^name:[[:space:]]*//' | tr -d '"' || true)
if [ -z "$name" ]; then
  echo "ERROR [$file]: missing required frontmatter field 'name'" >&2
  errors=$((errors + 1))
elif ! echo "$name" | grep -qE '^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$'; then
  echo "ERROR [$file]: 'name' must be kebab-case (got '$name')" >&2
  errors=$((errors + 1))
fi

# Required: description field (may be multi-line with >)
if ! echo "$frontmatter" | grep -qE '^description[: ]'; then
  echo "ERROR [$file]: missing required frontmatter field 'description'" >&2
  errors=$((errors + 1))
fi

# Warn if description is very short (under 20 chars on the same line)
desc_line=$(echo "$frontmatter" | grep -E '^description:' | sed 's/^description:[[:space:]]*//' || true)
if [ -n "$desc_line" ] && [ "${#desc_line}" -lt 20 ] && [ "$desc_line" != ">" ] && [ "$desc_line" != "|" ]; then
  echo "WARN [$file]: description looks very short ('$desc_line')" >&2
fi

# Warn if SKILL.md is over 500 lines (spec guideline)
line_count=$(wc -l < "$file")
if [ "$line_count" -gt 500 ]; then
  echo "WARN [$file]: SKILL.md is $line_count lines (spec recommends under 500; move details to references/)" >&2
fi

if [ "$errors" -gt 0 ]; then
  exit 1
fi

echo "OK: $file (name=$name)"
