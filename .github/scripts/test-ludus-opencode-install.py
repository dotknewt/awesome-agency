#!/usr/bin/env python3
"""Exercise the ludus-toolkit OpenCode installer and validate its configs."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[2]
OPENCODE_DIR = ROOT / "plugins" / "ludus-toolkit" / "opencode"
INSTALLER = OPENCODE_DIR / "install.py"
FRAGMENT = OPENCODE_DIR / "opencode.json"
SKILL_SOURCE = ROOT / "plugins" / "ludus-toolkit" / "skills"
SKILL_NAMES = {
    "change-template-input-language",
    "ludus-cli",
    "ludus-environment-guide",
    "ludus-range-config",
    "ludus-template-naming",
    "ludus-troubleshoot",
    "update-os-template",
}


def run_installer(project: Path, *, success: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        [sys.executable, str(INSTALLER), str(project), "--merge-config"],
        check=False,
        capture_output=True,
        text=True,
    )
    if (result.returncode == 0) != success:
        raise AssertionError(
            f"installer returned {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def file_manifest(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def assert_installed(project: Path) -> None:
    skill_root = project / ".opencode" / "skills"
    assert {path.name for path in skill_root.iterdir()} == SKILL_NAMES
    for name in SKILL_NAMES:
        installed = skill_root / name
        assert not installed.is_symlink()
        assert not any(path.is_symlink() for path in installed.rglob("*"))
        assert file_manifest(installed) == file_manifest(SKILL_SOURCE / name)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {Path(sys.argv[0]).name} OPENCode_SCHEMA.json")
    schema = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    validator.validate(json.loads(FRAGMENT.read_text(encoding="utf-8")))

    with tempfile.TemporaryDirectory() as temporary:
        base = Path(temporary)

        clean = base / "clean"
        clean.mkdir()
        run_installer(clean)
        assert_installed(clean)
        installed_validator = (
            clean
            / ".opencode"
            / "skills"
            / "ludus-template-naming"
            / "scripts"
            / "validate_template_name.py"
        )
        source_validator = (
            SKILL_SOURCE
            / "ludus-template-naming"
            / "scripts"
            / "validate_template_name.py"
        )
        assert installed_validator.read_bytes() == source_validator.read_bytes()
        generated = json.loads((clean / "opencode.json").read_text(encoding="utf-8"))
        validator.validate(generated)
        repeat = run_installer(clean)
        assert "7 skill(s) already current" in repeat.stdout
        assert "OpenCode config already current" in repeat.stdout

        preserved = base / "preserved"
        preserved.mkdir()
        original = {
            "$schema": "https://opencode.ai/config.json",
            "username": "ci-user",
            "mcp": {
                "other": {
                    "type": "local",
                    "command": ["other-mcp"],
                    "enabled": False,
                }
            },
        }
        (preserved / "opencode.json").write_text(json.dumps(original), encoding="utf-8")
        run_installer(preserved)
        merged = json.loads((preserved / "opencode.json").read_text(encoding="utf-8"))
        assert merged["username"] == "ci-user"
        assert merged["mcp"]["other"] == original["mcp"]["other"]
        assert merged["mcp"]["ludus"] == json.loads(FRAGMENT.read_text())["mcp"]["ludus"]
        validator.validate(merged)

        skill_conflict = base / "skill-conflict"
        conflict_path = skill_conflict / ".opencode" / "skills" / "ludus-cli"
        conflict_path.mkdir(parents=True)
        (conflict_path / "SKILL.md").write_text("different", encoding="utf-8")
        run_installer(skill_conflict, success=False)
        assert {path.name for path in conflict_path.parent.iterdir()} == {"ludus-cli"}
        assert not (skill_conflict / "opencode.json").exists()

        config_conflict = base / "config-conflict"
        config_conflict.mkdir()
        conflict_config = {"mcp": {"ludus": {"type": "local", "command": ["other"]}}}
        (config_conflict / "opencode.json").write_text(
            json.dumps(conflict_config), encoding="utf-8"
        )
        run_installer(config_conflict, success=False)
        assert not (config_conflict / ".opencode").exists()

        null_config = base / "null-config"
        null_config.mkdir()
        (null_config / "opencode.json").write_text('{"mcp": null}\n', encoding="utf-8")
        run_installer(null_config, success=False)
        assert not (null_config / ".opencode").exists()

        jsonc = base / "jsonc"
        jsonc.mkdir()
        (jsonc / "opencode.jsonc").write_text("{ // keep this comment\n}\n", encoding="utf-8")
        result = run_installer(jsonc, success=False)
        assert "Merge opencode/opencode.json manually" in result.stderr
        assert not (jsonc / ".opencode").exists()

        nested = base / "nested"
        (nested / ".opencode").mkdir(parents=True)
        (nested / ".opencode" / "opencode.json").write_text("{}\n", encoding="utf-8")
        run_installer(nested, success=False)
        assert not (nested / ".opencode" / "skills").exists()

    print("ludus-toolkit OpenCode installation checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
