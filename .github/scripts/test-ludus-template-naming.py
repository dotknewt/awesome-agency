#!/usr/bin/env python3
"""Exercise the Ludus template-name validator as an external command."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "skills" / "ludus-template-naming" / "scripts" / "validate_template_name.py"

CANONICAL_BASENAMES = (
    "ubuntu-24.04.2-x64-desktop-no",
    "debian-13.2-x64-server-no",
    "kali-2024.4-x64-desktop-no",
    "windows-11-22h2-x64-enterprise-no",
    "windows-server-2019-x64-no-security-updates-us",
    "windows-server-2019-x64-no-security-updates-no",
)

VALID_NAMES = tuple(
    name
    for basename in CANONICAL_BASENAMES
    for name in (basename, f"{basename}-template")
) + (
    "windows-11-22h2-arm64-us",
    "windows-11-22h2-x64-tpm-us",
    "ubuntu-24.04-x64-desktop-us",
    "ubuntu-24.04-beta-x64-server-us",
    "windows-server-2022-r2-arm64-no-security-updates-tpm-us",
    "flare-vm-no",
    "flare-vm-no-template",
    "flare-vm-us",
    "flare-vm-us-template",
)

INVALID_NAMES = {
    "ubuntu-24.04.2-x64-no-desktop": "Linux role must be desktop or server",
    "debian-13-2-x64-server-no": "numeric release components must use dots",
    "debian-13-2-0-x64-server-us": "numeric release components must use dots",
    "windows-11-22-x64-us": "numeric release components must use dots",
    "windows-server-20-19-x64-us": "numeric release components must use dots",
    "windows-server-2019-x64-no-security-updates": "final locale must be two lowercase letters",
    "windows-server-2019-x64-no_security_updates": "name must use lowercase ASCII letters, digits, dots, and hyphens",
    "Ubuntu-24.04.2-x64-desktop-no": "lowercase ASCII",
    "ubuntu/24.04.2-x64-desktop-us": "name must use lowercase ASCII letters, digits, dots, and hyphens",
    "fedora-41-x64-desktop-us": "unknown OS family",
    "ubuntu-24.04.2-amd64-desktop-us": "architecture must be x64 or arm64",
    "ubuntu-24.04.2-x64-workstation-us": "Linux role must be desktop or server",
    "ubuntu-24.04.2--x64-desktop-us": "repeated separator",
    "windows-11__22h2-x64-us": "name must use lowercase ASCII letters, digits, dots, and hyphens",
    "ubuntu-24..04-x64-desktop-us": "repeated separator",
    "ubuntu-24.04.2-x64-desktop_us": "name must use lowercase ASCII letters, digits, dots, and hyphens",
    "ubuntu-24.04.2-x64-desktop-us-template-template": "-template is allowed only as one terminal suffix",
    "ubuntu-template-24.04.2-x64-desktop-us": "-template is allowed only as one terminal suffix",
    "windows-11-22h2-x64-enterprise-no-extra": "final locale must be two lowercase letters",
    "debian-13_2-x64-server-us": "name must use lowercase ASCII letters, digits, dots, and hyphens",
    "windows-11-22h2-x64-tpm-bypas-us": "banned naming field: tpm-bypas",
    "windows-11-22h2-x64-tpm-bypass-us": "banned naming field: tpm-bypass",
    "windows-11-22h2-x64-standard-us": "banned naming field: standard",
    "windows-11-22h2-x64-standard-evaluation-us": "banned naming field: standard",
    "windows-11-22h2-x64-desktop-experience-us": "banned naming field: desktop-experience",
    "flare-vm": "FLARE names must use flare-vm-<locale>",
    "flare-vm-usa": "FLARE names must use flare-vm-<locale>",
    "flare-vm-US": "lowercase ASCII",
    "flare-vm-no-extra": "FLARE names must use flare-vm-<locale>",
    "flare_vm-no": "name must use lowercase ASCII letters, digits, dots, and hyphens",
    "flare-vm-no-template-template": "-template is allowed only as one terminal suffix",
    "windows-11-23h2-x64-enterprise-flare-vm-no": "banned naming field: flare-vm",
    "windows-11-23h2-x64-enterprise-flare-vm-no-template": "banned naming field: flare-vm",
    "windows-server-2022-x64-tpm-bypas-us": "banned naming field: tpm-bypas",
    "windows-server-2022-x64-tpm-bypass-us": "banned naming field: tpm-bypass",
    "windows-server-2022-x64-standard-us": "banned naming field: standard",
    "windows-server-2022-x64-standard-evaluation-us": "banned naming field: standard",
    "windows-server-2022-x64-desktop-experience-us": "banned naming field: desktop-experience",
    "windows-11_22h2-x64-us": "name must use lowercase ASCII letters, digits, dots, and hyphens",
    "windows-server-2019-x64-no_security_updates-us": "name must use lowercase ASCII letters, digits, dots, and hyphens",
    "windows-11-22h2-amd64-us": "architecture must be x64 or arm64",
    "windows-11-22h2-x64-enterprise.us": "final locale must be two lowercase letters",
    "windows-11-22h2-x64-enterprise.foo-us": "qualifiers must use lowercase alphanumerics",
    "windows-11-22h2-123-x64-us": "release must start with digits",
    "windows-foo-x64-us": "release must start with digits",
    "ubuntu-24.-04-x64-desktop-us": "DNS labels must start and end with a letter or digit",
    "ubuntu-24-.04-x64-desktop-us": "DNS labels must start and end with a letter or digit",
    ".ubuntu-24.04-x64-desktop-us": "DNS labels must start and end with a letter or digit",
    "ubuntu-24.04-x64-desktop-us.": "DNS labels must start and end with a letter or digit",
    "-ubuntu-24.04-x64-desktop-us": "DNS labels must start and end with a letter or digit",
    "ubuntu-24.04-x64-desktop-us-": "DNS labels must start and end with a letter or digit",
}

# Single-label Windows base: 18 fixed characters; suffix adds 9.
LABEL_LIMIT_BASE = "windows-11-x64-" + "a" * 45 + "-us"
SUFFIX_LIMIT_BASE = "windows-11-x64-" + "a" * 36 + "-us"
# Dotted numeric releases permit total-length tests with every label <= 63.
# 7 + 56 + 1 + 63 + 1 + 63 + 1 + 38 + 14 = 244; suffix makes 253.
TOTAL_LIMIT_BASE = "ubuntu-" + ".".join("1" * size for size in (56, 63, 63, 38)) + "-x64-server-us"
assert len(LABEL_LIMIT_BASE) == 63
assert len(SUFFIX_LIMIT_BASE + "-template") == 63
assert len(TOTAL_LIMIT_BASE + "-template") == 253


def run_validator(*names: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), "--", *names],
        check=False,
        capture_output=True,
        text=True,
    )


def main() -> int:
    for name in VALID_NAMES + (
        LABEL_LIMIT_BASE,
        SUFFIX_LIMIT_BASE,
        SUFFIX_LIMIT_BASE + "-template",
        TOTAL_LIMIT_BASE,
        TOTAL_LIMIT_BASE + "-template",
        TOTAL_LIMIT_BASE.replace("-x64", "111111111-x64"),
    ):
        result = run_validator(name)
        assert result.returncode == 0, (name, result.stdout, result.stderr)
        assert f"valid: {name}\n" == result.stdout
        assert result.stderr == ""

    for name, reason in INVALID_NAMES.items():
        result = run_validator(name)
        assert result.returncode != 0, name
        assert result.stdout == ""
        assert f"invalid: {name}: {reason}" in result.stderr, (name, result.stderr)

    for name, reason in (
        (LABEL_LIMIT_BASE.replace("-us", "a-us"), "DNS labels must not exceed 63 characters"),
        (LABEL_LIMIT_BASE + "-template", "DNS labels must not exceed 63 characters"),
        (SUFFIX_LIMIT_BASE.replace("-us", "a-us") + "-template", "DNS labels must not exceed 63 characters"),
        (TOTAL_LIMIT_BASE.replace("-x64", "1-x64") + "-template", "DNS name must not exceed 253 characters"),
        (TOTAL_LIMIT_BASE.replace("-x64", "1111111111-x64"), "DNS name must not exceed 253 characters"),
    ):
        result = run_validator(name)
        assert result.returncode != 0, name
        assert reason in result.stderr, (name, result.stderr)

    mixed = run_validator(VALID_NAMES[0], *tuple(INVALID_NAMES)[:2], VALID_NAMES[2])
    assert mixed.returncode != 0
    assert f"valid: {VALID_NAMES[0]}" in mixed.stdout
    assert f"valid: {VALID_NAMES[2]}" in mixed.stdout
    for name in tuple(INVALID_NAMES)[:2]:
        assert f"invalid: {name}:" in mixed.stderr

    missing = run_validator()
    assert missing.returncode != 0
    assert "usage:" in missing.stderr.lower()

    print("Ludus template naming checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
