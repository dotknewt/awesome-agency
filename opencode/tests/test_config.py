"""Focused tests for installer-owned OpenCode configuration."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agency import Entry, StateError
from agency.config import (
    PLUGIN_PATH,
    RUNTIME_AGENCY_PATH,
    RUNTIME_PATH,
    RUNTIME_VAULT_PATH,
    render_configuration,
)
import install as installer


SDD_PATHS = {
    "skills/subagent-model-policy/SKILL.md",
    "agents/sdd-worker.md",
    "agents/sdd-reviewer.md",
    "awesome-agency/runtime/subagent-dispatch.ts",
}


def _entry(name: str, source: Path, kind: str = "bundle") -> Entry:
    return Entry(name, source, "1.0.0", kind, {})


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self._xdg = tempfile.mkdtemp()
        self._xdg_patch = mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": self._xdg})
        self._xdg_patch.start()

    def tearDown(self):
        self._xdg_patch.stop()
        shutil.rmtree(self._xdg, ignore_errors=True)

    def _repo(self, root: Path) -> Path:
        repo = root / "repo"
        (repo / ".claude-plugin").mkdir(parents=True)
        bundles = []
        for name in ("one", "two"):
            source = repo / "plugins" / name / ".claude-plugin"
            source.mkdir(parents=True)
            (source / "plugin.json").write_text(
                json.dumps({"name": name, "version": "1.0.0", "description": name}),
                encoding="utf-8",
            )
            bundles.append({"name": name, "source": f"./plugins/{name}"})
        (repo / ".claude-plugin" / "marketplace.json").write_text(
            json.dumps({"name": "awesome-agency", "plugins": bundles}), encoding="utf-8"
        )
        return repo

    def test_fresh_configuration_has_runtime_entries_and_plugin(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "bundle"
            source.mkdir()
            result = render_configuration([_entry("bundle", source)], root / ".opencode", root)

        self.assertIn(RUNTIME_PATH, result)
        self.assertIn(PLUGIN_PATH, result)
        runtime = json.loads(result[RUNTIME_PATH].decode())
        self.assertEqual(runtime["version"], 1)
        self.assertEqual(runtime["entries"][0]["name"], "bundle")
        self.assertEqual(runtime["entries"][0]["package_root"], "awesome-agency/packages/bundles/bundle")
        self.assertEqual(runtime["entries"][0]["version"], "1.0.0")
        self.assertEqual(runtime["entries"][0]["source"], str(source.resolve()))
        self.assertIn("contribution", runtime["entries"][0])
        plugin = result[PLUGIN_PATH].decode()
        self.assertIn("import { AwesomeAgency }", plugin)
        self.assertIn("import SubagentDispatch", plugin)
        self.assertIn("export default async function", plugin)
        self.assertNotIn("export { AwesomeAgency }", plugin)

    def test_automatic_sdd_preserves_native_permissions(self):
        from agency.content import _parse_frontmatter

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "bundle"
            source.mkdir()
            result = render_configuration([_entry("bundle", source)], root / ".opencode", root)

        self.assertIn("skills/subagent-model-policy/SKILL.md", result)
        self.assertIn("awesome-agency/runtime/subagent-dispatch.ts", result)
        self.assertNotIn("plugins/subagent-dispatch.ts", result)
        for role in ("worker", "reviewer"):
            front, _ = _parse_frontmatter(result[f"agents/sdd-{role}.md"].decode())
            self.assertEqual(front["model"], "openai/gpt-5.6-sol")
            self.assertEqual(front["permission"]["task"], "deny")
            self.assertEqual(front["permission"]["subagent_dispatch"], "deny")
            if role == "reviewer":
                self.assertEqual(front["permission"]["edit"], "deny")
                self.assertEqual(front["permission"]["bash"], "deny")

    def test_automatic_sdd_sources_are_package_relative_and_required(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "synthetic-repo" / "bundle"
            source.mkdir(parents=True)
            original_read_bytes = Path.read_bytes

            def fail_sdd_worker(path):
                if path.as_posix().endswith("sdd/agents/sdd-worker.md"):
                    raise OSError("missing packaged source")
                return original_read_bytes(path)

            with mock.patch.object(Path, "read_bytes", fail_sdd_worker):
                with self.assertRaisesRegex(StateError, "cannot read automatic SDD sources"):
                    render_configuration([_entry("bundle", source)], root / ".opencode", root)

    def test_empty_configuration_does_not_emit_automatic_sdd(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            result = render_configuration([], root / ".opencode", root)
        self.assertTrue(SDD_PATHS.isdisjoint(result))

    def test_unrelated_user_config_and_mcp_are_not_owned(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "opencode.json").write_text(
                json.dumps({"username": "user", "mcp": {"other": {"enabled": False}}}),
                encoding="utf-8",
            )
            source = root / "bundle"
            source.mkdir()
            result = render_configuration([_entry("bundle", source)], root / ".opencode", root)

        self.assertEqual(
            set(result),
            {RUNTIME_PATH, RUNTIME_AGENCY_PATH, RUNTIME_VAULT_PATH, PLUGIN_PATH} | SDD_PATHS,
        )
        self.assertNotIn(b"username", result[RUNTIME_PATH])

    def test_jsonc_and_competing_locations_are_read_without_rewrite(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            jsonc = root / "opencode.jsonc"
            jsonc.write_text('{ // user comment\n "mcp": {}\n}\n', encoding="utf-8")
            source = root / "bundle"
            source.mkdir()
            result = render_configuration([_entry("bundle", source)], root / ".opencode", root)
            self.assertEqual(jsonc.read_text(encoding="utf-8"), '{ // user comment\n "mcp": {}\n}\n')
            self.assertIn(RUNTIME_PATH, result)

            (root / "opencode.json").write_text("{}\n", encoding="utf-8")
            with self.assertRaises(StateError):
                render_configuration([_entry("bundle", source)], root / ".opencode", root)

    def test_explicit_mcp_precedes_managed_mcp(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "bundle"
            source.mkdir()
            (source / "opencode").mkdir()
            (source / "opencode" / "opencode.json").write_text(
                json.dumps({"mcp": {"demo": {"type": "local", "command": ["demo"]}}}),
                encoding="utf-8",
            )
            (root / "opencode.json").write_text(
                json.dumps({"mcp": {"demo": {"type": "local", "command": ["other"]}}}),
                encoding="utf-8",
            )
            result = render_configuration([_entry("bundle", source)], root / ".opencode", root)
        runtime = json.loads(result[RUNTIME_PATH].decode())
        self.assertNotIn("demo", runtime["mcp"])

    def test_global_and_project_mcp_precedence_is_merged_read_only(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            xdg = root / "xdg"
            global_dir = xdg / "opencode"
            global_dir.mkdir(parents=True)
            (global_dir / "opencode.json").write_text(
                json.dumps({"mcp": {"same": {"type": "remote", "url": "global"}, "global": {"type": "remote", "url": "g"}}}),
                encoding="utf-8",
            )
            (root / "opencode.json").write_text(
                json.dumps({"mcp": {"same": {"type": "remote", "url": "project"}, "project": {"type": "remote", "url": "p"}}}),
                encoding="utf-8",
            )
            source = root / "bundle"
            (source / "opencode").mkdir(parents=True)
            (source / "opencode" / "opencode.json").write_text(
                json.dumps({"mcp": {"same": {"type": "remote", "url": "managed"}, "managed": {"type": "remote", "url": "m"}}}),
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(xdg)}):
                result = render_configuration([_entry("bundle", source)], root / ".opencode", root)
            runtime = json.loads(result[RUNTIME_PATH].decode())

        self.assertNotIn("same", runtime["mcp"])
        self.assertNotIn("global", runtime["mcp"])
        self.assertNotIn("project", runtime["mcp"])
        self.assertIn("managed", runtime["mcp"])

    def test_global_only_mcp_precedes_managed_for_project_install(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            xdg = root / "xdg"
            (xdg / "opencode").mkdir(parents=True)
            (xdg / "opencode" / "opencode.json").write_text(
                json.dumps({"mcp": {"same": {"type": "remote", "url": "global"}}}),
                encoding="utf-8",
            )
            source = root / "bundle"
            (source / "opencode").mkdir(parents=True)
            (source / "opencode" / "opencode.json").write_text(
                json.dumps({"mcp": {"same": {"type": "remote", "url": "managed"}}}),
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(xdg)}):
                result = render_configuration([_entry("bundle", source)], root / ".opencode", root)
            runtime = json.loads(result[RUNTIME_PATH].decode())
        self.assertNotIn("same", runtime["mcp"])

    def test_environment_interpolation_and_project_relative_vault(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "vault-memory"
            source.mkdir()
            (source / ".mcp.json").write_text(
                json.dumps({
                    "mcpServers": {
                        "obsidian": {
                            "type": "stdio",
                            "command": "npx",
                            "args": ["-y", "mcpvault", "${CLAUDE_PROJECT_DIR:-.}/vault/subdir"],
                            "env": {"TOKEN": "${TOKEN}"},
                        }
                    }
                }),
                encoding="utf-8",
            )
            result = render_configuration([_entry("vault-memory", source)], root / ".opencode", None)
            runtime = json.loads(result[RUNTIME_PATH].decode())
            server = runtime["mcp"]["obsidian"]

        self.assertEqual(server["type"], "local")
        self.assertEqual(server["command"], ["npx", "-y", "mcpvault", "{project}/vault/subdir"])
        self.assertEqual(server["environment"], {"TOKEN": "{env:TOKEN}"})

    def test_quoted_paths_are_preserved_and_ludus_fragment_is_supported(self):
        with tempfile.TemporaryDirectory(prefix="agency project ") as raw:
            root = Path(raw)
            source = root / "ludus"
            (source / "opencode").mkdir(parents=True)
            (source / "opencode" / "opencode.json").write_text(
                json.dumps({"mcp": {"ludus": {"type": "local", "command": ["docker", "run", "image with spaces"]}}}),
                encoding="utf-8",
            )
            result = render_configuration([_entry("ludus-toolkit", source)], root / ".opencode", root)
            runtime = json.loads(result[RUNTIME_PATH].decode())

        self.assertEqual(runtime["mcp"]["ludus"]["command"][-1], "image with spaces")

    def test_package_root_and_runtime_settings_are_stable_for_global_install(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "bundle"
            source.mkdir()
            result = render_configuration([_entry("bundle", source)], root / ".config" / "opencode", None)
            runtime = json.loads(result[RUNTIME_PATH].decode())

        self.assertEqual(runtime["project_context"], "runtime")
        self.assertEqual(runtime["entries"][0]["package_root"], "awesome-agency/packages/bundles/bundle")

    def test_agent_micro_entry_uses_installed_source_identity(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "issue-filer"
            source.mkdir()
            result = render_configuration(
                [_entry("issue-filer-agent", source, "agent")], root / ".opencode", root
            )
            runtime = json.loads(result[RUNTIME_PATH].decode())
        self.assertEqual(runtime["entries"][0]["package_root"], "awesome-agency/packages/agents/issue-filer")

    def test_runtime_and_automatic_sdd_share_ownership_across_partial_lifecycle(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = self._repo(root)
            project = root / "project"
            project.mkdir()
            self.assertEqual(installer.main(["install", "one", "--repo", str(repo), "--project", str(project)]), 0)
            self.assertEqual(installer.main(["install", "two", "--repo", str(repo), "--project", str(project)]), 0)
            state = json.loads((project / ".opencode" / "awesome-agency" / "state.json").read_text())
            for rel in (RUNTIME_PATH, RUNTIME_AGENCY_PATH, RUNTIME_VAULT_PATH, PLUGIN_PATH, *SDD_PATHS):
                self.assertEqual(set(state["files"][rel]["owners"]), {"one", "two"})

            self.assertEqual(installer.main(["uninstall", "one", "--repo", str(repo), "--project", str(project)]), 0)
            runtime = json.loads((project / ".opencode" / RUNTIME_PATH).read_text())
            self.assertEqual([entry["name"] for entry in runtime["entries"]], ["two"])
            self.assertTrue((project / ".opencode" / PLUGIN_PATH).is_file())
            state = json.loads((project / ".opencode" / "awesome-agency" / "state.json").read_text())
            for rel in SDD_PATHS:
                self.assertEqual(state["files"][rel]["owners"], ["two"])
                self.assertTrue((project / ".opencode" / rel).is_file())

            shutil.rmtree(repo)
            self.assertEqual(installer.main(["uninstall", "two", "--repo", str(repo), "--project", str(project)]), 0)
            self.assertFalse((project / ".opencode" / RUNTIME_PATH).exists())
            self.assertFalse((project / ".opencode" / RUNTIME_AGENCY_PATH).exists())
            self.assertFalse((project / ".opencode" / RUNTIME_VAULT_PATH).exists())
            self.assertFalse((project / ".opencode" / PLUGIN_PATH).exists())
            for rel in SDD_PATHS:
                self.assertFalse((project / ".opencode" / rel).exists())

    def test_install_dry_run_leaves_no_target_files(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = self._repo(root)
            project = root / "project"
            project.mkdir()
            self.assertEqual(installer.main([
                "install", "one", "--repo", str(repo), "--project", str(project), "--dry-run",
            ]), 0)
            self.assertFalse((project / ".opencode").exists())

    def test_update_introduces_automatic_sdd_into_old_installation(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = self._repo(root)
            project = root / "project"
            project.mkdir()

            def old_configuration(entries, target, project_root):
                rendered = render_configuration(entries, target, project_root)
                rendered = {rel: data for rel, data in rendered.items() if rel not in SDD_PATHS}
                rendered[PLUGIN_PATH] = (
                    b'// Generated by awesome-agency. Do not edit; it is transaction-owned.\n'
                    b'export { AwesomeAgency } from "../awesome-agency/runtime/agency.js"\n'
                )
                return rendered

            with mock.patch.object(installer, "render_configuration", side_effect=old_configuration):
                self.assertEqual(installer.main([
                    "install", "one", "--repo", str(repo), "--project", str(project),
                ]), 0)
            target = project / ".opencode"
            self.assertFalse(any((target / rel).exists() for rel in SDD_PATHS))

            self.assertEqual(installer.main([
                "update", "one", "--repo", str(repo), "--project", str(project),
            ]), 0)
            for rel in SDD_PATHS:
                self.assertTrue((target / rel).is_file())

    def test_conflicting_user_agent_refuses_install_without_other_writes(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = self._repo(root)
            project = root / "project"
            conflict = project / ".opencode" / "agents" / "sdd-worker.md"
            conflict.parent.mkdir(parents=True)
            conflict.write_bytes(b"user agent\n")

            self.assertEqual(installer.main([
                "install", "one", "--repo", str(repo), "--project", str(project),
            ]), 1)
            self.assertEqual(conflict.read_bytes(), b"user agent\n")
            self.assertEqual(
                [path.relative_to(project / ".opencode").as_posix() for path in (project / ".opencode").rglob("*") if path.is_file()],
                ["agents/sdd-worker.md"],
            )

    def test_marketplace_runtime_collision_refuses_install_before_writing(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = self._repo(root)
            project = root / "project"
            project.mkdir()
            original = installer.render_entry

            def conflicting_render(entry, target, model):
                rendered = original(entry, target, model)
                rendered["agents/sdd-worker.md"] = b"incompatible marketplace agent\n"
                return rendered

            with mock.patch.object(installer, "render_entry", side_effect=conflicting_render):
                self.assertEqual(installer.main([
                    "install", "one", "--repo", str(repo), "--project", str(project),
                ]), 1)
            self.assertFalse((project / ".opencode").exists())

    def test_generated_hook_resolves_env_paths_and_preserves_user_precedence(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "bundle"
            (source / "opencode").mkdir(parents=True)
            (source / "opencode" / "opencode.json").write_text(
                json.dumps({"mcp": {"managed": {"type": "local", "command": ["run", "${AGENCY_TOKEN}", "${CLAUDE_PLUGIN_ROOT}/catalog"]}, "user": {"type": "remote", "url": "managed"}}}),
                encoding="utf-8",
            )
            target = root / ".opencode"
            rendered = render_configuration([_entry("bundle", source)], target, root)
            for relative, data in rendered.items():
                path = target / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            script = """
