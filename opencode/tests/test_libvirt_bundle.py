"""Installed-package and documentation contract checks for libvirt-toolkit."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INSTALLER = ROOT / "opencode" / "install.py"
BUNDLE = ROOT / "plugins" / "libvirt-toolkit"
GUEST_ACCESS_SKILL = ROOT / "skills" / "guest-access"
REFERENCE = ROOT / "skills" / "libvirt-vms" / "references" / "ubuntu-template.md"
SERVER_README = BUNDLE / "mcp" / "libvirt" / "README.md"
WORKFLOW = ROOT / ".github" / "workflows" / "validate.yml"


class LibvirtBundlePackagingTests(unittest.TestCase):
    def test_installed_bundle_survives_temporary_source_removal(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source-copy"
            bundle = source / "plugins" / "libvirt-toolkit"
            bundle.parent.mkdir(parents=True)
            shutil.copytree(BUNDLE, bundle, symlinks=False)
            guest_access_skill = source / "skills" / "guest-access"
            guest_access_skill.parent.mkdir(parents=True)
            shutil.copytree(GUEST_ACCESS_SKILL, guest_access_skill, symlinks=False)
            (source / ".claude-plugin").mkdir()
            (source / ".claude-plugin" / "marketplace.json").write_text(
                json.dumps({
                    "name": "awesome-agency",
                    "plugins": [
                        {
                            "name": "libvirt-toolkit",
                            "description": "test copy",
                            "source": "./plugins/libvirt-toolkit",
                        },
                        {
                            "name": "guest-access",
                            "description": "test copy",
                            "version": "1.0.0",
                            "source": "./skills/guest-access",
                            "strict": False,
                        },
                    ],
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
                "UV_CACHE_DIR": str(root / "uv-cache"),
                "UV_PYTHON_INSTALL_DIR": str(root / "uv-python"),
                "UV_TOOL_DIR": str(root / "uv-tools"),
                "UV_NO_CONFIG": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
            })
            installed = subprocess.run(
                [
                    sys.executable,
                    str(INSTALLER),
                    "install",
                    "libvirt-toolkit",
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

            target = project / ".opencode"
            runtime = json.loads(
                (target / "awesome-agency" / "runtime.json").read_text(encoding="utf-8")
            )
            command = runtime["mcp"]["libvirt"]["command"]
            self.assertEqual(command[0:3], ["uv", "run", "--script"])
            self.assertEqual(
                command[3],
                "{package_root:awesome-agency/packages/bundles/libvirt-toolkit}/mcp/libvirt/server.py",
            )
            package = (
                target / "awesome-agency" / "packages" / "bundles" / "libvirt-toolkit"
            )
            copied_server = package / "mcp" / "libvirt" / "server.py"
            copied_core = package / "mcp" / "libvirt" / "libvirt_mcp"
            self.assertTrue(copied_server.is_file())
            self.assertTrue(copied_core.is_dir())
            self.assertFalse(copied_server.is_symlink())
            self.assertIn('"mcp==2.2.0"', copied_server.read_text(encoding="utf-8"))

            placeholder = "{package_root:awesome-agency/packages/bundles/libvirt-toolkit}"
            resolved_command = [
                item.replace(placeholder, str(package)) for item in command
            ]
            self.assertEqual(
                resolved_command,
                ["uv", "run", "--script", str(copied_server)],
            )

            # Only the disposable source copy is removed; the real checkout is untouched.
            shutil.rmtree(source)
            self.assertFalse(source.exists())
            provider_reference = package / "skills" / "libvirt-vms" / "references" / "guest-access.md"
            self.assertTrue(provider_reference.is_file())
            self.assertFalse(provider_reference.is_symlink())
            debian_reference = package / "skills" / "libvirt-vms" / "references" / "debian-template.md"
            self.assertTrue(debian_reference.is_file())
            self.assertFalse(debian_reference.is_symlink())
            cachyos_reference = package / "skills" / "libvirt-vms" / "references" / "cachyos-template.md"
            self.assertTrue(cachyos_reference.is_file())
            self.assertFalse(cachyos_reference.is_symlink())
            bundled_guest_skill = package / "skills" / "guest-access" / "SKILL.md"
            bundled_guest_reference = package / "skills" / "guest-access" / "references" / "ssh-workflow.md"
            self.assertTrue(bundled_guest_skill.is_file())
            self.assertTrue(bundled_guest_reference.is_file())
            self.assertFalse(bundled_guest_skill.is_symlink())
            self.assertFalse(bundled_guest_reference.is_symlink())
            discovered_guest_skill = target / "skills" / "guest-access" / "SKILL.md"
            self.assertTrue(discovered_guest_skill.is_file())
            self.assertFalse(discovered_guest_skill.is_symlink())
            self.assertIn("name: guest-access", discovered_guest_skill.read_text(encoding="utf-8"))
            self.assertEqual(
                [entry["name"] for entry in runtime["entries"]],
                ["guest-access", "libvirt-toolkit"],
            )
            launched = subprocess.run(
                [*resolved_command, "--help"],
                cwd=project,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(launched.returncode, 0, launched.stderr)
            self.assertIn("--state-dir", launched.stdout)

            imported = subprocess.run(
                [
                    "uv", "run", "--isolated", "--with", "mcp==2.2.0",
                    "python", "-c",
                    (
                        "import pathlib,sys; sys.path.insert(0, sys.argv[1]); "
                        "import libvirt_mcp.server; "
                        "print(pathlib.Path(libvirt_mcp.server.__file__).resolve())"
                    ),
                    str(copied_server.parent),
                ],
                cwd=project,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(imported.returncode, 0, imported.stderr)
            self.assertEqual(
                Path(imported.stdout.strip()),
                (copied_core / "server.py").resolve(),
            )


class LibvirtDocumentationContractTests(unittest.TestCase):
    def test_ubuntu_reference_preserves_seeded_autoinstall_command(self):
        reference = REFERENCE.read_text(encoding="utf-8")
        command = """virt-install --connect qemu:///session --name ubuntu-dev-template \\
  --cpu host-passthrough --vcpus=2,maxvcpus=8 \\
  --memory=8192,currentMemory=4096 \\
  --location="$HOME/Archive/iso/ubuntu-26.04-desktop-amd64.iso,kernel=casper/vmlinuz,initrd=casper/initrd" \\
  --extra-args="autoinstall" \\
  --disk size=32,format=qcow2 \\
  --disk path="$HOME/Archive/iso/ubuntu-dev-seed.iso",device=cdrom,readonly=on \\
  --os-variant=ubuntu26.04 --noautoconsole --wait=-1"""
        self.assertIn(command, reference)
        self.assertIn("NoCloud", reference)
        self.assertIn("cidata", reference)
        self.assertIn("user-data", reference)
        self.assertIn("meta-data", reference)

    def test_server_launch_examples_use_explicit_script_mode(self):
        readme = SERVER_README.read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"uv run (?!--script|--isolated)", readme))
        self.assertIn("uv run --script server.py", readme)
        self.assertIn("uv run --script /absolute/path/to/libvirt/server.py", readme)

    def test_ci_declares_uv_for_installed_bundle_acceptance(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("astral-sh/setup-uv@", workflow)


if __name__ == "__main__":
    unittest.main()
