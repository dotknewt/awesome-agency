from __future__ import annotations

"""Materialize Claude marketplace sources into OpenCode's layout."""

import json
import re
from pathlib import Path

import yaml

from . import ContentError, Entry

_TEXT_EXTENSIONS = {".md", ".txt", ".json", ".yml", ".yaml", ".toml", ".py", ".sh", ".jsonc"}
_PLACEHOLDER = "${CLAUDE_PLUGIN_ROOT}"
_MODES: dict[str, int] = {}
_EXCLUDED = {".git", ".svn", "__pycache__", ".DS_Store", "node_modules"}
_NATIVE_TO_PERMISSION = {
    "read": "read", "read*": "read", "edit": "edit", "write": "edit",
    "glob": "glob", "grep": "grep", "bash": "bash", "webfetch": "webfetch",
    "web_fetch": "webfetch", "websearch": "websearch", "web_search": "websearch",
    "task": "task", "askuserquestion": "question", "skill": "skill",
}
_OPENCODE_COLORS = {
    "red": "#EF4444",
    "green": "#22C55E",
    "blue": "#3B82F6",
    "yellow": "#EAB308",
    "cyan": "#06B6D4",
    "magenta": "#D946EF",
    "purple": "#A855F7",
    "orange": "#F97316",
    "pink": "#EC4899",
}


def _is_text(path: Path) -> bool:
    return path.suffix.lower() in _TEXT_EXTENSIONS


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        raise ValueError("frontmatter block missing")
    end = text.find("\n---", 4)
    if end < 0:
        raise ValueError("frontmatter block missing closing marker")
    front = text[4:end]
    try:
        raw = yaml.safe_load(front) or {}
    except yaml.YAMLError as error:
        # Some shipped descriptions contain an unquoted second colon. Retry
        # with that scalar quoted, while retaining YAML as the parser.
        repaired = []
        for line in front.splitlines():
            match = re.match(r"^(description:\s*)(?![>|])(.+)$", line)
            if match and ":" in match.group(2):
                repaired.append(match.group(1) + json.dumps(match.group(2)))
            else:
                repaired.append(line)
        try:
            raw = yaml.safe_load("\n".join(repaired)) or {}
        except yaml.YAMLError:
            raise error
    if not isinstance(raw, dict):
        raise ContentError("frontmatter must be a YAML mapping")
    return raw, text[end + 4:].lstrip("\n")


def _model(value: str | None) -> str | None:
    if value is None:
        return None
    return value if "/" in value else f"anthropic/{value}"


def _items(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, list):
        return [str(item) for item in value]
    raise ContentError("agent tools must be a YAML list or comma-delimited string")


def _color(value: str | None) -> str | None:
    if value is None:
        return None
    if re.fullmatch(r"#[0-9A-Fa-f]{6}", str(value)):
        return str(value)
    return _OPENCODE_COLORS.get(str(value).lower())


def _permission_key(tool: str) -> str:
    lowered = tool.lower()
    if lowered in _NATIVE_TO_PERMISSION:
        return _NATIVE_TO_PERMISSION[lowered]
    if tool.startswith("mcp__"):
        return tool
    raise ContentError(f"unsupported source tool: {tool}")


def _agent_frontmatter(raw: dict, override: str | None) -> dict:
    fields = {key: raw[key] for key in ("description", "variant") if key in raw}
    if "color" in raw:
        converted_color = _color(raw.get("color"))
        if converted_color:
            fields["color"] = converted_color
    fields["mode"] = "subagent"
    fields["model"] = _model(override or raw.get("model"))
    tools = _items(raw.get("tools"))
    denied = _items(raw.get("disallowedTools", raw.get("disallowed-tools")))
    if tools or denied:
        permission = {"*": "deny"}
        for tool in tools:
            permission[_permission_key(tool)] = "allow"
        for tool in denied:
            permission[_permission_key(tool)] = "deny"
        fields["permission"] = permission
    return fields


