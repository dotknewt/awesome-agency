"""Standalone installed-package checks for the guest-access skill."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "opencode" / "install.py"
SKILL = ROOT / "skills" / "guest-access"


class GuestAccessPackagingTests(unittest.TestCase):
    def test_installed_skill_and_reference_survive_temporary_source_removal(self):
        self.assertTrue(SKILL.is_dir(), "guest-access skill source is missing")

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source-copy"
            copied_skill = source / "skills" / "guest-access"
            copied_skill.parent.mkdir(parents=True)
            shutil.copytree(SKILL, copied_skill, symlinks=False)
            (source / ".claude-plugin").mkdir()
            (source / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps({
                    "name": "awesome-agency",
                    "plugins": [{
                        "name": "guest-access",
                        "description": "test copy",
                        "version": "1.0.0",
                        "source": "./skills/guest-access",
                        "strict": False,
                    }],
                }),
                encoding="utf-8",
            )
            project = root / "project"
            env = {
                key: value
                for key, value in os.environ.items()
                if key != "HOME" and not key.startswith(("XDG_", "UV_"))
            }
            env.update({
                "HOME": str(root / "home"),
                "XDG_CONFIG_HOME": str(root / "xdg-config"),
                "XDG_CACHE_HOME": str(root / "xdg-cache"),
                "XDG_DATA_HOME": str(root / "xdg-data"),
                "XDG_STATE_HOME": str(root / "xdg-state"),
                "PYTHONDONTWRITEBYTECODE": "1",
            })
            installed = subprocess.run(
                [
                    sys.executable,
                    str(INSTALLER),
                    "install",
                    "guest-access",
                    "--repo",
                    str(source),
                    "--project",
                    str(project),
                ],
                cwd=ROOT,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(installed.returncode, 0, installed.stderr)

            shutil.rmtree(source)
            self.assertFalse(source.exists())

            target = project / ".opencode"
            public_skill = target / "skills" / "guest-access" / "SKILL.md"
            public_reference = (
                target / "skills" / "guest-access" / "references" / "ssh-workflow.md"
            )
            self.assertTrue(public_skill.is_file())
            self.assertTrue(public_reference.is_file())
            self.assertFalse(public_skill.is_symlink())
            self.assertFalse(public_reference.is_symlink())
            self.assertIn("name: guest-access", public_skill.read_text(encoding="utf-8"))
            self.assertIn("# SSH Workflow", public_reference.read_text(encoding="utf-8"))

            runtime = json.loads(
                (target / "awesome-agency" / "runtime.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                [entry["name"] for entry in runtime["entries"]],
                ["guest-access"],
            )


if __name__ == "__main__":
    unittest.main()
