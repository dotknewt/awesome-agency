#!/usr/bin/env python3
"""Verify every agent declares a model explicitly.

Claude Code treats `model` as optional and silently defaults to `inherit`. That
makes a deliberate `inherit` indistinguishable from someone forgetting the field,
so this repo requires it on every agent (see docs/specs/agents/Agent-Specification.md
"Model conventions"). Vendored bundles are exempt — they follow upstream's rules.

This checks presence only, never the value. Which tier or pinned ID is right is a
judgment call the spec describes but no script can make, and an allowlist of model
names would reject models newer than the last time someone edited this file.

Usage:
  check-agent-models.py           validate (exit 1 on any violation)
  check-agent-models.py --list    print current assignments, no validation
"""

from __future__ import annotations

import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Real agent sources. plugins/*/agents/ are symlinks into agents/, so scanning them
# would double-report the same file.
#
# `agents/` is dir-per-agent: the agent is `<name>/<name>.md` and any other .md in
# that dir is supporting documentation (README, release notes), not an agent.
# `.claude/agents/` is flat, so every .md there is an agent.
SCAN_DIRS = ("agents", ".claude/agents")
DIR_PER_AGENT_ROOTS = ("agents",)

MODEL_LINE = re.compile(r"^model:\s*(.*?)\s*$")


def agent_files() -> list[str]:
    found = []
    for rel in SCAN_DIRS:
        root = os.path.join(REPO_ROOT, rel)
        if not os.path.isdir(root):
            continue
        dir_per_agent = rel in DIR_PER_AGENT_ROOTS
        for dirpath, dirnames, filenames in os.walk(root):
            # A bundle vendored from upstream keeps upstream's conventions.
            if ".vendored" in filenames:
                dirnames[:] = []
                continue
            for name in sorted(filenames):
                if not name.endswith(".md"):
                    continue
                if dir_per_agent and name != f"{os.path.basename(dirpath)}.md":
                    continue
                found.append(os.path.join(dirpath, name))
    return sorted(found)


def read_model(path: str) -> str | None:
    """Return the raw `model` value, or None if the field is absent.

    Reads only the frontmatter block so a `model:` mentioned in body prose (this
    repo's agents discuss model choice) cannot be mistaken for a declaration.
    """
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = MODEL_LINE.match(line)
        if match:
            return match.group(1).strip().strip("\"'")
    return None


def main() -> int:
    files = agent_files()
    if not files:
        print("no agent files found — check SCAN_DIRS", file=sys.stderr)
        return 1

    if "--list" in sys.argv:
        width = max(len(os.path.relpath(f, REPO_ROOT)) for f in files)
        for path in files:
            rel = os.path.relpath(path, REPO_ROOT)
            print(f"{rel.ljust(width)}  {read_model(path) or '<missing>'}")
        return 0

    errors = []
    for path in files:
        rel = os.path.relpath(path, REPO_ROOT)
        model = read_model(path)
        if model is None:
            errors.append(
                f"{rel}: no `model` in frontmatter. This repo requires an explicit "
                f"choice — `inherit` is fine, but say so."
            )
        elif not model:
            errors.append(f"{rel}: `model` is present but empty")

    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if errors:
        print(
            f"\n{len(errors)} agent(s) violate the model convention; see "
            f"docs/specs/agents/Agent-Specification.md",
            file=sys.stderr,
        )
        return 1

    print(f"ok: {len(files)} agents declare a model")
    return 0


if __name__ == "__main__":
    sys.exit(main())
