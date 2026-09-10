#!/usr/bin/env python3
"""Validate canonical Ludus template basenames and built names."""

from __future__ import annotations

import argparse
import re
import sys


LINUX_FAMILIES = {"ubuntu", "debian", "kali"}
ARCHITECTURES = {"x64", "arm64"}
LINUX_ROLES = {"desktop", "server"}
ALLOWED_NAME = re.compile(r"^[a-z0-9.-]+$")
RELEASE = re.compile(r"^[0-9]+(?:\.[0-9]+)*(?:-[a-z0-9]*[a-z][a-z0-9]*)*$")
QUALIFIER = re.compile(r"^[a-z0-9]+$")
LOCALE = re.compile(r"^[a-z]{2}$")
BANNED_QUALIFIERS = {
    "flare-vm",
    "tpm-bypas",
    "tpm-bypass",
    "standard",
    "standard-evaluation",
    "desktop-experience",
}


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
        return "name must use lowercase ASCII letters, digits, dots, and hyphens"
    if any(separator in name for separator in ("--", "..")):
        return "repeated separator"

    # Validate the supplied name before stripping the built suffix: it consumes
    # both label and total DNS length budget.
    if len(name) > 253:
        return "DNS name must not exceed 253 characters"
    for label in name.split("."):
        if len(label) > 63:
            return "DNS labels must not exceed 63 characters"
        if not label or not label[0].isalnum() or not label[-1].isalnum():
            return "DNS labels must start and end with a letter or digit"

    suffix_count = name.count("-template")
    if suffix_count:
        if suffix_count != 1 or not name.endswith("-template"):
            return "-template is allowed only as one terminal suffix"
        name = name.removesuffix("-template")
        if "-template" in name:
            return "built name must contain exactly one terminal -template suffix"

    if name.startswith("flare-vm"):
        if re.fullmatch(r"flare-vm-[a-z]{2}", name):
            return None
        return "FLARE names must use flare-vm-<locale>"

    fields = name.split("-")
    if not fields or fields[0] not in LINUX_FAMILIES | {"windows"}:
        return "unknown OS family; expected ubuntu, debian, kali, windows, or windows-server"
    if has_hyphenated_numeric_release(fields):
        return "numeric release components must use dots"

    release_start = 2 if fields[:2] == ["windows", "server"] else 1
    architecture_index = next(
        (index for index in range(release_start, len(fields)) if fields[index] in ARCHITECTURES),
        None,
    )
    if architecture_index is None:
        return "architecture must be x64 or arm64"
    release = "-".join(fields[release_start:architecture_index])
    remaining = fields[architecture_index + 1:]

    if fields[0] in LINUX_FAMILIES:
        if len(remaining) < 2:
            return "expected Linux shape: <os>-<release>-<arch>-<role>[-<qualifier>...]-<locale>"
        role = remaining[0]
        qualifiers = remaining[1:-1]
    elif len(fields) > 1 and fields[1] == "server":
        if not remaining:
            return "expected Windows Server shape: windows-server-<release>-<arch>[-<qualifier>...]-<locale>"
        role = None
        qualifiers = remaining[:-1]
    else:
        if not remaining:
            return "expected Windows client shape: windows-<release>-<arch>[-<qualifier>...]-<locale>"
        role = None
        qualifiers = remaining[:-1]

    if role is not None and role not in LINUX_ROLES:
        return "Linux role must be desktop or server"

    locale = fields[-1]
    if not LOCALE.fullmatch(locale):
        return "final locale must be two lowercase letters"
    if not RELEASE.fullmatch(release):
        return "release must start with digits and use dots for numeric parts or hyphens for semantic alphanumeric parts"
    # Hyphens also join multiword qualifiers. Match banned phrases on token
    # boundaries so spelling them as separate fields cannot evade exclusion.
    banned_qualifier = next(
        (
            banned
            for index in range(len(qualifiers))
            for end in range(index + 1, len(qualifiers) + 1)
            if (banned := "-".join(qualifiers[index:end])) in BANNED_QUALIFIERS
        ),
        None,
    )
    if banned_qualifier is not None:
        return f"banned naming field: {banned_qualifier}"
    if any(not QUALIFIER.fullmatch(qualifier) for qualifier in qualifiers):
        return "qualifiers must use lowercase alphanumerics joined by hyphens"
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
