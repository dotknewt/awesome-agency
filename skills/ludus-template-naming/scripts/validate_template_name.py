#!/usr/bin/env python3
"""Validate canonical Ludus template basenames and built names."""

from __future__ import annotations

import argparse
import re
import sys


LINUX_FAMILIES = {"ubuntu", "debian", "kali"}
ARCHITECTURES = {"x64", "arm64"}
LINUX_ROLES = {"desktop", "server"}
ALLOWED_NAME = re.compile(r"^[a-z0-9._-]+$")
RELEASE = re.compile(r"^[0-9]+(?:\.[0-9]+)*(?:_[a-z0-9]*[a-z][a-z0-9]*)*$")
QUALIFIER = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
LOCALE = re.compile(r"^[a-z]{2}$")


def has_hyphenated_numeric_release(fields: list[str]) -> bool:
    release_start = 2 if fields[:2] == ["windows", "server"] else 1
    architecture_index = next(
        (index for index in range(release_start, len(fields)) if fields[index] in ARCHITECTURES),
        None,
    )
    return (
        architecture_index is not None
        and architecture_index - release_start >= 2
        and all(field.isdigit() for field in fields[release_start:architecture_index])
    )


def validate_name(name: str) -> str | None:
    if not name.isascii() or name != name.lower():
        return "lowercase ASCII"
    if not name or not ALLOWED_NAME.fullmatch(name):
        return "name must use lowercase ASCII letters, digits, dots, underscores, and hyphens"
    if any(separator in name for separator in ("--", "__", "..")):
        return "repeated separator"

    suffix_count = name.count("-template")
    if suffix_count:
        if suffix_count != 1 or not name.endswith("-template"):
            return "-template is allowed only as one terminal suffix"
        name = name.removesuffix("-template")
        if "-template" in name:
            return "built name must contain exactly one terminal -template suffix"

    fields = name.split("-")
    if not fields or fields[0] not in LINUX_FAMILIES | {"windows"}:
        return "unknown OS family; expected ubuntu, debian, kali, windows, or windows-server"
    if has_hyphenated_numeric_release(fields):
        return "numeric release components must use dots"

    if fields[0] in LINUX_FAMILIES:
        if len(fields) < 5:
            return "expected Linux shape: <os>-<release>-<arch>-<role>[-<qualifier>...]-<locale>"
        release, arch, role = fields[1:4]
        qualifiers = fields[4:-1]
    elif len(fields) > 1 and fields[1] == "server":
        if len(fields) < 5:
            return "expected Windows Server shape: windows-server-<release>-<arch>[-<qualifier>...]-<locale>"
        release, arch = fields[2:4]
        role = None
        qualifiers = fields[4:-1]
    else:
        if len(fields) < 4:
            return "expected Windows client shape: windows-<release>-<arch>[-<qualifier>...]-<locale>"
        release, arch = fields[1:3]
        role = None
        qualifiers = fields[3:-1]

    if role is not None and role not in LINUX_ROLES:
        return "Linux role must be desktop or server"

    locale = fields[-1]
    if not LOCALE.fullmatch(locale):
        return "final locale must be two lowercase letters"
    if not RELEASE.fullmatch(release):
        if re.fullmatch(r"[0-9]+(?:_[0-9]+)+", release):
            return "numeric release components must use dots"
        return "release must start with digits and use dots for numeric parts or underscores for semantic alphanumeric parts"
    if arch not in ARCHITECTURES:
        return "architecture must be x64 or arm64"
    ambiguous_qualifier = ["no", "security", "updates"]
    if any(
        qualifiers[index : index + 3] == ambiguous_qualifier
        for index in range(len(qualifiers) - 2)
    ):
        return "write the multiword qualifier as no_security_updates"
    if any(not QUALIFIER.fullmatch(qualifier) for qualifier in qualifiers):
        return "qualifiers must use lowercase alphanumerics with underscores inside a field"
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate canonical Ludus template basenames and built names."
    )
    parser.add_argument("names", metavar="NAME", nargs="+")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    failed = False
    for name in args.names:
        reason = validate_name(name)
        if reason is None:
            print(f"valid: {name}")
        else:
            print(f"invalid: {name}: {reason}", file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
