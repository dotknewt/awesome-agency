"""Regression tests for OpenCode distribution checks."""
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
CHECKER_PATH = ROOT / ".github/scripts/check-opencode.py"
spec = importlib.util.spec_from_file_location("check_opencode", CHECKER_PATH)
checker = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(checker)


class CheckerRegressionTests(unittest.TestCase):
    def test_disabled_plugin_proof_requires_local_plugin_and_disabled_server(self):
        plugin = Path("/tmp/project/.opencode/plugins/awesome-agency.js")
        output = json.dumps({
            "plugin": [plugin.as_uri()],
            "mcp": {"synthetic": {"enabled": False}},
        }).encode()
        checker.assert_debug_config(output, plugin, "synthetic")
        with self.assertRaises(RuntimeError):
            checker.assert_debug_config(
                json.dumps({"plugin": [plugin.as_uri()], "mcp": {"synthetic": {"enabled": True}}}).encode(),
                plugin,
                "synthetic",
            )

    def test_missing_entry_fails_post_install_assertion(self):
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / ".opencode"
            (target / "awesome-agency").mkdir(parents=True)
            state = {"entries": {"one": {}}, "files": {}}
            runtime = {"entries": [{"name": "one"}]}
            (target / "awesome-agency/state.json").write_text(json.dumps(state), encoding="utf-8")
            (target / "awesome-agency/runtime.json").write_text(json.dumps(runtime), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                checker.assert_installed_artifacts(target, {"one", "two"}, set())

    def test_real_hook_command_args_and_matcher_drift_fail_original_fingerprint(self):
        matrix = json.loads((ROOT / ".github/host-compat.json").read_text(encoding="utf-8"))
        declaration = next(
            item for item in matrix["opencode"]["hook_declarations"]
            if item["source"] == "plugins/vault-memory/hooks/hooks.json"
        )
        source = ROOT / declaration["source"]
        original = json.loads(source.read_text(encoding="utf-8"))

        mutations = {
            "matcher": lambda data: data["hooks"]["PreToolUse"][0].update(matcher="DifferentTool"),
            "command": lambda data: data["hooks"]["PreToolUse"][0]["hooks"][0].update(command="different-command"),
            "args": lambda data: data["hooks"]["PreToolUse"][0]["hooks"][0]["args"].__setitem__(0, "different-script.mjs"),
        }
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            mutated_path = root / declaration["source"]
            mutated_path.parent.mkdir(parents=True)
            (root / declaration["adapter"]).parent.mkdir(parents=True)
            (root / declaration["adapter"]).write_text("adapter", encoding="utf-8")
            coverage = root / declaration["coverage"][0]
            coverage.parent.mkdir(parents=True)
            coverage.write_text(declaration["test_names"][0], encoding="utf-8")
            metadata = {"hook_declarations": [{**declaration}]}

            for field, mutate in mutations.items():
                changed = json.loads(json.dumps(original))
                mutate(changed)
                mutated_path.write_text(json.dumps(changed), encoding="utf-8")
                with patch.object(checker, "ROOT", root), self.assertRaisesRegex(
                    RuntimeError, "hook declaration changed"
                ):
                    checker.check_hook_declaration(mutated_path, metadata)

    def test_new_hook_event_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "hooks/hooks.json"
            source.parent.mkdir()
            source.write_text(json.dumps({"hooks": {"NewEvent": []}}), encoding="utf-8")
            entry = SimpleNamespace(name="test", source=root)
            metadata = {
                "hook_adapters": {},
                "hook_fields": [],
                "mcp_server_fields": [],
                "runtime_adapter": "adapter.js",
                "hook_declarations": [{
                    "source": "hooks/hooks.json",
                    "sha256": checker.hashlib.sha256(source.read_bytes()).hexdigest(),
                    "adapter": "adapter.js",
                    "coverage": [],
                    "test_names": [],
                }],
            }
            (root / "adapter.js").write_text("adapter", encoding="utf-8")
            with patch.object(checker, "ROOT", root), self.assertRaisesRegex(
                RuntimeError, "unsupported future hook event 'NewEvent'"
            ):
                checker.check_source_constructs(entry, metadata)


if __name__ == "__main__":
    unittest.main()
