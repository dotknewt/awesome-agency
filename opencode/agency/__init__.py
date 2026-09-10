from __future__ import annotations

"""Core types and interfaces for the OpenCode marketplace installer."""

from dataclasses import dataclass
from pathlib import Path


STATE_SCHEMA_VERSION = 2


@dataclass(frozen=True)
class Entry:
    """A concrete installable entry from `marketplace.json`."""

    name: str
    source: Path
    version: str
    kind: str
    manifest: dict


@dataclass(frozen=True)
class Operation:
    """Planned filesystem + ownership operation.

    The command layer applies these operations atomically and can roll them back.
    """

    target: Path
    writes: dict[str, bytes]
    deletes: list[str]
    file_modes: dict[str, int]
    owners_after: dict[str, list[str]]
    owners_before: dict[str, list[str]]
    remove_entries: set[str] | None = None


class AgencyError(Exception):
    """Base class for installer exceptions."""


class CatalogError(AgencyError):
    """Raised when the generated marketplace cannot be read or interpreted."""


class ContentError(AgencyError):
    """Raised for invalid content trees, bad symlinks, or conversion failures."""


class StateError(AgencyError):
    """Raised for ownership/state collisions and apply failures."""
