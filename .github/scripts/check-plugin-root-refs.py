#!/usr/bin/env python3
"""Verify every ${CLAUDE_PLUGIN_ROOT}/... reference resolves inside its install.

Each marketplace entry is installed with its own `source` directory as the
plugin root, so a path that resolves for a bundle can still be broken for the
micro-entry that ships the same skill or agent standalone. This walks every
entry's source (following symlinks, since Claude Code dereferences them at
install time) and checks each referenced path exists.
"""

from __future__ import annotations

import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MANIFEST = os.path.join(REPO_ROOT, ".claude-plugin", "marketplace.json")

SCANNED_SUFFIXES = (".md", ".json", ".sh", ".py", ".yml", ".yaml")
# Changelogs quote historical paths that no longer exist; they are prose, not refs.
SKIPPED_FILENAMES = {"RELEASE-NOTES.md", "CHANGELOG.md"}

REF = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}(/[A-Za-z0-9._/-]+)")


def main() -> int:
    with open(MANIFEST, encoding="utf-8") as fh:
        plugins = json.load(fh)["plugins"]

    failures = []
    for plugin in plugins:
        source = os.path.join(REPO_ROOT, plugin["source"])
        if not os.path.isdir(source):
            failures.append(f"{plugin['name']}: source does not exist: {plugin['source']}")
            continue

        for dirpath, _dirnames, filenames in os.walk(source, followlinks=True):
            for filename in filenames:
                if filename in SKIPPED_FILENAMES or not filename.endswith(SCANNED_SUFFIXES):
                    continue
                path = os.path.join(dirpath, filename)
                with open(path, encoding="utf-8", errors="ignore") as fh:
                    text = fh.read()
                for ref in sorted(set(REF.findall(text))):
                    if not os.path.exists(os.path.join(source, ref.lstrip("/"))):
                        rel = os.path.relpath(path, REPO_ROOT)
                        failures.append(
                            f"{plugin['name']}: {rel} references "
                            f"${{CLAUDE_PLUGIN_ROOT}}{ref}, which is not in {plugin['source']}"
                        )

    for failure in failures:
        print(f"::error::{failure}" if os.environ.get("GITHUB_ACTIONS") else f"error: {failure}")

    if failures:
        print(f"{len(failures)} unresolved ${{CLAUDE_PLUGIN_ROOT}} reference(s)")
        return 1

    print(f"all ${{CLAUDE_PLUGIN_ROOT}} references resolve across {len(plugins)} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
