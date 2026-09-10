#!/usr/bin/env python3
"""CLI entry point for the OpenCode marketplace installer.

Usage:
    python3 opencode/install.py list [--repo PATH]
    python3 opencode/install.py install ENTRY... [--repo PATH] [--project PATH | --global] [--model MODEL] [--dry-run]
    python3 opencode/install.py update [ENTRY...] [--repo PATH] [--project PATH | --global] [--model MODEL] [--dry-run]
    python3 opencode/install.py uninstall ENTRY... [--repo PATH] [--project PATH | --global] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure the opencode directory is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agency.catalog import load_entries
from agency.content import render_entry, get_rendered_file_modes
from agency.config import render_configuration
from agency.state import (
    apply_operation,
    load_state,
    plan_operation,
    plan_uninstall_many,
)
from agency import AgencyError, CatalogError, ContentError, StateError


def _default_repo() -> Path:
    p = Path(__file__).resolve().parent.parent
    if (p / ".claude-plugin" / "marketplace.json").is_file():
        return p
    return Path.cwd()


def _resolve_target(args) -> Path | None:
    if getattr(args, "global_target", False):
        xdg = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
        return Path(xdg) / "opencode"
    project = getattr(args, "project", None)
    if project:
        return Path(project) / ".opencode"
    return None


def cmd_list(args, repo: Path) -> int:
    entries = load_entries(repo)
    for name in sorted(entries):
        e = entries[name]
        print(f"  {e.name:30s}  {e.kind:10s}  {e.version}")
    print(f"\n{len(entries)} entries available.")
    return 0


def cmd_install(args, repo: Path) -> int:
    target = _resolve_target(args)
    if target is None:
        print("error: install requires --project PATH or --global", file=sys.stderr)
        return 1

    entries = load_entries(repo)
    model = getattr(args, "model", None)
    dry_run = getattr(args, "dry_run", False)

    for name in args.entries:
        if name not in entries:
            print(f"error: unknown entry '{name}'", file=sys.stderr)
            print(f"available: {', '.join(sorted(entries))}", file=sys.stderr)
            return 1

    state = load_state(target)
    selected = set(state.get("entries", {})) | set(args.entries)
    _apply_selection(args, entries, target, selected, set(args.entries), model, model is not None, dry_run, reconcile=True)
    action = "Would install" if dry_run else "Installed"
    for name in args.entries:
        print(f"{action} {name}")
    return 0


def cmd_update(args, repo: Path) -> int:
    target = _resolve_target(args)
    if target is None:
        print("error: update requires --project PATH or --global", file=sys.stderr)
        return 1

    entries = load_entries(repo)
    model = getattr(args, "model", None)
    dry_run = getattr(args, "dry_run", False)

    state = load_state(target)
    installed_names = set(state.get("entries", {}))
    names = list(args.entries) if args.entries else sorted(installed_names)

    for name in names:
        if name not in entries:
            print(f"error: unknown entry '{name}'", file=sys.stderr)
            return 1
    missing = set(names) - installed_names
    if missing:
        raise StateError("cannot update entries that are not installed: " + ", ".join(sorted(missing)))

    if not names:
        print("No installed entries to update.")
        return 0

    selected = installed_names
    _apply_selection(args, entries, target, selected, set(names), model, model is not None, dry_run, reconcile=True)
    action = "Would update" if dry_run else "Updated"
    for name in names:
        print(f"{action} {name}")
    return 0


def cmd_uninstall(args, repo: Path) -> int:
    target = _resolve_target(args)
    if target is None:
        print("error: uninstall requires --project PATH or --global", file=sys.stderr)
        return 1

    dry_run = getattr(args, "dry_run", False)
    state = load_state(target)
    requested = set(args.entries)
    installed_names = set(state.get("entries", {}))
    missing = requested - installed_names
    if missing:
        raise StateError("cannot uninstall entries that are not installed: " + ", ".join(sorted(missing)))

    replacements = _remaining_runtime(target, state, requested)
    op = plan_uninstall_many(target, requested, state, replacements=replacements)
    apply_operation(op, dry_run=dry_run)
    action = "Would uninstall" if dry_run else "Uninstalled"
    for name in args.entries:
        print(f"{action} {name}")
    return 0


def _remaining_runtime(target: Path, state: dict, removed: set[str]) -> dict[str, bytes]:
    """Derive the next runtime file only from persisted settings."""
    runtime_rel = "awesome-agency/runtime.json"
    remaining = set(state.get("entries", {})) - removed
    runtime_path = target / runtime_rel
    if not remaining:
        return {}
    if not runtime_path.is_file():
        raise StateError(f"managed runtime settings missing: {runtime_path}")
    try:
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StateError(f"cannot read managed runtime settings: {runtime_path}") from error
    entries = [item for item in runtime.get("entries", []) if item.get("name") not in removed]
    if {item.get("name") for item in entries} != remaining:
        raise StateError("managed runtime settings do not match persisted installed entries")
    contributions = {}
    complete = all(isinstance(item.get("contribution"), dict) for item in entries)
    if complete:
        for item in entries:
            contributions.update(item["contribution"].get("mcp", {}))
    else:
        contributions = dict(runtime.get("mcp", {}))
    runtime["entries"] = entries
    runtime["mcp"] = contributions
    return {runtime_rel: (json.dumps(runtime, indent=2, sort_keys=True) + "\n").encode("utf-8")}


def _apply_selection(
    args,
    entries,
    target: Path,
    selected: set[str],
    changed: set[str],
    model: str | None,
    model_supplied: bool,
    dry_run: bool,
    *,
    reconcile: bool,
) -> None:
    """Render the complete selected set and apply content/config atomically."""
    state = load_state(target)
    desired_all: dict[str, bytes] = {}
    owners_all: dict[str, list[str]] = {}
    modes_all: dict[str, int] = {}
    versions: dict[str, str] = {}
    models: dict[str, str | None] = {}
    kinds: dict[str, str] = {}
    selected_entries = []

    for name in sorted(selected):
        if name not in entries:
            raise StateError(f"installed entry source is no longer available: {name}")
        entry = entries[name]
        selected_entries.append(entry)
        entry_model = model if model_supplied and name in changed else state.get("entries", {}).get(name, {}).get("model")
        desired = render_entry(entry, target, entry_model)
        modes = get_rendered_file_modes()
        for rel, data in desired.items():
            if rel in desired_all and desired_all[rel] != data:
                raise StateError(f"collision: selected entries disagree on {rel}")
            desired_all[rel] = data
            owners_all.setdefault(rel, [])
            if name not in owners_all[rel]:
                owners_all[rel].append(name)
            modes_all[rel] = modes.get(rel, 0o644)
        versions[name] = entry.version
        models[name] = entry_model
        kinds[name] = entry.kind

    contribution = render_configuration(
        selected_entries,
        target,
        getattr(args, "project", None),
    )
    for rel, data in contribution.items():
        desired_all[rel] = data
        owners_all[rel] = list(sorted(selected))
        modes_all[rel] = 0o644

    op = plan_operation(
        target,
        desired_all,
        owners_all,
        file_modes=modes_all,
        entry_versions=versions,
        entry_models=models,
        entry_kinds=kinds,
        reconcile=reconcile,
    )
    apply_operation(
        op,
        dry_run=dry_run,
        entry_versions=versions,
        entry_models=models,
        entry_kinds=kinds,
    )


def _add_target_selectors(parser: argparse.ArgumentParser) -> None:
    targets = parser.add_mutually_exclusive_group(required=True)
    targets.add_argument("--project", type=Path, default=None)
    targets.add_argument("--global", dest="global_target", action="store_true")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="opencode-install",
        description="Install awesome-agency marketplace entries into OpenCode.",
    )

    sub = parser.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="List available entries")
    p_list.add_argument("--repo", type=Path, default=None)

    p_install = sub.add_parser("install", help="Install entries")
    p_install.add_argument("entries", nargs="+")
    p_install.add_argument("--repo", type=Path, default=None)
    _add_target_selectors(p_install)
    p_install.add_argument("--model", type=str, default=None)
    p_install.add_argument("--dry-run", action="store_true")

    p_update = sub.add_parser("update", help="Update entries")
    p_update.add_argument("entries", nargs="*")
    p_update.add_argument("--repo", type=Path, default=None)
    _add_target_selectors(p_update)
    p_update.add_argument("--model", type=str, default=None)
    p_update.add_argument("--dry-run", action="store_true")

    p_uninstall = sub.add_parser("uninstall", help="Uninstall entries")
    p_uninstall.add_argument("entries", nargs="+")
    p_uninstall.add_argument("--repo", type=Path, default=None)
    _add_target_selectors(p_uninstall)
    p_uninstall.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 1

    repo = getattr(args, "repo", None) or _default_repo()

    try:
        if args.command == "list":
            return cmd_list(args, repo)
        elif args.command == "install":
            return cmd_install(args, repo)
        elif args.command == "update":
            return cmd_update(args, repo)
        elif args.command == "uninstall":
            return cmd_uninstall(args, repo)
    except AgencyError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