def _rewrite_references(text: str, managed_root: str) -> str:
    def replace(match: re.Match[str]) -> str:
        suffix = match.group(1) or ""
        if suffix.startswith(("skills/", "agents/", "commands/", "instructions/")):
            return f"{managed_root.rsplit('/awesome-agency/', 1)[0]}/awesome-agency/packages/{suffix}"
        return f"{managed_root}{suffix}"

    return re.sub(r"\$\{CLAUDE_PLUGIN_ROOT\}(/[A-Za-z0-9_.${}/-]+)?", replace, text)


def _render_file(path: Path, managed_root: str, model: str | None, *, agent: bool, convert: bool) -> bytes:
    text = path.read_text(encoding="utf-8")
    if convert:
        try:
            raw, body = _parse_frontmatter(text)
        except ValueError:
            rendered = text
        else:
            if agent:
                fields = _agent_frontmatter(raw, model)
            else:
                fields = {key: raw[key] for key in ("name", "description", "license", "compatibility", "metadata") if key in raw}
            rendered = "---\n" + yaml.safe_dump(fields, sort_keys=False) + "---\n" + body
    else:
        rendered = text
    return _rewrite_references(rendered, managed_root).encode("utf-8")


def _validate_key(key: Path) -> str:
    if key.is_absolute() or ".." in key.parts:
        raise ContentError(f"public path must be relative and non-traversing: {key}")
    return key.as_posix()


def _validate_relative_public_path(path: Path) -> str:
    return _validate_key(path)


def _copy_tree(source: Path, key: Path, out: dict[str, bytes], managed_root: str, model: str | None, *, agent=False, convert=False, stack: set[Path] | None = None) -> None:
    stack = set() if stack is None else stack
    if source.is_symlink():
        if not source.exists():
            raise ContentError(f"broken symlink in source content: {source}")
        source = source.resolve()
    if source.is_dir():
        marker = source.resolve()
        if marker in stack:
            raise ContentError(f"cyclic symlink detected while copying {source}")
        stack.add(marker)
        for child in sorted(source.iterdir(), key=lambda item: item.name):
            if child.name in _EXCLUDED:
                continue
            _copy_tree(child, key / child.name, out, managed_root, model, agent=agent, convert=convert, stack=stack)
        stack.remove(marker)
        return
    if not source.is_file():
        raise ContentError(f"unsupported content node: {source}")
    public = _validate_key(key)
    out[public] = _render_file(source, managed_root, model, agent=agent, convert=convert) if _is_text(source) else source.read_bytes()
    _MODES[public] = source.stat().st_mode & 0o7777


def _repo_root(source: Path) -> Path:
    for parent in (source, *source.parents):
        if (parent / ".claude-plugin" / "marketplace.json").is_file():
            return parent
    return source


def _package_root(kind: str, identity: str) -> Path:
    return Path("awesome-agency") / "packages" / kind / identity


def _manifest(source: Path) -> dict:
    path = source / ".claude-plugin" / "plugin.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ContentError(f"cannot read bundle manifest: {path}") from error
    if not isinstance(data, dict):
        raise ContentError(f"bundle manifest is not an object: {path}")
    return data


def _explicit_agents(source: Path, manifest: dict) -> list[Path]:
    values = manifest.get("agents", [])
    if not isinstance(values, list):
        raise ContentError("plugin.json agents must be a list")
    result = []
    for value in values:
        path = Path(value) if isinstance(value, str) else Path(".")
        if not isinstance(value, str) or path.is_absolute() or ".." in path.parts:
            raise ContentError(f"invalid manifest agent path: {value!r}")
        result.append(source / value.removeprefix("./"))
    return result


