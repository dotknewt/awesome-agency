from __future__ import annotations

"""Ownership manifest, preflight, and transactional filesystem operations.

State schema (version 2):
    {
      "version": 2,
      "entries": {
        "<entry-name>": {
          "version": "...",
          "model": "..." or null,
          "kind": "skill"|"agent"|"bundle"|"command"
        }
      },
      "files": {
        "<rel-path>": {
          "sha256": "<hex>",
          "mode": 0o755,
          "owners": ["entry-a", "entry-b"]
        }
      }
    }
"""

import hashlib
import json
import os
import tempfile
from pathlib import Path

from . import Operation, StateError


STATE_FILE = "awesome-agency/state.json"
STATE_SCHEMA_VERSION = 2


# ---------------------------------------------------------------------------
# Hashing
# ---------------------------------------------------------------------------

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# State load / save
# ---------------------------------------------------------------------------

def _empty_state() -> dict:
    return {"version": STATE_SCHEMA_VERSION, "entries": {}, "files": {}}


def load_state(target: Path) -> dict:
    fp = target / STATE_FILE
    if not fp.is_file():
        return _empty_state()
    try:
        data = json.loads(fp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StateError(f"cannot read installer state: {fp}") from error
    if not isinstance(data, dict):
        raise StateError(f"invalid installer state: {fp}")
    if data.get("version") != STATE_SCHEMA_VERSION:
        raise StateError(f"unsupported installer state version: {data.get('version')!r}")
    return data


def save_state(target: Path, state: dict) -> None:
    fp = target / STATE_FILE
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(
        json.dumps(state, indent=2, sort_keys=True),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Backward-compat owners helpers (used by tests / CLI that still call them)
# ---------------------------------------------------------------------------

def load_owners(target: Path) -> dict[str, list[str]]:
    state = load_state(target)
    return {
        rel: list(info["owners"])
        for rel, info in state.get("files", {}).items()
        if info.get("owners")
    }


def save_owners(target: Path, owners: dict[str, list[str]]) -> None:
    state = load_state(target)
    files = state.setdefault("files", {})
    for rel, owner_list in owners.items():
        if rel in files:
            files[rel]["owners"] = list(owner_list)
        else:
            files[rel] = {"sha256": "", "mode": 0o644, "owners": list(owner_list)}
    save_state(target, state)


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------

def _validate_relative_path(rel: str) -> None:
    p = Path(rel)
    if p.is_absolute():
        raise StateError(f"absolute paths not allowed: {rel}")
    if ".." in p.parts:
        raise StateError(f"traversing paths not allowed: {rel}")


def _check_ancestor_symlinks(target: Path, rel: str) -> None:
    dest = target / rel
    current = target
    while current != dest.parent:
        next_part = dest.relative_to(current).parts[0]
        candidate = current / next_part
        if candidate.is_symlink():
            raise StateError(f"destination ancestor is a symlink: {candidate}")
        current = candidate


# ---------------------------------------------------------------------------
# Recompute desired union for ALL selected entries
# ---------------------------------------------------------------------------

def recompute_desired(
    target: Path,
    selected: dict[str, dict],
    models: dict[str, str | None] | None = None,
) -> tuple[dict[str, bytes], dict[str, int], dict[str, list[str]]]:
    """Recompute the full desired state from all selected entries.

    ``selected`` maps entry_name -> {
        "kind": str,
        "rendered": dict[str, bytes],  # rel-path -> content
        "modes": dict[str, int],       # rel-path -> mode
    }

    Returns (desired_bytes, desired_modes, desired_owners).
    """
    del target, models

    desired_bytes: dict[str, bytes] = {}
    desired_modes: dict[str, int] = {}
    desired_owners: dict[str, list[str]] = {}

    for entry_name, info in selected.items():
        rendered = info["rendered"]
        modes = info.get("modes", {})
        for rel, data in rendered.items():
            desired_bytes[rel] = data
            desired_modes[rel] = modes.get(rel, 0o644)
            desired_owners.setdefault(rel, [])
            if entry_name not in desired_owners[rel]:
                desired_owners[rel].append(entry_name)

    return desired_bytes, desired_modes, desired_owners


# ---------------------------------------------------------------------------
# Plan operation
# ---------------------------------------------------------------------------

def plan_operation(
    target: Path,
    desired: dict[str, bytes],
    owners: dict[str, list[str]],
    *,
    file_modes: dict[str, int] | None = None,
    entry_versions: dict[str, str] | None = None,
    entry_models: dict[str, str | None] | None = None,
    entry_kinds: dict[str, str] | None = None,
    reconcile: bool = False,
) -> Operation:
    """Plan an install/update operation with full hash-based preflight.

    Validates paths, checks ancestor symlinks, and detects collisions.
    """
    for rel in desired:
        _validate_relative_path(rel)
        _check_ancestor_symlinks(target, rel)

    state = load_state(target)
    recorded_files = state.get("files", {})

    writes: dict[str, bytes] = {}
    resolved_modes: dict[str, int] = dict(file_modes) if file_modes else {}
    owners_after: dict[str, list[str]] = {}
    owners_before: dict[str, list[str]] = {}
    deletes: list[str] = []
    old_bytes: dict[str, bytes] = {}
    old_modes: dict[str, int] = {}

    for rel in desired:
        dest = target / rel
        if dest.is_symlink():
            raise StateError(f"destination is a symlink: {dest}")

        desired_data = desired[rel]
        desired_hash = sha256_bytes(desired_data)
        recorded = recorded_files.get(rel)
        on_disk = dest.exists() and dest.is_file()

        if on_disk:
            disk_hash = sha256_file(dest)
            disk_data = dest.read_bytes()
            disk_mode = dest.stat().st_mode & 0o7777

            if recorded and recorded.get("owners"):
                recorded_hash = recorded.get("sha256", "")
                if disk_hash != recorded_hash:
                    # File changed on disk since last install
                    if disk_hash != desired_hash:
                        raise StateError(
                            f"conflict: {rel} changed on disk since it was recorded"
                        )
                    # Disk matches desired even though recorded differs — adopt
                    owners_before[rel] = list(recorded.get("owners", []))
                    owners_after[rel] = list(dict.fromkeys((recorded.get("owners", []) if recorded else []) + owners.get(rel, [])))
                    writes[rel] = desired_data
                    old_bytes[rel] = disk_data
                    old_modes[rel] = disk_mode
                    resolved_modes.setdefault(rel, disk_mode)
                else:
                    # Disk matches recorded — safe to replace
                    owners_before[rel] = list(recorded.get("owners", []))
                    owners_after[rel] = list(dict.fromkeys((recorded.get("owners", []) if recorded else []) + owners.get(rel, [])))
                    writes[rel] = desired_data
                    old_bytes[rel] = disk_data
                    old_modes[rel] = disk_mode
            else:
                # Unowned file on disk
                if disk_hash == desired_hash:
                    # Bytes identical — may adopt
                    owners_before[rel] = []
                    owners_after[rel] = list(owners.get(rel, []))
                    writes[rel] = desired_data
                    old_bytes[rel] = disk_data
                    old_modes[rel] = disk_mode
                    resolved_modes.setdefault(rel, disk_mode)
                else:
                    raise StateError(
                        f"collision: {rel} exists on disk but is unowned "
                        f"and differs from desired content"
                    )
        else:
            # File doesn't exist on disk — clean install
            owners_before[rel] = list(
                recorded.get("owners", []) if recorded else []
            )
            owners_after[rel] = list(dict.fromkeys((recorded.get("owners", []) if recorded else []) + owners.get(rel, [])))
            writes[rel] = desired_data

    if reconcile:
        selected_names = {owner for file_owners in owners.values() for owner in file_owners}
        for rel, recorded in recorded_files.items():
            previous = set(recorded.get("owners", []))
            if not previous.intersection(selected_names) or rel in desired:
                continue
            dest = target / rel
            if dest.is_symlink():
                raise StateError(f"destination is a symlink: {dest}")
            if dest.is_file() and sha256_file(dest) == recorded.get("sha256"):
                deletes.append(rel)
                owners_before[rel] = list(recorded.get("owners", []))
                owners_after[rel] = [o for o in owners_before[rel] if o not in selected_names]

    return Operation(
        target=target,
        writes=writes,
        deletes=deletes,
        file_modes=resolved_modes,
        owners_after=owners_after,
        owners_before=owners_before,
    )


# ---------------------------------------------------------------------------
# Plan uninstall
# ---------------------------------------------------------------------------

def plan_uninstall(
    target: Path,
    entry_name: str,
    installed_files: dict[str, bytes],
    state: dict | None = None,
) -> Operation:
    """Plan removal of one entry, keeping files shared with other owners."""
    return plan_uninstall_many(
        target,
        {entry_name},
        state,
        installed_files=set(installed_files),
    )


def plan_uninstall_many(
    target: Path,
    entry_names: set[str],
    state: dict | None = None,
    *,
    installed_files: set[str] | None = None,
    replacements: dict[str, bytes] | None = None,
) -> Operation:
    """Plan one atomic source-independent removal of several entries."""
    if state is None:
        state = load_state(target)
    recorded_files = state.get("files", {})
    replacements = replacements or {}

    writes: dict[str, bytes] = {}
    deletes: list[str] = []
    file_modes: dict[str, int] = {}
    owners_after: dict[str, list[str]] = {}
    owners_before: dict[str, list[str]] = {}

    for rel, recorded in recorded_files.items():
        if installed_files is not None and rel not in installed_files:
            continue
        before_owners = list(recorded.get("owners", []))
        if not set(before_owners).intersection(entry_names):
            continue
        _validate_relative_path(rel)
        _check_ancestor_symlinks(target, rel)
        dest = target / rel
        if dest.is_symlink():
            raise StateError(f"destination is a symlink: {dest}")
        owners_before[rel] = before_owners
        remaining = [owner for owner in before_owners if owner not in entry_names]
        owners_after[rel] = remaining
        if remaining and rel in replacements:
            desired = replacements[rel]
            if dest.is_file():
                disk_hash = sha256_file(dest)
                if disk_hash != recorded.get("sha256") and disk_hash != sha256_bytes(desired):
                    raise StateError(f"conflict: {rel} changed on disk since it was recorded")
            writes[rel] = desired
            file_modes[rel] = int(recorded.get("mode", 0o644))
        elif not remaining:
            if dest.is_file() and sha256_file(dest) != recorded.get("sha256"):
                continue
            deletes.append(rel)

    return Operation(
        target=target,
        writes=writes,
        deletes=deletes,
        file_modes=file_modes,
        owners_after=owners_after,
        owners_before=owners_before,
        remove_entries=set(entry_names),
    )


# ---------------------------------------------------------------------------
# Apply operation (atomic staging + rollback)
# ---------------------------------------------------------------------------

def apply_operation(
    op: Operation,
    *,
    dry_run: bool = False,
    entry_versions: dict[str, str] | None = None,
    entry_models: dict[str, str | None] | None = None,
    entry_kinds: dict[str, str] | None = None,
    remove_entries: set[str] | None = None,
) -> None:
    """Apply a planned operation atomically.

    1. Stage all new bytes + new state into a temp dir.
    2. Snapshot old files that will be replaced.
    3. Atomic os.replace each staged file.
    4. On failure, restore old bytes/modes and old state.
    """
    if dry_run:
        return

    target = op.target
    old_state = load_state(target)

    # Snapshot old bytes and modes for rollback
    snap_bytes: dict[str, bytes] = {}
    snap_modes: dict[str, int] = {}
    snap_state_content: bytes | None = None

    state_fp = target / STATE_FILE
    if state_fp.exists():
        snap_state_content = state_fp.read_bytes()

    for rel in op.writes:
        fp = target / rel
        if fp.exists() and fp.is_file():
            snap_bytes[rel] = fp.read_bytes()
            snap_modes[rel] = fp.stat().st_mode & 0o7777

    deleted_snap: dict[str, bytes] = {}
    deleted_mode_snap: dict[str, int] = {}
    for rel in op.deletes:
        fp = target / rel
        if fp.exists():
            deleted_snap[rel] = fp.read_bytes()
            deleted_mode_snap[rel] = fp.stat().st_mode & 0o7777

    # Build new state
    new_state = {
        "version": STATE_SCHEMA_VERSION,
        "entries": dict(old_state.get("entries", {})),
        "files": dict(old_state.get("files", {})),
    }

    # Update entry metadata
    if entry_versions:
        for name, ver in entry_versions.items():
            new_state["entries"].setdefault(name, {})
            new_state["entries"][name]["version"] = ver
    if entry_models:
        for name, model in entry_models.items():
            new_state["entries"].setdefault(name, {})
            new_state["entries"][name]["model"] = model
    if entry_kinds:
        for name, kind in entry_kinds.items():
            new_state["entries"].setdefault(name, {})
            new_state["entries"][name]["kind"] = kind
    for name in (remove_entries or op.remove_entries or set()):
        new_state["entries"].pop(name, None)

    # Update file records, including preserved edited files whose ownership changed.
    files = new_state["files"]
    for rel, owners in op.owners_after.items():
        if rel in files:
            files[rel]["owners"] = list(owners)
    for rel, data in op.writes.items():
        files[rel] = {
            "sha256": sha256_bytes(data),
            "mode": op.file_modes.get(rel, 0o644),
            "owners": list(op.owners_after.get(rel, [])),
        }

    for rel in op.deletes:
        if rel in files:
            remaining_owners = op.owners_after.get(rel, [])
            if remaining_owners:
                files[rel]["owners"] = remaining_owners
            else:
                del files[rel]

    # Stage writes
    staged: list[Path] = []
    created_dirs: set[Path] = set()
    try:
        for rel, data in op.writes.items():
            fp = target / rel
            missing: list[Path] = []
            parent = fp.parent
            while parent != target and not parent.exists():
                missing.append(parent)
                parent = parent.parent
            fp.parent.mkdir(parents=True, exist_ok=True)
            created_dirs.update(missing)
            # Write to temp file then atomic replace
            fd, tmp = tempfile.mkstemp(dir=fp.parent, suffix=".tmp")
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(data)
                os.replace(tmp, fp)
            except Exception:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
                raise
            staged.append(fp)
            if rel in op.file_modes:
                fp.chmod(op.file_modes[rel])

        # Delete files
        for rel in op.deletes:
            fp = target / rel
            if fp.exists() or fp.is_symlink():
                fp.unlink()

        # Write new state atomically
        state_parent_missing = not state_fp.parent.exists()
        state_fp.parent.mkdir(parents=True, exist_ok=True)
        if state_parent_missing:
            created_dirs.add(state_fp.parent)
        state_fd, state_tmp = tempfile.mkstemp(
            dir=state_fp.parent, suffix=".tmp", prefix=".state-"
        )
        try:
            with os.fdopen(state_fd, "w") as f:
                json.dump(new_state, f, indent=2, sort_keys=True)
            os.replace(state_tmp, state_fp)
        except Exception:
            try:
                os.unlink(state_tmp)
            except OSError:
                pass
            raise

    except Exception as rollback_exc:
        # Rollback: restore old bytes/modes
        for rel, data in snap_bytes.items():
            fp = target / rel
            try:
                fp.write_bytes(data)
                fp.chmod(snap_modes[rel])
            except OSError:
                pass

        for rel, data in deleted_snap.items():
            fp = target / rel
            try:
                fp.parent.mkdir(parents=True, exist_ok=True)
                fp.write_bytes(data)
                fp.chmod(deleted_mode_snap[rel])
            except OSError:
                pass

        # Rollback state file
        if snap_state_content is not None:
            try:
                state_fp.write_bytes(snap_state_content)
            except OSError:
                pass
        elif state_fp.exists():
            try:
                state_fp.unlink()
            except OSError:
                pass

        # Remove any files we created that shouldn't exist
        for fp in staged:
            rel = fp.relative_to(target).as_posix()
            if rel not in snap_bytes and fp.exists():
                try:
                    fp.unlink()
                except OSError:
                    pass

        for directory in sorted(created_dirs, key=lambda path: len(path.parts), reverse=True):
            try:
                directory.rmdir()
            except OSError:
                pass

        raise StateError(
            f"apply failed, rolled back: {rollback_exc}"
        ) from rollback_exc
