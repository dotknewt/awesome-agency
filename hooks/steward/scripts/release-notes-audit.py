#!/usr/bin/env python3
"""Audit RELEASE-NOTES.md coverage for the plugin bundles in a marketplace repo.

Mechanical checks only — this reports whether a bundle whose content changed also
bumped its version and recorded a matching entry. Whether that entry actually
explains *why* the change was made is a judgment call left to the caller
(the marketplace-maintainer agent, or a human).

Bundle ownership is derived from the tree, not a hand-maintained list: a bundle
owns every path reachable from `plugins/<name>/`, following symlinks back into the
repo's shared pools. A bundle containing a `.vendored` marker file is exempt.

Usage:
    release-notes-audit.py [--repo PATH] [--base REF] [--all] [--json]

Exit status is 1 when findings exist, 0 when clean.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

VENDORED_MARKER = ".vendored"
NOTES_FILENAME = "RELEASE-NOTES.md"
MANIFEST_RELPATH = os.path.join(".claude-plugin", "plugin.json")


def git(repo: str, *args: str) -> str | None:
    """Run a read-only git command, returning None if it fails."""
    try:
        out = subprocess.run(
            ["git", "-C", repo, *args],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    return out.stdout


def default_branch(repo: str) -> str:
    remote = git(repo, "remote", "show", "origin") or ""
    for line in remote.splitlines():
        line = line.strip()
        if line.startswith("HEAD branch:"):
            return line.split(":", 1)[1].strip()
    return "main"


def resolve_base(repo: str, base: str | None) -> str | None:
    """Resolve the ref to diff against, preferring an explicit --base."""
    if base:
        return (git(repo, "rev-parse", base) or "").strip() or None
    branch = default_branch(repo)
    for ref in (f"origin/{branch}", branch):
        merge_base = git(repo, "merge-base", "HEAD", ref)
        if merge_base and merge_base.strip():
            return merge_base.strip()
    return None


def discover_bundles(repo: str) -> dict[str, dict]:
    """Map bundle name -> {manifest, version, vendored, owned paths}."""
    bundles: dict[str, dict] = {}
    plugins_dir = os.path.join(repo, "plugins")
    if not os.path.isdir(plugins_dir):
        return bundles

    for name in sorted(os.listdir(plugins_dir)):
        bundle_dir = os.path.join(plugins_dir, name)
        manifest_path = os.path.join(bundle_dir, MANIFEST_RELPATH)
        if not os.path.isfile(manifest_path):
            continue
        try:
            with open(manifest_path, encoding="utf-8") as fh:
                manifest = json.load(fh)
        except (OSError, json.JSONDecodeError):
            manifest = {}

        bundles[name] = {
            "version": manifest.get("version"),
            "vendored": os.path.exists(os.path.join(bundle_dir, VENDORED_MARKER)),
            "owns": owned_paths(repo, bundle_dir),
        }
    return bundles


def owned_paths(repo: str, bundle_dir: str) -> set[str]:
    """Repo-relative paths a bundle ships, with symlinks resolved to their pools."""
    owned = set()
    for dirpath, dirnames, filenames in os.walk(bundle_dir):
        for entry in dirnames + filenames:
            real = os.path.realpath(os.path.join(dirpath, entry))
            rel = os.path.relpath(real, repo)
            if not rel.startswith(".."):
                owned.add(rel)
    return owned


def owning_bundles(path: str, bundles: dict[str, dict]) -> list[str]:
    """Every bundle that ships `path` (a pool artifact can belong to several)."""
    return sorted(
        name
        for name, info in bundles.items()
        if path in info["owns"]
        or any(path.startswith(owned + "/") for owned in info["owns"])
    )


def has_entry(notes: str, version: str) -> bool:
    """True when the notes carry a `## v<version>` heading."""
    return re.search(rf"^##\s+v{re.escape(version)}\b", notes, re.MULTILINE) is not None


def version_at(repo: str, base: str, bundle: str) -> str | None:
    blob = git(repo, "show", f"{base}:plugins/{bundle}/{MANIFEST_RELPATH}")
    if blob is None:
        return None
    try:
        return json.loads(blob).get("version")
    except json.JSONDecodeError:
        return None


def audit(repo: str, base: str | None, check_all: bool) -> list[dict]:
    bundles = discover_bundles(repo)
    findings: list[dict] = []

    if check_all:
        targets = {name: None for name, info in bundles.items() if not info["vendored"]}
    else:
        resolved = resolve_base(repo, base)
        if resolved is None:
            return [{
                "bundle": "-",
                "code": "NO_BASE",
                "message": "cannot resolve a base revision to diff against; "
                           "pass --base or use --all",
            }]
        changed = changed_paths(repo, resolved)
        targets = {}
        for path in changed:
            # Editing the notes themselves must not demand a further bump.
            if os.path.basename(path) == NOTES_FILENAME:
                continue
            for name in owning_bundles(path, bundles):
                if not bundles[name]["vendored"]:
                    targets.setdefault(name, resolved)

    for name in sorted(targets):
        findings.extend(audit_bundle(repo, name, bundles[name], targets[name]))
    return findings


def changed_paths(repo: str, base: str) -> set[str]:
    """Committed changes since base, plus anything dirty in the working tree."""
    paths = set()
    diff = git(repo, "diff", "--name-only", f"{base}...HEAD") or ""
    paths.update(line for line in diff.splitlines() if line)
    status = git(repo, "status", "--porcelain") or ""
    for line in status.splitlines():
        if len(line) > 3:
            paths.add(line[3:].split(" -> ")[-1].strip())
    return paths


def audit_bundle(repo: str, name: str, info: dict, base: str | None) -> list[dict]:
    findings = []
    version = info["version"]
    notes_path = os.path.join(repo, "plugins", name, NOTES_FILENAME)

    if not version:
        findings.append({
            "bundle": name,
            "code": "NO_VERSION",
            "message": f"plugins/{name}/{MANIFEST_RELPATH} has no version field",
        })
        return findings

    if not os.path.isfile(notes_path):
        findings.append({
            "bundle": name,
            "code": "MISSING_NOTES",
            "message": f"plugins/{name}/{NOTES_FILENAME} does not exist",
        })
        return findings

    with open(notes_path, encoding="utf-8") as fh:
        notes = fh.read()

    if base is not None:
        previous = version_at(repo, base, name)
        if previous is not None and previous == version:
            findings.append({
                "bundle": name,
                "code": "NO_BUMP",
                "message": f"bundle content changed but version stayed at {version}",
            })

    if not has_entry(notes, version):
        findings.append({
            "bundle": name,
            "code": "NO_ENTRY",
            "message": f"plugins/{name}/{NOTES_FILENAME} has no '## v{version}' entry",
        })

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=os.getcwd(), help="repository root")
    parser.add_argument("--base", help="revision to diff against")
    parser.add_argument("--all", action="store_true",
                        help="audit every bundle, ignoring the diff")
    parser.add_argument("--json", action="store_true", help="emit findings as JSON")
    args = parser.parse_args()

    repo = os.path.abspath(args.repo)
    findings = audit(repo, args.base, args.all)

    if args.json:
        print(json.dumps(findings, indent=2))
    elif findings:
        prefix = "::error::" if os.environ.get("GITHUB_ACTIONS") else "error: "
        for finding in findings:
            print(f"{prefix}{finding['bundle']}: {finding['message']}")
    else:
        print("release notes are current for every bundle in scope")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