def _materialize_agent(source: Path, out: dict[str, bytes], model: str | None, target: Path) -> None:
    if source.is_file():
        main = source.resolve()
        source = main.parent
        identity = main.stem
    else:
        main = source / f"{source.name}.md"
        identity = source.name
    package = _package_root("agents", identity)
    managed = str(target.resolve() / package)
    _copy_tree(source, package, out, managed, model, convert=False)
    repo = _repo_root(source)
    referenced = set()
    for path in source.rglob("*"):
        if path.is_file() and _is_text(path):
            referenced.update(re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/(skills|agents|instructions|commands)/([A-Za-z0-9_.${}/-]+)", path.read_text(encoding="utf-8", errors="ignore")))
    for root, value in referenced:
        identity = value.split("/", 1)[0]
        dependency = repo / root / identity
        if dependency.is_dir():
            destination = Path("awesome-agency") / "packages" / root / identity
            _copy_tree(dependency, destination, out, str(target.resolve() / destination), model, convert=False)
    if not main.is_file():
        raise ContentError(f"agent source has no canonical {main.name}: {source}")
    _copy_tree(main, Path("agents") / main.name, out, managed, model, agent=True, convert=True)


def _materialize_skill(source: Path, out: dict[str, bytes], model: str | None, target: Path) -> None:
    source = source.resolve()
    identity = source.name
    package = _package_root("skills", identity)
    managed = str(target.resolve() / package)
    _copy_tree(source, package, out, managed, model, convert=False)
    main = source / "SKILL.md"
    if not main.is_file():
        raise ContentError(f"skill source has no SKILL.md: {source}")
    _copy_tree(main, Path("skills") / identity / "SKILL.md", out, managed, model, convert=True)
    references = source / "references"
    if references.is_dir():
        _copy_tree(references, Path("skills") / identity / "references", out, managed, model, convert=False)
    try:
        raw, body = _parse_frontmatter(main.read_text(encoding="utf-8"))
    except ValueError:
        raw, body = {}, ""
    if raw.get("disable-model-invocation") is True:
        description = raw.get("description", identity)
        command = "---\n" + yaml.safe_dump({"description": description}, sort_keys=False)
        command += "---\n\n" + body.rstrip() + "\n\nArguments: $ARGUMENTS\n"
        out[f"commands/{identity}.md"] = _rewrite_references(command, managed).encode("utf-8")


def _bundle(source: Path, entry: Entry, out: dict[str, bytes], model: str | None, target: Path) -> None:
    source = source.resolve()
    manifest = _manifest(source)
    package = _package_root("bundles", entry.name)
    managed = str(target.resolve() / package)
    _copy_tree(source, package, out, managed, model, convert=False)
    skills = source / "skills"
    if skills.is_dir():
        for child in sorted(skills.iterdir(), key=lambda item: item.name):
            _materialize_skill(child, out, model, target)
    for agent in _explicit_agents(source, manifest):
        if not agent.exists():
            raise ContentError(f"manifest agent does not exist: {agent}")
        _materialize_agent(agent, out, model, target)


def render_entry(entry: Entry, target: Path, model: str | None) -> dict[str, bytes]:
    """Return stable target-relative OpenCode files for one marketplace entry."""
    _MODES.clear()
    source = Path(entry.source)
    if not source.exists():
        raise ContentError(f"entry source does not exist: {source}")
    out: dict[str, bytes] = {}
    if entry.kind == "bundle":
        _bundle(source, entry, out, model, Path(target))
    elif entry.kind == "skill":
        _materialize_skill(source, out, model, Path(target))
    elif entry.kind == "agent":
        _materialize_agent(source, out, model, Path(target))
    elif entry.kind == "command":
        package = _package_root("commands", source.name)
        managed = str(Path(target).resolve() / package)
        _copy_tree(source, package, out, managed, model, convert=False)
        _copy_tree(source, Path("commands"), out, managed, model, convert=False)
    else:
        raise ContentError(f"unsupported entry kind: {entry.kind}")
    return out


def get_rendered_file_modes() -> dict[str, int]:
    return dict(_MODES)
