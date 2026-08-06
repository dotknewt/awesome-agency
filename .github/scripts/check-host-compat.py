#!/usr/bin/env python3
"""Verify every marketplace entry installs and behaves sensibly in both hosts.

This repo ships a Claude Code marketplace that GitHub Copilot CLI also installs
from. The two hosts read the *same* files but honor different subsets of them, and
Copilot's divergences are silent — a wrong `model:` value is a log line the user
never sees, not an install failure. This check makes those divergences visible at
review time instead.

`.github/host-compat.json` is the source of truth for what each host supports.
Everything here is derived from it; add a capability there, not in this script.

Severity comes from the matrix and follows one rule: a bundle that is *broken* in a
host fails; a bundle that is merely *degraded* reports. `known_exceptions` in the
matrix waives a capability for a named artifact.

Entries are walked per marketplace `source`, not per pool directory, so a skill that
is fine inside its bundle but broken as a standalone micro-install is still caught.

Usage:
  check-host-compat.py           validate (exit 1 on any error-severity finding)
  check-host-compat.py --list    print the portability posture, never fails
  check-host-compat.py --strict  treat warnings as errors too
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MANIFEST = os.path.join(REPO_ROOT, ".claude-plugin", "marketplace.json")
MATRIX = os.path.join(REPO_ROOT, ".github", "host-compat.json")

# A vendored bundle follows upstream's authoring conventions, not ours — so prose and
# frontmatter rules are waived for it. Host-installability facts (hook events, bundled MCP,
# ${CLAUDE_PLUGIN_ROOT}) are NOT waived: upstream's conventions have no bearing on whether
# code actually runs in a user's Copilot session, and vendored bundles ship as real
# marketplace entries.
VENDOR_MARKER = ".vendored"
AUTHORING_CAPABILITIES = {
    "agent-model-alias",
    "agent-color",
    "skill-disable-model-invocation",
    "commands",
}
# Changelogs quote historical config that no longer applies; they are prose.
SKIPPED_FILENAMES = {"RELEASE-NOTES.md", "CHANGELOG.md"}

FRONTMATTER = re.compile(r"\A---\n(.*?)\n---", re.DOTALL)
PLUGIN_ROOT_REF = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}")

# A `model:` value Copilot drops is only a *problem* when the artifact advertises a
# benefit that depends on it. "Runs on Haiku so the main session does not burn tokens"
# is a promise this repo cannot keep in Copilot; a bare `model: haiku` is not.
MODEL_CLAIM = re.compile(
    r"runs on (haiku|sonnet|opus|fable|a \w+ model)"
    r"|(cheap|cheaper|small|fast|lightweight|inexpensive)\s+model"
    r"|burn(ing)? (tokens|context)"
    r"|to (keep|save) (cost|costs|tokens)"
    r"|so the main session",
    re.IGNORECASE,
)

# A skill marked explicit-invocation-only is safe in Copilot only if its body also
# tells the model when not to run — the frontmatter field alone is dropped.
INVOCATION_GUARD = re.compile(
    r"explicit(ly)?[- ]invok|only when (the user|explicitly|asked)"
    r"|do not (run|use|invoke) (this )?(skill )?unless"
    r"|never (run|invoke) (this )?(skill )?automatically"
    r"|must be (explicitly )?(requested|invoked|asked for)"
    r"|invoke(d)? (only )?by name",
    re.IGNORECASE,
)


class Finding:
    def __init__(self, entry: str, capability: str, severity: str, detail: str):
        self.entry = entry
        self.capability = capability
        self.severity = severity
        self.detail = detail

    def __str__(self) -> str:
        return f"[{self.severity}] {self.entry}: {self.capability}: {self.detail}"


def frontmatter_field(text: str, field: str) -> str | None:
    """Return a top-level frontmatter scalar, ignoring commented-out lines."""
    match = FRONTMATTER.search(text)
    if not match:
        return None
    pattern = re.compile(rf"^{re.escape(field)}:\s*(.*?)\s*$", re.MULTILINE)
    hit = pattern.search(match.group(1))
    return hit.group(1) if hit else None


def body_of(text: str) -> str:
    """Return everything after the frontmatter block.

    Guards must be checked against the body only: the whole point is that Copilot drops
    frontmatter, so a constraint written as a YAML comment protects nothing.
    """
    match = FRONTMATTER.search(text)
    return text[match.end():] if match else text


def relative(path: str) -> str:
    return os.path.relpath(path, REPO_ROOT)


def walk_source(source: str):
    """Yield (path, text, vendored) for every readable text file under an entry source.

    Follows symlinks because both hosts dereference them when installing. `vendored` marks
    files under a subtree carrying VENDOR_MARKER; os.walk is top-down, so a marker is always
    seen before the files it covers.
    """
    vendored_roots: list[str] = []
    for dirpath, _dirnames, filenames in os.walk(source, followlinks=True):
        if VENDOR_MARKER in filenames:
            vendored_roots.append(dirpath)
        vendored = any(dirpath == root or dirpath.startswith(root + os.sep)
                       for root in vendored_roots)
        for filename in sorted(filenames):
            if filename in SKIPPED_FILENAMES:
                continue
            if not filename.endswith((".md", ".json")):
                continue
            path = os.path.join(dirpath, filename)
            try:
                with open(path, encoding="utf-8", errors="ignore") as fh:
                    yield path, fh.read(), vendored
            except OSError:
                continue


def is_agent_file(path: str, text: str) -> bool:
    return path.endswith(".md") and frontmatter_field(text, "description") is not None \
        and os.sep + "agents" + os.sep in path


def is_skill_file(path: str) -> bool:
    return os.path.basename(path) == "SKILL.md"


def is_command_file(path: str) -> bool:
    return path.endswith(".md") and os.sep + "commands" + os.sep in path


def waived(exceptions: list[dict], path_or_entry: str, capability: str) -> bool:
    for item in exceptions:
        if item.get("capability") != capability:
            continue
        artifact = (item.get("artifact") or "").rstrip("/")
        if not artifact:
            continue
        if path_or_entry == artifact or path_or_entry.startswith(artifact + "/"):
            return True
    return False


def malformed_exceptions(exceptions: list[dict]) -> list[str]:
    """known_exceptions is hand-edited; a typo must be diagnosable, not a traceback."""
    bad = []
    for index, item in enumerate(exceptions):
        if not isinstance(item, dict) or not item.get("artifact") or not item.get("capability"):
            bad.append(f"known_exceptions[{index}] needs both 'artifact' and 'capability': {item!r}")
    return bad


def check_entry(entry: dict, matrix: dict) -> list[Finding]:
    name = entry["name"]
    source = os.path.join(REPO_ROOT, entry["source"])
    severity = {c["id"]: c["severity"] for c in matrix["capabilities"]}
    exceptions = matrix.get("known_exceptions", [])
    shared_events = set(matrix["shared_hook_events"])
    findings: list[Finding] = []

    if not os.path.isdir(source):
        return [Finding(name, "marketplace-install", "error",
                        f"source does not exist: {entry['source']}")]

    entry_rel = entry["source"].removeprefix("./").rstrip("/")
    skill_names: set[str] = set()
    command_names: list[tuple[str, str]] = []

    for path, text, vendored in walk_source(source):
        rel = relative(path)
        prose = not vendored

        if is_skill_file(path):
            skill_names.add(os.path.basename(os.path.dirname(path)))
            value = frontmatter_field(text, "disable-model-invocation")
            if prose and value and value.lower() == "true" \
                    and not INVOCATION_GUARD.search(body_of(text)) \
                    and not waived(exceptions, rel, "skill-disable-model-invocation"):
                findings.append(Finding(
                    name, "skill-disable-model-invocation",
                    severity["skill-disable-model-invocation"],
                    f"{rel} sets disable-model-invocation, which Copilot drops, and the "
                    "body never says when not to run; state the constraint in prose so "
                    "the model self-restricts",
                ))

        elif is_command_file(path):
            if prose:
                command_names.append((os.path.splitext(os.path.basename(path))[0], rel))

        elif is_agent_file(path, text):
            model = frontmatter_field(text, "model")
            if prose and model and MODEL_CLAIM.search(text) \
                    and not waived(exceptions, rel, "agent-model-alias"):
                findings.append(Finding(
                    name, "agent-model-alias", severity["agent-model-alias"],
                    f"{rel} declares model '{model}' and advertises a benefit that "
                    "depends on it, but Copilot ignores the field and uses the session "
                    "model; drop the claim or qualify it as Claude-only",
                ))
            if prose and frontmatter_field(text, "color") \
                    and not waived(exceptions, rel, "agent-color"):
                findings.append(Finding(
                    name, "agent-color", severity["agent-color"],
                    f"{rel} declares color; Copilot ignores it (cosmetic only)",
                ))

        elif os.path.basename(path) == "hooks.json":
            findings.extend(check_hooks(name, path, text, shared_events, severity,
                                        exceptions))

        elif os.path.basename(path) == ".mcp.json" \
                and os.path.dirname(path) == source.rstrip("/") \
                and not waived(exceptions, rel, "bundled-mcp") \
                and not waived(exceptions, entry_rel, "bundled-mcp"):
            findings.append(Finding(
                name, "bundled-mcp", severity["bundled-mcp"],
                f"{rel} is not auto-started by Copilot; document manual setup in the "
                "bundle README or add a known_exceptions entry",
            ))

        if PLUGIN_ROOT_REF.search(text) and os.path.basename(path) == "hooks.json" \
                and not waived(exceptions, rel, "plugin-root-var"):
            findings.append(Finding(
                name, "plugin-root-var", severity["plugin-root-var"],
                f"{rel} uses ${{CLAUDE_PLUGIN_ROOT}} in a hook command; Copilot support "
                "is unverified (see docs/TODO.md)",
            ))

    for command, rel in command_names:
        if command in skill_names or waived(exceptions, rel, "commands"):
            continue
        findings.append(Finding(
            name, "commands", severity["commands"],
            f"{rel} has no skill counterpart; Copilot has no slash-command concept, so "
            "this capability is unreachable there",
        ))

    return findings


def check_hooks(name: str, path: str, text: str, shared_events: set[str],
                severity: dict[str, str], exceptions: list[dict]) -> list[Finding]:
    try:
        events = json.loads(text).get("hooks", {})
    except (json.JSONDecodeError, AttributeError):
        return [Finding(name, "hook-events", "error",
                        f"{relative(path)} is not valid JSON")]
    if not isinstance(events, dict):
        return [Finding(name, "hook-events", "error",
                        f"{relative(path)} 'hooks' is not an object")]
    rel = relative(path)
    if waived(exceptions, rel, "hook-events"):
        return []
    findings = []
    for event in sorted(events):
        if event not in shared_events:
            findings.append(Finding(
                name, "hook-events", severity["hook-events"],
                f"{rel} uses event '{event}', which Copilot does not support",
            ))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true",
                        help="print the portability posture without failing")
    parser.add_argument("--strict", action="store_true",
                        help="treat warnings as errors")
    args = parser.parse_args()

    with open(MATRIX, encoding="utf-8") as fh:
        matrix = json.load(fh)
    with open(MANIFEST, encoding="utf-8") as fh:
        plugins = json.load(fh)["plugins"]

    findings: list[Finding] = []
    for problem in malformed_exceptions(matrix.get("known_exceptions", [])):
        findings.append(Finding("host-compat.json", "known-exceptions", "error", problem))
    for entry in plugins:
        findings.extend(check_entry(entry, matrix))

    if args.list:
        print(f"host-compat matrix v{matrix['version']} ({matrix['updated']})")
        for capability in matrix["capabilities"]:
            states = " ".join(
                f"{host}={support['status']}"
                for host, support in capability["support"].items()
            )
            print(f"  {capability['id']:<32} {capability['severity']:<6} {states}")
        print(f"\n{len(plugins)} marketplace entries, {len(findings)} findings")
        for finding in findings:
            print(f"  {finding}")
        return 0

    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warn"]
    infos = [f for f in findings if f.severity == "info"]

    for finding in errors + warnings + infos:
        stream = sys.stderr if finding.severity == "error" else sys.stdout
        print(finding, file=stream)

    if args.strict:
        errors = errors + warnings

    if errors:
        print(f"\n{len(errors)} host-compatibility error(s)", file=sys.stderr)
        return 1

    print(f"\nhost-compat OK: {len(plugins)} entries, "
          f"{len(warnings)} warning(s), {len(infos)} note(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
