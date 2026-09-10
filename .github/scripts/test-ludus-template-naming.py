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
    "windows-11_22h2-x64-enterprise-no",
    "windows-server-2019-x64-no_security_updates-us",
    "windows-server-2019-x64-no_security_updates-no",
)

VALID_NAMES = tuple(
    name
    for basename in CANONICAL_BASENAMES
    for name in (basename, f"{basename}-template")
) + (
    "windows-11_22h2-arm64-us",
    "windows-11_22h2-x64-tpm-us",
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
    "windows-server-2019-x64-no-security-updates-us": "write the multiword qualifier as no_security_updates",
    "windows-server-2019-x64-no_security_updates": "final locale must be two lowercase letters",
    "Ubuntu-24.04.2-x64-desktop-no": "lowercase ASCII",
    "ubuntu/24.04.2-x64-desktop-us": "name must use lowercase ASCII letters, digits, dots, underscores, and hyphens",
    "fedora-41-x64-desktop-us": "unknown OS family",
    "ubuntu-24.04.2-amd64-desktop-us": "architecture must be x64 or arm64",
    "ubuntu-24.04.2-x64-workstation-us": "Linux role must be desktop or server",
    "ubuntu-24.04.2--x64-desktop-us": "repeated separator",
    "windows-11__22h2-x64-us": "repeated separator",
    "ubuntu-24..04-x64-desktop-us": "repeated separator",
    "ubuntu-24.04.2-x64-desktop_us": "expected Linux shape",
    "ubuntu-24.04.2-x64-desktop-us-template-template": "-template is allowed only as one terminal suffix",
    "ubuntu-template-24.04.2-x64-desktop-us": "-template is allowed only as one terminal suffix",
    "windows-11_22h2-x64-enterprise-no-extra": "final locale must be two lowercase letters",
    "debian-13_2-x64-server-us": "numeric release components must use dots",
    "windows-11_22h2-x64-tpm_bypas-us": "banned naming field: tpm_bypas",
    "windows-11_22h2-x64-tpm_bypass-us": "banned naming field: tpm_bypass",
    "windows-11_22h2-x64-standard-us": "banned naming field: standard",
    "windows-11_22h2-x64-standard_evaluation-us": "banned naming field: standard_evaluation",
    "windows-11_22h2-x64-desktop_experience-us": "banned naming field: desktop_experience",
    "flare-vm": "FLARE names must use flare-vm-<locale>",
    "flare-vm-usa": "FLARE names must use flare-vm-<locale>",
    "flare-vm-US": "lowercase ASCII",
    "flare-vm-no-extra": "FLARE names must use flare-vm-<locale>",
    "flare_vm-no": "unknown OS family; expected ubuntu, debian, kali, windows, or windows-server",
    "flare-vm-no-template-template": "-template is allowed only as one terminal suffix",
    "windows-11_23h2-x64-enterprise-flare_vm-no_security_updates-tpm_bypass-no": "banned naming field: flare_vm",
    "windows-11_23h2-x64-enterprise-flare_vm-no_security_updates-tpm_bypass-no-template": "banned naming field: flare_vm",
    "windows-server-2022-x64-tpm_bypas-us": "banned naming field: tpm_bypas",
    "windows-server-2022-x64-tpm_bypass-us": "banned naming field: tpm_bypass",
    "windows-server-2022-x64-standard-us": "banned naming field: standard",
    "windows-server-2022-x64-standard_evaluation-us": "banned naming field: standard_evaluation",
    "windows-server-2022-x64-desktop_experience-us": "banned naming field: desktop_experience",
}


def run_validator(*names: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), *names],
        check=False,
        capture_output=True,
        text=True,
    )


def main() -> int:
    for name in VALID_NAMES:
        result = run_validator(name)
        assert result.returncode == 0, (name, result.stdout, result.stderr)
        assert f"valid: {name}\n" == result.stdout
        assert result.stderr == ""

    for name, reason in INVALID_NAMES.items():
        result = run_validator(name)
        assert result.returncode != 0, name
        assert result.stdout == ""
        assert f"invalid: {name}: {reason}" in result.stderr

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
