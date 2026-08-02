#!/usr/bin/env bash
# Validate a plugin.json (or marketplace.json) file.
# Usage: validate-plugin-json.sh <file-path>
# Exits 0 on success, 1 on validation failure.
set -euo pipefail

file="${1:-}"

if [ -z "$file" ]; then
  echo "Usage: validate-plugin-json.sh <file-path>" >&2
  exit 1
fi

if [ ! -f "$file" ]; then
  echo "ERROR: file not found: $file" >&2
  exit 1
fi

errors=0

# 1. Must be valid JSON
if ! jq empty "$file" 2>/dev/null; then
  echo "ERROR [$file]: invalid JSON" >&2
  errors=$((errors + 1))
  exit 1
fi

# Detect marketplace format (has a top-level "plugins" array)
is_marketplace=$(jq -r 'if has("plugins") then "yes" else "no" end' "$file")

# 2. Required fields
if [ "$is_marketplace" = "yes" ]; then
  # Marketplace: needs name and plugins array
  for field in name plugins; do
    value=$(jq -r ".$field // empty" "$file")
    if [ -z "$value" ]; then
      echo "ERROR [$file]: missing required marketplace field '$field'" >&2
      errors=$((errors + 1))
    fi
  done
  # Each plugin entry must have name, source, description
  invalid_entries=$(jq '[.plugins[] | select((.name == null or .name == "") or (.source == null or .source == "") or (.description == null or .description == ""))] | length' "$file")
  if [ "${invalid_entries:-0}" -gt 0 ]; then
    echo "ERROR [$file]: $invalid_entries plugin entries missing name, source, or description" >&2
    errors=$((errors + 1))
  fi
else
  # Plugin manifest: needs name and description
  for field in name description; do
    value=$(jq -r ".$field // empty" "$file")
    if [ -z "$value" ]; then
      echo "ERROR [$file]: missing required field '$field'" >&2
      errors=$((errors + 1))
    fi
  done
fi

# 3. name must be kebab-case
name=$(jq -r '.name // ""' "$file")
if [ -n "$name" ] && ! echo "$name" | grep -qE '^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$'; then
  echo "ERROR [$file]: 'name' must be kebab-case (got '$name')" >&2
  errors=$((errors + 1))
fi

# 4. version, if present, must be semver-ish
version=$(jq -r '.version // ""' "$file")
if [ -n "$version" ] && ! echo "$version" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+'; then
  echo "WARN [$file]: 'version' does not look like semver (got '$version')" >&2
fi

if [ "$errors" -gt 0 ]; then
  exit 1
fi

echo "OK: $file"