const mod = await import(process.argv[1])
const plugin = await mod.AwesomeAgency({ directory: process.argv[2] })
const cfg = { mcp: { user: { type: 'remote', url: 'explicit' } } }
await plugin.config(cfg)
console.log(JSON.stringify(cfg))
"""
            env = dict(os.environ, AGENCY_TOKEN="secret-value")
            result = subprocess.run(
                ["node", "--input-type=module", "-e", script, str(target / RUNTIME_AGENCY_PATH), str(root)],
                check=False,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            config = json.loads(result.stdout)

        self.assertEqual(config["mcp"]["user"]["url"], "explicit")
        self.assertEqual(config["mcp"]["managed"]["command"][1], "secret-value")
        self.assertEqual(config["mcp"]["managed"]["command"][-1], str(target / "awesome-agency/packages/bundles/bundle/catalog"))

    def test_failed_fresh_preflight_does_not_create_target(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = self._repo(root)
            project = root / "project"
            project.mkdir()
            (project / "opencode.json").write_text(
                json.dumps({"mcp": {"one": {"type": "remote", "url": "user"}}}),
                encoding="utf-8",
            )
            (project / "opencode.jsonc").write_text("{}\n", encoding="utf-8")
            self.assertEqual(installer.main(["install", "one", "--repo", str(repo), "--project", str(project)]), 1)
            self.assertFalse((project / ".opencode").exists())

    def test_update_without_model_retains_existing_model_pin(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = self._repo(root)
            project = root / "project"
            project.mkdir()
            self.assertEqual(installer.main(["install", "one", "two", "--model", "openai/test", "--repo", str(repo), "--project", str(project)]), 0)
            self.assertEqual(installer.main(["update", "one", "--repo", str(repo), "--project", str(project)]), 0)
            state = json.loads((project / ".opencode" / "awesome-agency" / "state.json").read_text())
        self.assertEqual(state["entries"]["one"]["model"], "openai/test")
        self.assertEqual(state["entries"]["two"]["model"], "openai/test")

    def test_multi_uninstall_is_one_source_independent_operation(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo = self._repo(root)
            project = root / "project"
            project.mkdir()
            self.assertEqual(installer.main(["install", "one", "two", "--repo", str(repo), "--project", str(project)]), 0)
            shutil.rmtree(repo)
            with mock.patch.object(installer, "apply_operation", wraps=installer.apply_operation) as apply:
                self.assertEqual(installer.main(["uninstall", "one", "two", "--repo", str(repo), "--project", str(project)]), 0)
            self.assertEqual(apply.call_count, 1)
            self.assertFalse((project / ".opencode" / RUNTIME_PATH).exists())
            self.assertFalse((project / ".opencode" / PLUGIN_PATH).exists())


if __name__ == "__main__":
    unittest.main()
