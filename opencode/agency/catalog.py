from __future__ import annotations

"""Catalog loading for OpenCode marketplace entries."""

import json
from pathlib import Path

from . import CatalogError, Entry


_KNOWN_DRAFT_MARKERS = {"draft", "wip", "parked", "archive", "in-progress"}
_DRAFT_NAME_PREFIXES = ("draft-", "wip-", "parked-", "archive-")
_FORBIDDEN_SOURCE_PARTS = {".."}


def _is_parked_entry(source: str) -> bool:
    """Return True when a source path points at parked/draft-like content."""

    normalized = Path(source).as_posix().strip("/")
    if any(part in _FORBIDDEN_SOURCE_PARTS for part in normalized.split("/")):
        raise CatalogError(f"entry source path escapes marketplace tree: {source}")
    parts = normalized.split("/")
    return any(part in _KNOWN_DRAFT_MARKERS for part in parts)


def _infer_kind(source: Path) -> str:
    if not source.parts:
        return "bundle"
    top = source.parts[0]
    if top == "skills":
        return "skill"
    if top == "agents":
        return "agent"
    if top == "commands":
        return "command"
    if top == "plugins":
        return "bundle"
    return "bundle"


def _bundle_version(source: Path) -> str:
    manifest_path = source / ".claude-plugin" / "plugin.json"
    if not manifest_path.is_file():
        raise CatalogError(f"bundle entry missing plugin.json: {source}")
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CatalogError(f"cannot read bundle plugin manifest: {manifest_path}") from error

    version = data.get("version")
    if not isinstance(version, str) or not version:
        raise CatalogError(f"bundle entry version missing in {manifest_path}")
    return version


def load_entries(repo: Path) -> dict[str, Entry]:
    """Load curated entries from ``.claude-plugin/marketplace.json``.

    This keeps the market as the single source of truth while filtering entries
    that are intentionally not shipped (drafts and parked bundles).
    """

    repo = repo.resolve()
    market_path = repo / ".claude-plugin" / "marketplace.json"
    if not market_path.is_file():
        raise CatalogError(f"marketplace manifest missing: {market_path}")

    try:
        data = json.loads(market_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CatalogError(f"cannot read marketplace JSON {market_path}: {error}") from error

    raw_plugins = data.get("plugins")
    if not isinstance(raw_plugins, list):
        raise CatalogError("marketplace field `plugins` must be a list")

    out: dict[str, Entry] = {}
    for item in raw_plugins:
        if not isinstance(item, dict):
            raise CatalogError(f"invalid marketplace entry: {item!r}")

        name = item.get("name")
        source_value = item.get("source")

        if not isinstance(name, str) or not name:
            raise CatalogError(f"invalid entry name in marketplace: {item!r}")
        if not isinstance(source_value, str) or not source_value:
            raise CatalogError(f"entry {name}: missing source")
        if source_value.startswith("/"):
            raise CatalogError(f"entry {name}: absolute source paths are not supported: {source_value}")

        if _is_parked_entry(source_value):
            continue

        # Exclude entries whose name starts with a draft prefix
        if any(name.startswith(p) for p in _DRAFT_NAME_PREFIXES):
            continue

        source = (repo / source_value).resolve()
        if not source.is_dir() and not source.is_file():
            raise CatalogError(f"entry {name}: source path does not exist: {source_value}")

        kind = _infer_kind(Path(source_value))
        if kind == "bundle":
            version = _bundle_version(source)
        else:
            version = item.get("version")
            if not isinstance(version, str) or not version:
                raise CatalogError(f"entry {name}: missing version")

        if name in out:
            raise CatalogError(f"duplicate marketplace entry name: {name}")

        out[name] = Entry(
            name=name,
            source=source,
            version=version,
            kind=kind,
            manifest=dict(item),
        )

    return out
