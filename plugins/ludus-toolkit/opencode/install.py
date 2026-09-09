#!/usr/bin/env python3
"""Install ludus-toolkit skills and optionally merge its OpenCode config."""

from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import sys
import tempfile
import uuid
from pathlib import Path


SKILL_NAMES = (
    "change-template-input-language",
    "ludus-cli",
    "ludus-environment-guide",
    "ludus-range-config",
    "ludus-troubleshoot",
    "update-os-template",
)
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_SOURCE = SCRIPT_DIR.parent / "skills"
CONFIG_FRAGMENT = SCRIPT_DIR / "opencode.json"


class InstallError(Exception):
    """A conflict or invalid installation input."""


def tree_manifest(root: Path, *, reject_symlinks: bool = False) -> dict[str, bytes | None]:
    if reject_symlinks and root.is_symlink():
        raise InstallError(f"installed skill is a symlink: {root}")

    manifest: dict[str, bytes | None] = {}
    for current, directories, files in os.walk(root, followlinks=True):
        current_path = Path(current)
        for name in directories:
            path = current_path / name
            if reject_symlinks and path.is_symlink():
                raise InstallError(f"installed skill contains a symlink: {path}")
            manifest[f"{path.relative_to(root).as_posix()}/"] = None
        for name in files:
            path = current_path / name
            if reject_symlinks and path.is_symlink():
                raise InstallError(f"installed skill contains a symlink: {path}")
            manifest[path.relative_to(root).as_posix()] = path.read_bytes()
    return manifest


def validate_sources() -> None:
    missing = []
    for name in SKILL_NAMES:
        source = SKILL_SOURCE / name
        if not source.is_dir() or not (source / "SKILL.md").is_file():
            missing.append(str(source))
    if missing:
        raise InstallError("missing bundled skill source(s): " + ", ".join(missing))
    if not CONFIG_FRAGMENT.is_file():
        raise InstallError(f"missing OpenCode config fragment: {CONFIG_FRAGMENT}")


def preflight_skills(project: Path) -> tuple[list[str], list[str]]:
    install_root = project / ".opencode" / "skills"
    pending: list[str] = []
    current: list[str] = []

    for name in SKILL_NAMES:
        source = SKILL_SOURCE / name
        destination = install_root / name
        if not os.path.lexists(destination):
            pending.append(name)
            continue
        if not destination.is_dir() or destination.is_symlink():
            raise InstallError(f"skill destination conflicts with bundled content: {destination}")
        try:
            installed = tree_manifest(destination, reject_symlinks=True)
        except OSError as error:
            raise InstallError(f"cannot inspect installed skill {destination}: {error}") from error
        if tree_manifest(source) != installed:
            raise InstallError(
                f"installed skill differs from bundled content: {destination}; "
                "move or remove it before retrying"
            )
        current.append(name)

    return pending, current


def prepare_config(project: Path) -> tuple[Path, dict[str, object] | None]:
    root_json = project / "opencode.json"
    candidates = (
        root_json,
        project / "opencode.jsonc",
        project / ".opencode" / "opencode.json",
    )
    existing = [path for path in candidates if os.path.lexists(path)]
    if existing and existing != [root_json]:
        locations = ", ".join(str(path) for path in existing)
        raise InstallError(
            "automatic config merge requires the project-root opencode.json to be the "
            f"only OpenCode config; found: {locations}. Merge opencode/opencode.json manually."
        )

    fragment = json.loads(CONFIG_FRAGMENT.read_text(encoding="utf-8"))
    ludus_config = fragment["mcp"]["ludus"]

    if not existing:
        return root_json, fragment
    if root_json.is_symlink() or not root_json.is_file():
        raise InstallError(f"refusing to replace non-regular config file: {root_json}")

    try:
        config = json.loads(root_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InstallError(f"cannot parse {root_json} as JSON: {error}") from error
    if not isinstance(config, dict):
        raise InstallError(f"OpenCode config must contain a JSON object: {root_json}")

    if "mcp" not in config:
        proposed = copy.deepcopy(config)
        proposed["mcp"] = {"ludus": ludus_config}
        return root_json, proposed
    mcp = config["mcp"]
    if not isinstance(mcp, dict):
        raise InstallError(f"OpenCode config field 'mcp' must be an object: {root_json}")

    if "ludus" not in mcp:
        proposed = copy.deepcopy(config)
        proposed["mcp"]["ludus"] = ludus_config
        return root_json, proposed
    existing_ludus = mcp["ludus"]
    if existing_ludus != ludus_config:
        raise InstallError(
            f"OpenCode config already defines conflicting mcp.ludus settings in {root_json}; "
            "merge opencode/opencode.json manually"
        )
    return root_json, None


def install_skills(project: Path, pending: list[str]) -> None:
    install_root = project / ".opencode" / "skills"
    install_root.mkdir(parents=True, exist_ok=True)
    for name in pending:
        destination = install_root / name
        temporary = install_root / f".{name}.tmp-{uuid.uuid4().hex}"
        try:
            shutil.copytree(SKILL_SOURCE / name, temporary, symlinks=False)
            os.replace(temporary, destination)
        finally:
            if temporary.exists():
                shutil.rmtree(temporary)


def write_config(path: Path, config: dict[str, object]) -> None:
    rendered = json.dumps(config, indent=2, ensure_ascii=False) + "\n"
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as temporary:
            temporary.write(rendered)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_name = temporary.name
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install ludus-toolkit's six skills into an OpenCode project."
    )
    parser.add_argument("project", type=Path, help="path to the consuming project")
    parser.add_argument(
        "--merge-config",
        action="store_true",
        help="create or merge the project-root opencode.json MCP definition",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project = args.project.expanduser().resolve()
    try:
        if not project.is_dir():
            raise InstallError(f"project directory does not exist: {project}")
        validate_sources()
        pending, current = preflight_skills(project)
        config_path: Path | None = None
        proposed_config: dict[str, object] | None = None
        if args.merge_config:
            config_path, proposed_config = prepare_config(project)

        install_skills(project, pending)
        if config_path is not None and proposed_config is not None:
            write_config(config_path, proposed_config)

        if pending:
            print(f"installed {len(pending)} skill(s) in {project / '.opencode' / 'skills'}")
        if current:
            print(f"{len(current)} skill(s) already current")
        if config_path is not None:
            action = "updated" if proposed_config is not None else "already current"
            print(f"OpenCode config {action}: {config_path}")
        print("Restart OpenCode to load the installed skills and MCP server.")
        return 0
    except (InstallError, OSError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
