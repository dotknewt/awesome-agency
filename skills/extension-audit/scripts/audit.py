#!/usr/bin/env python3
"""Static audit tooling for Claude Code and Copilot extension artifacts.

This module intentionally uses only the Python standard library.  It never
imports or executes files from the audited path and never fetches repositories.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable


SKILL_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {
    ".git", ".hg", ".svn", ".tox", ".venv", "venv", "node_modules",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "dist",
    "build", "coverage", ".coverage", ".cache", "target", ".terraform",
}
TEXT_EXTENSIONS = {
    ".md", ".markdown", ".json", ".json5", ".yaml", ".yml", ".toml", ".ini",
    ".cfg", ".conf", ".txt", ".py", ".js", ".jsx", ".ts", ".tsx", ".sh",
    ".bash", ".zsh", ".fish", ".ps1", ".bat", ".cmd", ".mjs", ".cjs",
}
SEVERITY_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
PROMPT_PATTERNS = [
    (re.compile(r"\bignore (?:all )?(?:previous|prior|earlier) instructions\b", re.I),
     "prompt-injection phrase: instruction override"),
    (re.compile(r"\b(?:system|developer) message\b.{0,40}\b(?:reveal|ignore|override)\b", re.I),
     "prompt-injection phrase: privileged-message manipulation"),
    (re.compile(r"\bdo not (?:tell|show|mention|disclose)\b.{0,50}\b(?:user|reviewer|human)\b", re.I),
     "prompt-injection phrase: concealment"),
    (re.compile(r"\b(?:exfiltrat|steal|leak|send)\w*\b.{0,60}\b(?:token|secret|credential|environment|file)\b", re.I),
     "prompt-injection/exfiltration language"),
    (re.compile(r"\b(?:jailbreak|bypass|override)\b.{0,50}\b(?:safety|policy|guardrail)\b", re.I),
     "prompt-injection phrase: safety bypass"),
]
SECURITY_PATTERNS = [
    ("critical", re.compile(r"(?:curl|wget|Invoke-WebRequest|requests\.(?:get|post|put)|httpx\.(?:get|post)|urllib\.request|fetch\s*\(|WebClient)", re.I), "outbound network access"),
    ("high", re.compile(r"(?:os\.environ|process\.env|ENV\[|getenv\s*\(|\$\{?[A-Z][A-Z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD|CREDENTIAL)[A-Z0-9_]*\}?)", re.I), "credential/environment access"),
    ("high", re.compile(r"(?:~/.ssh|\.ssh/|\.aws/|\.config/gcloud|id_rsa|\.env\b|/etc/passwd|/etc/shadow)", re.I), "sensitive path access"),
    ("high", re.compile(r"(?:rm\s+-rf|sudo\s+|chmod\s+(?:777|666)|(?:bash|sh|zsh)\s+-c|python(?:3)?\s+-c|node\s+-e|child_process|subprocess\.(?:run|Popen|call)|os\.system|shell\s*=\s*True|eval\s*\(|exec\s*\()", re.I), "dangerous shell/code execution"),
    ("high", re.compile(r"(?:\b(?:Bash|Write|Edit|Read|NotebookEdit)\s*\(\s*\*\s*\)|[\"'](?:permissions|tools|allow)[\"']\s*:\s*\[[^\]]*[\"']\*[\"'])", re.I), "broad tool or permission scope"),
    ("medium", re.compile(r"(?:base64\.(?:b64decode|decode)|atob\s*\(|nc\s+-|netcat|socket\.create_connection|ftp://)", re.I), "obfuscation or alternate network channel"),
]
DEPENDENCY_VERSION = re.compile(r"^(?:[\^~*<>=!]|latest$|git\+|https?://|file:)", re.I)


@dataclass
class Finding:
    severity: str
    category: str
    message: str
    path: str | None = None
    line: int | None = None
    evidence: str | None = None
    remediation: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


def relpath(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def iter_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        yield root
        return
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink() and not path.exists():
            continue
        try:
            relative_parts = path.relative_to(root).parts
        except ValueError:
            continue
        if any(part in EXCLUDED_DIRS for part in relative_parts):
            continue
        yield path


def read_text(path: Path, limit: int = 2_000_000) -> str | None:
    try:
        if path.stat().st_size > limit:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def line_number(text: str, needle: str) -> int | None:
    for number, line in enumerate(text.splitlines(), 1):
        if needle.lower() in line.lower():
            return number
    return None


def parse_frontmatter(text: str) -> tuple[dict[str, str], int]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, 0
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if end is None:
        return {}, 0
    result: dict[str, str] = {}
    current: str | None = None
    block: list[str] = []
    mode: str | None = None
    for raw in lines[1:end]:
        if not raw.strip():
            if mode:
                block.append("")
            continue
        if not raw[0].isspace() and ":" in raw:
            if current and mode:
                result[current] = (" ".join(block) if mode == ">" else "\n".join(block)).strip()
            current, _, value = raw.partition(":")
            current = current.strip()
            value = value.strip()
            if value[:1] in {">", "|"}:
                mode = value[0]
                block = []
            else:
                mode = None
                block = []
                result[current] = value.strip("\"'")
        elif mode:
            block.append(raw.strip())
    if current and mode:
        result[current] = (" ".join(block) if mode == ">" else "\n".join(block)).strip()
    return result, end + 1


def json_load(path: Path) -> Any | None:
    text = read_text(path)
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def classify(path: Path, root: Path) -> tuple[str, dict[str, Any]]:
    name = path.name
    rel = relpath(path, root)
    if name == "SKILL.md":
        kind = "skill"
    elif name == "hooks.json":
        kind = "hook"
    elif name in {"AGENTS.md", "CLAUDE.md"} or name.endswith(".instructions.md"):
        kind = "instruction"
    elif name.endswith(".agent.md") or "/agents/" in f"/{rel}" or rel.startswith(".claude/agents/"):
        kind = "agent"
    elif "/commands/" in f"/{rel}" or rel.startswith(".claude/commands/"):
        kind = "command"
    elif name == "plugin.json" and (".claude-plugin/" in f"/{rel}" or ".github/plugin/" in f"/{rel}"):
        kind = "plugin"
    elif name in {"marketplace.json"} or "marketplace" in name.lower():
        kind = "marketplace"
    elif path.suffix.lower() in TEXT_EXTENSIONS:
        kind = "file"
    else:
        kind = "file"
    metadata: dict[str, Any] = {"type": kind, "path": rel}
    try:
        mode = stat.S_IMODE(path.stat().st_mode)
        metadata["permissions"] = oct(mode)
        metadata["executable"] = bool(mode & stat.S_IXUSR)
    except OSError:
        pass
    text = read_text(path)
    if text is not None and kind in {"skill", "agent", "instruction", "command"}:
        frontmatter, _ = parse_frontmatter(text)
        if frontmatter:
            metadata["frontmatter"] = {
                key: value for key, value in frontmatter.items()
                if key in {"name", "description", "model", "color", "tools", "allowed-tools", "argument-hint"}
            }
            if "description" in frontmatter:
                metadata["description"] = frontmatter["description"]
        triggers = re.findall(r"<(?:example|commentary)>|(?:PreToolUse|PostToolUse|UserPromptSubmit|Stop|SessionStart)", text)
        if triggers:
            metadata["triggers"] = sorted(set(triggers))
    if kind in {"plugin", "marketplace", "hook"}:
        data = json_load(path)
        if data is not None:
            metadata["json_keys"] = sorted(data.keys()) if isinstance(data, dict) else "array"
            if isinstance(data, dict):
                for key in ("agents", "skills", "commands", "hooks", "mcpServers", "permissions", "tools"):
                    if key in data:
                        metadata[key] = data[key]
            if kind == "hook":
                metadata["hook_events"] = sorted(data.keys()) if isinstance(data, dict) else []
                metadata["hook_triggers"] = []
                if isinstance(data, dict):
                    for event, configs in data.items():
                        config_list = configs if isinstance(configs, list) else [configs]
                        for config in config_list:
                            if isinstance(config, dict):
                                metadata["hook_triggers"].append({
                                    "event": event,
                                    "matcher": config.get("matcher", ""),
                                    "hook_types": sorted({
                                        str(item.get("type"))
                                        for item in config.get("hooks", [])
                                        if isinstance(item, dict) and item.get("type")
                                    }),
                                })
    return kind, metadata


def inventory(root: Path) -> tuple[list[dict[str, Any]], list[Finding]]:
    entries: list[dict[str, Any]] = []
    findings: list[Finding] = []
    for path in iter_files(root):
        kind, metadata = classify(path, root)
        if kind != "file" or path.name in {"plugin.json", "marketplace.json"} or path.name == "hooks.json":
            entries.append(metadata)
    if not entries:
        findings.append(Finding("medium", "inventory", "No recognized extension artifacts were discovered.",
                                remediation="Point the audit at a plugin/repository root containing standard Claude/Copilot files."))
    return entries, findings


def security_scan(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_files(root):
        if path.suffix.lower() not in TEXT_EXTENSIONS and path.name not in {"Dockerfile", "Makefile"}:
            continue
        text = read_text(path)
        if text is None:
            continue
        relative = relpath(path, root)
        for number, line in enumerate(text.splitlines(), 1):
            for pattern, message in PROMPT_PATTERNS:
                if pattern.search(line):
                    findings.append(Finding("high", "prompt-injection", message, relative, number, line.strip(),
                                            "Remove instruction-override or concealment language; require explicit user consent."))
            for severity, pattern, message in SECURITY_PATTERNS:
                if pattern.search(line):
                    actual = severity
                    if message == "outbound network access" and re.search(
                        r"(?:token|secret|credential|environ|read_text|open\s*\(|cat\s+)", line, re.I
                    ):
                        actual = "critical"
                    findings.append(Finding(actual, "security", message, relative, number, line.strip(),
                                            "Review the behavior manually; prefer allowlisted, scoped, non-secret operations."))
        if path.suffix.lower() in {".sh", ".bash", ".zsh", ".py", ".js", ".ts", ".ps1"}:
            try:
                mode = stat.S_IMODE(path.stat().st_mode)
                if mode & stat.S_IWOTH:
                    findings.append(Finding("high", "permissions", "World-writable executable/script file.", relative,
                                            remediation="Remove world-write permission and keep shipped scripts immutable."))
            except OSError:
                pass
    for entry in inventory(root)[0]:
        if entry["type"] != "hook":
            continue
        path = root / entry["path"]
        data = json_load(path)
        if not isinstance(data, dict):
            findings.append(Finding("high", "hook", "Hook configuration is not valid JSON.", entry["path"]))
            continue
        for event, configs in data.items():
            if event in {"UserPromptSubmit", "Stop", "SessionStart", "SessionEnd", "PreCompact"}:
                findings.append(Finding("medium", "hook", f"Auto-triggered hook event: {event}.", entry["path"],
                                        remediation="Document why the event is needed and keep behavior read-only and narrowly scoped."))
            if not isinstance(configs, list):
                configs = [configs]
            for config in configs:
                if not isinstance(config, dict):
                    continue
                matcher = str(config.get("matcher", ""))
                if event in {"PreToolUse", "PostToolUse"} and not matcher:
                    findings.append(Finding("high", "hook", f"Broad {event} hook with empty matcher.", entry["path"],
                                            remediation="Restrict the matcher to the smallest required tool/event set."))
                if matcher in {".*", "*"} or ".*" in matcher:
                    findings.append(Finding("high", "hook", f"Broad hook matcher '{matcher}'.", entry["path"],
                                            remediation="Replace broad matchers with an explicit allowlist."))
                for hook in config.get("hooks", []):
                    if isinstance(hook, dict) and hook.get("type") == "command":
                        command = str(hook.get("command", ""))
                        if re.search(r"(?:rm\s+-rf|curl|wget|sudo|chmod\s+777)", command, re.I):
                            findings.append(Finding("critical", "hook", "Hook command contains dangerous or outbound behavior.",
                                                    entry["path"], evidence=command))
    return findings


def referenced_paths(text: str) -> list[str]:
    return sorted(set(re.findall(r"(?<![\w./-])((?:references|scripts|examples|assets)/[A-Za-z0-9_.\-/]+)", text)))


def quality_for(path: Path, root: Path) -> tuple[int, list[Finding]]:
    text = read_text(path) or ""
    relative = relpath(path, root)
    lines = text.splitlines()
    frontmatter, body_start = parse_frontmatter(text)
    score = 0
    findings: list[Finding] = []

    description = frontmatter.get("description", "")
    if description:
        score += 15
    else:
        findings.append(Finding("medium", "quality", "Missing concise description.", relative, 1,
                                remediation="Add a specific description explaining scope and intended trigger."))
    headings = [line for line in lines if re.match(r"^#{1,3}\s+\S+", line)]
    if len(headings) >= 2:
        score += 15
    else:
        findings.append(Finding("low", "quality", "Sparse structure: fewer than two section headings.", relative,
                                remediation="Organize responsibilities, process, and output into clear sections."))
    trigger_text = " ".join([description, text[:2000]])
    if re.search(r"\b(?:when|asks to|trigger|event|example|PreToolUse|UserPromptSubmit)\b", trigger_text, re.I):
        score += 15
    else:
        findings.append(Finding("low", "quality", "Trigger conditions are not specific or discoverable.", relative,
                                remediation="Name concrete user phrases, artifact types, or hook events."))
    action_lines = sum(
        bool(re.match(r"^\s*(?:\d+[.)]|[-*])\s+[A-Z][a-z]+(?:\s|$)", line))
        or bool(re.match(r"^\s*(?:Validate|Check|Create|Review|Run|Return|Report|Scan|Use|Avoid|Add|Read|Keep)\b", line))
        for line in lines[body_start:]
    )
    if action_lines >= 3:
        score += 15
    else:
        findings.append(Finding("low", "quality", "Body has limited imperative/actionable guidance.", relative,
                                remediation="Use explicit verb-first steps and decision criteria."))
    refs = referenced_paths(text)
    if refs or re.search(r"\b(?:progressive disclosure|references|scripts|examples)\b", text, re.I):
        score += 10
    else:
        findings.append(Finding("low", "quality", "No progressive-disclosure resources or file references are evident.", relative,
                                remediation="Move detailed material into references/scripts and link it from the artifact."))
    if re.search(r"\b(?:output|report|return|format|schema|structured)\b", text, re.I):
        score += 10
    else:
        findings.append(Finding("medium", "quality", "No explicit output contract is described.", relative,
                                remediation="Define the expected report, files, or structured response."))
    if re.search(r"\b(?:do not|don't|never|read-only|safe|security|permission|secret|credential)\b", text, re.I):
        score += 10
    else:
        findings.append(Finding("medium", "quality", "Safety boundaries are not explicit.", relative,
                                remediation="State read/write limits, secret handling, and unsafe-operation boundaries."))
    missing_refs = [ref for ref in refs if not (path.parent / ref).exists() and not (root / ref).exists()]
    if refs and not missing_refs:
        score += 10
    elif missing_refs:
        findings.append(Finding("medium", "quality", "Broken relative file reference(s): " + ", ".join(missing_refs),
                                relative, line_number(text, missing_refs[0]),
                                remediation="Fix or remove stale references."))
    else:
        findings.append(Finding("low", "quality", "No cross-references to supporting files.", relative,
                                remediation="Link related scripts, examples, or references where useful."))
    return max(0, min(100, score)), findings


def quality_scan(root: Path) -> tuple[list[dict[str, Any]], list[Finding]]:
    results: list[dict[str, Any]] = []
    findings: list[Finding] = []
    for path in iter_files(root):
        kind, _ = classify(path, root)
        if kind not in {"skill", "agent", "instruction", "command"}:
            continue
        score, local_findings = quality_for(path, root)
        results.append({"path": relpath(path, root), "type": kind, "score": score})
        findings.extend(local_findings)
    if results:
        average = round(sum(item["score"] for item in results) / len(results))
    else:
        average = 0
    return [{"artifacts": results, "score": average}], findings


def candidate_metadata(root: Path) -> list[Path]:
    candidates = []
    for path in iter_files(root):
        if path.name == "plugin.json" and (".claude-plugin" in path.parts or ".github" in path.parts):
            candidates.append(path)
        elif path.suffix.lower() == ".json" and (
            path.name == "marketplace.json" or "marketplace" in path.name.lower()
        ):
            candidates.append(path)
    return sorted(set(candidates))


def validate_source(source: Any, path: str, findings: list[Finding]) -> None:
    if isinstance(source, str):
        if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", source):
            if not source.startswith("https://"):
                findings.append(Finding("high", "marketplace", "Source URL must use HTTPS.", path))
        elif os.path.isabs(source) or re.match(r"^[A-Za-z]:[\\/]", source) or ".." in Path(source.replace("\\", "/")).parts:
            findings.append(Finding("high", "marketplace", f"Unsafe source path: {source}", path))
    elif isinstance(source, dict):
        source_type = source.get("source")
        if source_type != "github":
            findings.append(Finding("high", "marketplace", 'source.source must be "github".', path))
        repo = source.get("repo")
        if not isinstance(repo, str) or not re.match(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$", repo):
            findings.append(Finding("high", "marketplace", "source.repo must use owner/repo format.", path))
        for key in ("repository", "homepage"):
            value = source.get(key)
            if value and (not isinstance(value, str) or not value.startswith("https://")):
                findings.append(Finding("high", "marketplace", f"{key} must be an HTTPS URL.", path))
        source_path = str(source.get("path", "")).replace("\\", "/")
        if source_path and (os.path.isabs(source_path) or ".." in Path(source_path).parts):
            findings.append(Finding("high", "marketplace", "Source path escapes its repository.", path))
        if source.get("ref") and not source.get("sha"):
            findings.append(Finding("medium", "marketplace", "Source ref is not pinned by a commit SHA.", path))
        if source.get("sha") and not re.match(r"^[0-9a-fA-F]{7,64}$", str(source["sha"])):
            findings.append(Finding("high", "marketplace", "Source SHA must be a hexadecimal commit identifier.", path))


def marketplace_scan(root: Path, policy: str = "marketplace") -> list[Finding]:
    findings: list[Finding] = []
    names: dict[str, str] = {}
    for path in candidate_metadata(root):
        data = json_load(path)
        relative = relpath(path, root)
        if data is None:
            findings.append(Finding("high", "marketplace", "Invalid JSON metadata.", relative))
            continue
        is_marketplace_doc = isinstance(data, dict) and isinstance(data.get("plugins"), list)
        scope = "marketplace" if is_marketplace_doc else ("plugin-manifests" if path.name == "plugin.json" else relative)
        objects = data.get("plugins", []) if is_marketplace_doc else [data]
        for item in objects:
            if not isinstance(item, dict):
                findings.append(Finding("high", "marketplace", "Metadata entry is not an object.", relative))
                continue
            name = item.get("name")
            if not isinstance(name, str) or not re.match(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$", name):
                findings.append(Finding("high", "marketplace", "Missing or invalid kebab-case name.", relative))
            elif f"{scope}:{name}" in names:
                findings.append(Finding("high", "marketplace", f"Duplicate metadata name '{name}' (also in {names[f'{scope}:{name}']}).", relative))
            else:
                names[f"{scope}:{name}"] = relative
            if not isinstance(item.get("description"), str) or not item.get("description", "").strip():
                findings.append(Finding("medium", "marketplace", "Missing description.", relative))
            if "version" in item and (not isinstance(item["version"], str) or not SEMVER.match(item["version"])):
                findings.append(Finding("high", "marketplace", "Version is not valid semver.", relative))
            if "author" in item and not isinstance(item["author"], (str, dict)):
                findings.append(Finding("medium", "marketplace", "Author must be a string or object.", relative))
            if "repository" in item and (not isinstance(item["repository"], str) or not item["repository"].startswith("https://")):
                findings.append(Finding("high", "marketplace", "Repository must be an HTTPS URL.", relative))
            if "homepage" in item and (not isinstance(item["homepage"], str) or not item["homepage"].startswith("https://")):
                findings.append(Finding("high", "marketplace", "Homepage must be an HTTPS URL.", relative))
            if "keywords" in item and (not isinstance(item["keywords"], list) or not all(isinstance(k, str) for k in item["keywords"])):
                findings.append(Finding("medium", "marketplace", "Keywords must be an array of strings.", relative))
            if "source" in item:
                validate_source(item["source"], relative, findings)
            for key in ("sourceRepo", "sourceRepository"):
                if key in item and (not isinstance(item[key], str) or not item[key].startswith("https://")):
                    findings.append(Finding("high", "marketplace", f"{key} must be an HTTPS URL.", relative))
            source_path = item.get("sourcePath")
            if source_path and (os.path.isabs(str(source_path)) or ".." in Path(str(source_path).replace("\\", "/")).parts):
                findings.append(Finding("high", "marketplace", "sourcePath escapes its repository.", relative))
            if item.get("sourceRef") and not item.get("sourceSha"):
                findings.append(Finding("medium", "marketplace", "sourceRef is not pinned by sourceSha.", relative))
            if item.get("sourceSha") and not re.match(r"^[0-9a-fA-F]{7,64}$", str(item["sourceSha"])):
                findings.append(Finding("high", "marketplace", "sourceSha must be hexadecimal.", relative))
            if policy == "public-submission":
                required_fields = ("name", "description", "author", "repository", "keywords")
                if path.name != "plugin.json":
                    required_fields += ("source",)
                for required in required_fields:
                    if not item.get(required):
                        findings.append(Finding("high", "marketplace", f"Public submission requires '{required}'.", relative))
                source = item.get("source")
                if path.name != "plugin.json" and isinstance(source, dict) and not source.get("sha"):
                    findings.append(Finding("high", "marketplace", "Public submission sources must include a pinned SHA.", relative))
    return findings


def dependency_findings(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_files(root):
        relative = relpath(path, root)
        if path.name == "package.json":
            data = json_load(path)
            if isinstance(data, dict):
                for section in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
                    for package, version in (data.get(section) or {}).items():
                        if isinstance(version, str) and DEPENDENCY_VERSION.search(version):
                            findings.append(Finding("medium", "integrity", f"Unpinned {section} dependency: {package}={version}",
                                                    relative, remediation="Pin an exact version or immutable commit SHA."))
        elif path.name in {"requirements.txt", "requirements-dev.txt"}:
            text = read_text(path) or ""
            for number, line in enumerate(text.splitlines(), 1):
                clean = line.strip()
                if clean and not clean.startswith(("#", "-r")) and "==" not in clean:
                    findings.append(Finding("medium", "integrity", "Python dependency is not pinned with ==.", relative, number, clean))
        elif path.name == "pyproject.toml":
            text = read_text(path) or ""
            for number, line in enumerate(text.splitlines(), 1):
                if re.search(r"^\s*['\"][A-Za-z0-9_.-]+\s*(?:[<>=!~^]|$)", line) and "==" not in line:
                    findings.append(Finding("medium", "integrity", "Possible unpinned pyproject dependency.", relative, number, line.strip()))
    return findings


def should_hash(path: Path, root: Path, manifest_rel: str) -> bool:
    relative = relpath(path, root)
    return relative != manifest_rel and not any(part in EXCLUDED_DIRS for part in Path(relative).parts)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def integrity_entries(root: Path, manifest_path: Path) -> list[dict[str, Any]]:
    manifest_rel = relpath(manifest_path, root)
    entries = []
    for path in iter_files(root):
        if should_hash(path, root, manifest_rel):
            try:
                entries.append({"path": relpath(path, root), "sha256": sha256(path), "size": path.stat().st_size})
            except OSError:
                continue
    return sorted(entries, key=lambda item: item["path"])


def generate_integrity(root: Path, manifest_path: Path) -> tuple[dict[str, Any], list[Finding]]:
    document = {
        "format": "extension-audit-integrity-v1",
        "algorithm": "sha256",
        "root": ".",
        "files": integrity_entries(root, manifest_path),
    }
    try:
        manifest_path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        return document, [Finding("critical", "integrity", f"Unable to write integrity manifest: {exc}", relpath(manifest_path, root))]
    return document, []


def verify_integrity(root: Path, manifest_path: Path) -> tuple[dict[str, Any], list[Finding]]:
    findings: list[Finding] = []
    relative = relpath(manifest_path, root)
    data = json_load(manifest_path)
    if not isinstance(data, dict) or not isinstance(data.get("files"), list):
        return {"manifest": relative, "modified": [], "missing": [], "untracked": []}, [
            Finding("critical", "integrity", "INTEGRITY.json is missing or malformed.", relative)
        ]
    expected = {item.get("path"): item for item in data["files"] if isinstance(item, dict) and item.get("path")}
    current = {relpath(path, root): path for path in iter_files(root) if should_hash(path, root, relative)}
    modified: list[str] = []
    missing = sorted(set(expected) - set(current))
    untracked = sorted(set(current) - set(expected))
    for path_name, item in expected.items():
        if path_name in current:
            try:
                if sha256(current[path_name]) != item.get("sha256"):
                    modified.append(path_name)
            except OSError:
                modified.append(path_name)
    for path_name in modified:
        findings.append(Finding("high", "integrity", "File hash changed.", path_name))
    for path_name in missing:
        findings.append(Finding("high", "integrity", "Manifest file is missing from the working tree.", path_name))
    for path_name in untracked:
        findings.append(Finding("medium", "integrity", "File is not recorded in INTEGRITY.json.", path_name))
    return {"manifest": relative, "modified": sorted(modified), "missing": missing, "untracked": untracked}, findings


def build_report(root: Path, sections: dict[str, Any], findings: list[Finding], note: str | None = None) -> dict[str, Any]:
    counts = {level: sum(f.severity == level for f in findings) for level in SEVERITY_RANK}
    report: dict[str, Any] = {
        "tool": "extension-audit",
        "version": "0.1.0",
        "path": str(root),
        "static_only": True,
        "heuristic_limitations": [
            "Pattern matching can miss obfuscated behavior and can flag benign examples.",
            "No target extension code, hooks, commands, or network requests are executed.",
            "Integrity proves bytes match a local manifest; it does not prove provenance or safety.",
            "Semantic quality is a deterministic rubric, not an LLM judgment.",
        ],
        "sections": sections,
        "findings": [f.as_dict() for f in findings],
        "summary": {"counts": counts, "total_findings": len(findings)},
    }
    if note:
        report["note"] = note
    return report


def emit(report: dict[str, Any], as_json: bool, output: str | None) -> None:
    if as_json:
        rendered = json.dumps(report, indent=2, sort_keys=True)
    else:
        summary = report["summary"]["counts"]
        print(f"extension-audit: {report['path']}")
        print(f"Findings: {report['summary']['total_findings']} "
              f"(critical={summary['critical']}, high={summary['high']}, medium={summary['medium']}, low={summary['low']})")
        for name, section in report["sections"].items():
            if isinstance(section, dict):
                print(f"- {name}: {json.dumps(section, sort_keys=True)}")
            else:
                print(f"- {name}: {section}")
        for finding in report["findings"]:
            location = finding.get("path", "")
            if finding.get("line"):
                location += f":{finding['line']}"
            prefix = f"[{finding['severity'].upper()}] {finding['category']}"
            print(f"{prefix} {location} — {finding['message']}")
            if finding.get("evidence"):
                print(f"  evidence: {finding['evidence'][:240]}")
        print("Heuristic limitations apply; review findings before taking action.")
        rendered = json.dumps(report, indent=2, sort_keys=True)
    if output:
        Path(output).write_text(rendered + "\n", encoding="utf-8")
    elif as_json:
        print(rendered)


def exit_code(findings: list[Finding], command: str, sections: dict[str, Any]) -> int:
    if any(f.severity == "critical" for f in findings):
        return 3
    if any(f.severity == "high" for f in findings):
        return 2
    if command == "quality" and sections.get("quality", [{}])[0].get("score", 100) < 60:
        return 1
    return 0


def root_from(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.exists():
        raise SystemExit(f"target does not exist: {value}")
    return path


def common_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("path", nargs="?", default=".", help="Local plugin or repository path.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human-readable output.")
    parser.add_argument("--output", help="Also write the rendered report to a file.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Static, report-only audit for extension artifacts.")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan", help="Run inventory, security, quality, marketplace, and available integrity checks.")
    common_parser(scan)
    scan.add_argument("--policy", choices=("marketplace", "public-submission"), default="marketplace")
    quality = sub.add_parser("quality", help="Score semantic quality of extension artifacts.")
    common_parser(quality)
    marketplace = sub.add_parser("marketplace", help="Validate marketplace/plugin metadata.")
    common_parser(marketplace)
    marketplace.add_argument("--policy", choices=("marketplace", "public-submission"), default="marketplace")
    integrity = sub.add_parser("integrity", help="Generate deterministic INTEGRITY.json.")
    common_parser(integrity)
    integrity.add_argument("--manifest", default="INTEGRITY.json", help="Manifest path relative to target.")
    verify = sub.add_parser("verify", help="Verify INTEGRITY.json and report modified/missing/untracked files.")
    common_parser(verify)
    verify.add_argument("--manifest", default="INTEGRITY.json", help="Manifest path relative to target.")

    args = parser.parse_args(argv)
    root = root_from(args.path)
    findings: list[Finding] = []
    sections: dict[str, Any] = {}
    command = args.command

    if command in {"scan"}:
        entries, local = inventory(root)
        sections["inventory"] = entries
        findings.extend(local)
        findings.extend(security_scan(root))
        quality_data, local = quality_scan(root)
        sections["quality"] = quality_data
        findings.extend(local)
        findings.extend(marketplace_scan(root, args.policy))
        findings.extend(dependency_findings(root))
        manifest = root / "INTEGRITY.json"
        if manifest.exists():
            verification, local = verify_integrity(root, manifest)
            sections["integrity"] = verification
            findings.extend(local)
        else:
            sections["integrity"] = {"status": "not present", "hint": "Run integrity to create INTEGRITY.json."}
    elif command == "quality":
        quality_data, findings = quality_scan(root)
        sections["quality"] = quality_data
    elif command == "marketplace":
        findings = marketplace_scan(root, args.policy)
        sections["marketplace"] = {"metadata_files": [relpath(p, root) for p in candidate_metadata(root)], "policy": args.policy}
    elif command in {"integrity", "verify"}:
        manifest = Path(args.manifest)
        if not manifest.is_absolute():
            manifest = root / manifest
        if command == "integrity":
            document, findings = generate_integrity(root, manifest)
            sections["integrity"] = {"manifest": relpath(manifest, root), "file_count": len(document["files"]), "status": "generated"}
        else:
            verification, findings = verify_integrity(root, manifest)
            sections["integrity"] = verification
        findings.extend(dependency_findings(root))

    report = build_report(root, sections, findings)
    emit(report, args.json, args.output)
    return exit_code(findings, command, sections)


if __name__ == "__main__":
    raise SystemExit(main())
