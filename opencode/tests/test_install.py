"""Behavioral and lifecycle tests for the OpenCode marketplace installer.

Run with:
    python3 -m unittest discover -s opencode/tests -p 'test_install.py' -v
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agency import Entry, Operation, CatalogError, ContentError, StateError
import agency.catalog as catalog_mod
import agency.content as content_mod
import agency.state as state_mod


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_repo(tmp: Path) -> Path:
    repo = tmp / "repo"
    repo.mkdir()
    market = {
        "name": "awesome-agency",
        "plugins": [
            {"name": "bundle-a", "description": "A test bundle", "source": "./plugins/bundle-a"},
            {"name": "bundle-b", "description": "Another bundle", "source": "./plugins/bundle-b"},
            {"name": "skill-alpha", "description": "A skill", "source": "./skills/alpha", "version": "1.0.0", "strict": False},
            {"name": "agent-beta", "description": "An agent", "source": "./agents/beta", "version": "1.0.0", "strict": False, "agents": ["./beta.md"]},
            {"name": "doublecheck", "description": "A second skill", "source": "./skills/doublecheck", "version": "1.0.0", "strict": False},
            {"name": "doublecheck-agent", "description": "A second agent", "source": "./agents/doublecheck-agent", "version": "1.0.0", "strict": False, "agents": ["./doublecheck-agent.md"]},
        ],
    }
    (repo / ".claude-plugin").mkdir(parents=True)
    (repo / ".claude-plugin" / "marketplace.json").write_text(json.dumps(market), encoding="utf-8")

    # bundle-a
    ba = repo / "plugins" / "bundle-a" / ".claude-plugin"
    ba.mkdir(parents=True)
    (ba / "plugin.json").write_text(json.dumps({"name": "bundle-a", "version": "2.1.0", "description": "A test bundle", "agents": ["./agents/helper.md"]}), encoding="utf-8")
    (repo / "plugins" / "bundle-a" / "skills" / "bundled-skill" / "SKILL.md").parent.mkdir(parents=True)
    (repo / "plugins" / "bundle-a" / "skills" / "bundled-skill" / "SKILL.md").write_text("---\nname: bundled-skill\ndescription: In bundle\n---\nBody here.\n", encoding="utf-8")
    (repo / "plugins" / "bundle-a" / "agents" / "helper.md").parent.mkdir(parents=True)
    (repo / "plugins" / "bundle-a" / "agents" / "helper.md").write_text("---\nname: helper\ndescription: Helper agent\nmodel: claude-sonnet-4-20250514\ntools:\n  - Bash\n---\nYou are a helper.\n", encoding="utf-8")

    # bundle-b
    bb = repo / "plugins" / "bundle-b" / ".claude-plugin"
    bb.mkdir(parents=True)
    (bb / "plugin.json").write_text(json.dumps({"name": "bundle-b", "version": "0.3.0", "description": "Another bundle"}), encoding="utf-8")
    (repo / "plugins" / "bundle-b" / "skills" / "bb-skill" / "SKILL.md").parent.mkdir(parents=True)
    (repo / "plugins" / "bundle-b" / "skills" / "bb-skill" / "SKILL.md").write_text("---\nname: bb-skill\ndescription: BB skill\n---\nBody.\n", encoding="utf-8")

    # skill-alpha
    (repo / "skills" / "alpha" / "SKILL.md").parent.mkdir(parents=True)
    (repo / "skills" / "alpha" / "SKILL.md").write_text("---\nname: alpha\ndescription: Alpha skill\ntools:\n  - Read\n  - Read*\n---\nSkill body.\n", encoding="utf-8")

    # agent-beta
    (repo / "agents" / "beta" / "beta.md").parent.mkdir(parents=True)
    (repo / "agents" / "beta" / "beta.md").write_text("---\nname: beta\ndescription: Beta agent\nmodel: claude-haiku-4-5\ntools:\n  - Bash\n---\nAgent body.\n", encoding="utf-8")

    (repo / "skills" / "doublecheck" / "SKILL.md").parent.mkdir(parents=True)
    (repo / "skills" / "doublecheck" / "SKILL.md").write_text("---\nname: doublecheck\ndescription: Second skill\n---\nSecond skill body.\n", encoding="utf-8")
    (repo / "agents" / "doublecheck-agent" / "doublecheck-agent.md").parent.mkdir(parents=True)
    (repo / "agents" / "doublecheck-agent" / "doublecheck-agent.md").write_text("---\nname: doublecheck-agent\ndescription: Second agent\nmodel: claude-haiku-4-5\n---\nSecond agent body.\n", encoding="utf-8")

    return repo


class _InstallerTestCase(unittest.TestCase):
    """Base class with shared setup for installer tests."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._xdg_patch = mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.tmp / "xdg")})
        self._xdg_patch.start()
        self.repo = _make_repo(self.tmp)
        self.target = self.tmp / "target"
        self.target.mkdir()
        self.entries = catalog_mod.load_entries(self.repo)

    def tearDown(self):
        self._xdg_patch.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _install(self, entry_name, model=None):
        entry = self.entries[entry_name]
        desired = content_mod.render_entry(entry, self.target, model)
        modes = content_mod.get_rendered_file_modes()
        owners = {k: [entry_name] for k in desired}
        versions = {entry_name: entry.version}
        models = {entry_name: model}
        kinds = {entry_name: entry.kind}
        op = state_mod.plan_operation(
            self.target, desired, owners,
            file_modes=modes, entry_versions=versions,
            entry_models=models, entry_kinds=kinds,
        )
        state_mod.apply_operation(
            op, entry_versions=versions,
            entry_models=models, entry_kinds=kinds,
        )
        return desired

    def _uninstall(self, entry_name):
        state = state_mod.load_state(self.target)
        installed = {
            rel: info for rel, info in state["files"].items()
            if entry_name in info.get("owners", [])
        }
        op = state_mod.plan_uninstall(self.target, entry_name, installed, state)
        state_mod.apply_operation(op, remove_entries={entry_name})


# ===========================================================================
# Catalog
# ===========================================================================

class TestCatalog(_InstallerTestCase):

    def test_all_published_entries_selectable(self):
        self.assertEqual(set(self.entries.keys()), {"bundle-a", "bundle-b", "skill-alpha", "agent-beta", "doublecheck", "doublecheck-agent"})

    def test_bundle_version_from_plugin_json(self):
        self.assertEqual(self.entries["bundle-a"].version, "2.1.0")
        self.assertEqual(self.entries["bundle-b"].version, "0.3.0")

    def test_entry_kind_inferred(self):
        self.assertEqual(self.entries["skill-alpha"].kind, "skill")
        self.assertEqual(self.entries["agent-beta"].kind, "agent")
        self.assertEqual(self.entries["bundle-a"].kind, "bundle")

    def test_draft_entries_excluded(self):
        repo = self.tmp / "repo_draft"
        repo.mkdir()
        market = {
            "name": "test",
            "plugins": [
                {"name": "draft-foo", "description": "Draft", "source": "./skills/foo", "version": "0.1.0"},
                {"name": "bar", "description": "Good", "source": "./skills/bar", "version": "1.0.0"},
            ],
        }
        (repo / ".claude-plugin").mkdir()
        (repo / ".claude-plugin" / "marketplace.json").write_text(json.dumps(market))
        (repo / "skills" / "foo" / "SKILL.md").parent.mkdir(parents=True)
        (repo / "skills" / "foo" / "SKILL.md").write_text("---\nname: foo\ndescription: f\n---\n")
        (repo / "skills" / "bar" / "SKILL.md").parent.mkdir(parents=True)
        (repo / "skills" / "bar" / "SKILL.md").write_text("---\nname: bar\ndescription: b\n---\n")
        entries = catalog_mod.load_entries(repo)
        self.assertNotIn("draft-foo", entries)
        self.assertIn("bar", entries)

    def test_absolute_source_rejected(self):
        repo = self.tmp / "abs"
        repo.mkdir()
        market = {"name": "t", "plugins": [{"name": "x", "source": "/etc/passwd", "version": "1.0"}]}
        (repo / ".claude-plugin").mkdir()
        (repo / ".claude-plugin" / "marketplace.json").write_text(json.dumps(market))
        with self.assertRaises(CatalogError):
            catalog_mod.load_entries(repo)


# ===========================================================================
# Content rendering
# ===========================================================================

class TestContent(_InstallerTestCase):
    def test_agent_references_use_managed_directory_and_neighbor_is_materialized(self):
        source = self.repo / "agents" / "beta"
        (source / "instructions").mkdir()
        (source / "instructions" / "guide.md").write_text("guide")
        dependency = self.repo / "skills" / "shared-dependency"
        dependency.mkdir()
        (dependency / "SKILL.md").write_text("---\nname: shared\ndescription: Shared\n---\nshared")
        (source / "beta.md").write_text(
            "---\nname: beta\ndescription: Beta\ntools: Read, UnknownTool\n---\n"
            "Read ${CLAUDE_PLUGIN_ROOT}/instructions/guide.md and "
            "${CLAUDE_PLUGIN_ROOT}/skills/shared-dependency/SKILL.md\n"
        )
        with self.assertRaises(ContentError):
            content_mod.render_entry(self.entries["agent-beta"], self.target, None)
        (source / "beta.md").write_text(
            "---\nname: beta\ndescription: Beta\ntools: Read\n---\n"
            "Read ${CLAUDE_PLUGIN_ROOT}/instructions/guide.md and "
            "${CLAUDE_PLUGIN_ROOT}/skills/shared-dependency/SKILL.md\n"
        )
        rendered = content_mod.render_entry(self.entries["agent-beta"], self.target, None)
        self.assertIn("awesome-agency/packages/agents/beta/instructions/guide.md", rendered)
        self.assertIn("awesome-agency/packages/skills/shared-dependency/SKILL.md", rendered)
        self.assertIn(str(self.target.resolve()), rendered["agents/beta.md"].decode())

    def test_bundle_materializes_every_non_metadata_asset(self):
        bundle = self.repo / "plugins" / "bundle-a"
        (bundle / "templates").mkdir()
        (bundle / "templates" / "example.txt").write_text("template")
        (bundle / "workflows").mkdir()
        (bundle / "workflows" / "flow.js").write_text("workflow")
        result = content_mod.render_entry(self.entries["bundle-a"], self.target, None)
        self.assertTrue(any(path.endswith("/templates/example.txt") for path in result))
        self.assertTrue(any(path.endswith("/workflows/flow.js") for path in result))

    def test_bundle_uses_public_discovery_paths_and_manifest_agents_only(self):
        bundle = self.repo / "plugins" / "bundle-a"
        (bundle / "agents" / "unlisted.md").write_text("not public")
        result = content_mod.render_entry(self.entries["bundle-a"], self.target, None)
        self.assertIn("skills/bundled-skill/SKILL.md", result)
        self.assertIn("agents/helper.md", result)
        self.assertNotIn("agents/unlisted.md", result)
        self.assertTrue(any(path.startswith("awesome-agency/") for path in result))

    def test_agent_frontmatter_uses_opencode_permissions_and_provider_model(self):
        result = content_mod.render_entry(self.entries["agent-beta"], self.target, None)
        text = result["agents/beta.md"].decode()
        self.assertIn("mode: subagent", text)
        self.assertIn("model: anthropic/claude-haiku-4-5", text)
        self.assertIn("permission:", text)
        self.assertIn("'*': deny", text)
        self.assertIn("bash: allow", text)
        self.assertNotIn("tools:", text)


    def test_skill_prefix(self):
        result = content_mod.render_entry(self.entries["skill-alpha"], self.target, None)
        self.assertIn("skills/alpha/SKILL.md", result)

    def test_explicit_skill_gets_open_code_command_entry_point(self):
        skill = self.tmp / "repo" / "skills" / "explicit"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: explicit\ndescription: Run explicitly\ndisable-model-invocation: true\n---\nDo the work.\n"
        )
        entry = Entry(name="explicit", source=skill, version="1.0.0", kind="skill", manifest={"name": "explicit"})
        result = content_mod.render_entry(entry, self.target, None)
        command = result["commands/explicit.md"].decode()
        self.assertIn("description: Run explicitly", command)
        self.assertIn("Do the work.", command)
        self.assertIn("$ARGUMENTS", command)

    def test_agent_prefix(self):
        result = content_mod.render_entry(self.entries["agent-beta"], self.target, None)
        self.assertIn("agents/beta.md", result)

    def test_bundle_renders_manifest_and_children(self):
        result = content_mod.render_entry(self.entries["bundle-a"], self.target, None)
        self.assertTrue(any("plugin.json" in k for k in result))
        self.assertTrue(any("bundled-skill" in k for k in result))

    def test_model_override_replaces_existing(self):
        result = content_mod.render_entry(self.entries["agent-beta"], self.target, "claude-sonnet-4-20250514")
        agent_file = result["agents/beta.md"].decode()
        self.assertIn("model: anthropic/claude-sonnet-4-20250514", agent_file)
        self.assertNotIn("claude-haiku-4-5", agent_file)

    def test_readonly_when_only_read_tools(self):
        result = content_mod.render_entry(self.entries["skill-alpha"], self.target, None)
        body = result["skills/alpha/SKILL.md"].decode()
        self.assertNotIn("tools:", body)

    def test_not_readonly_when_bash_tool(self):
        result = content_mod.render_entry(self.entries["agent-beta"], self.target, None)
        body = result["agents/beta.md"].decode()
        self.assertIn("permission:", body)

    def test_disallowed_tools_normalized(self):
        skill_dir = self.tmp / "repo" / "skills" / "disallowed"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text('---\nname: d\ndescription: t\ndisallowedTools:\n  - Write\n---\nBody.\n')
        entry = Entry(name="d", source=skill_dir, version="1.0.0", kind="skill", manifest={"name": "d", "version": "1.0.0"})
        result = content_mod.render_entry(entry, self.target, None)
        body = [v for k, v in result.items() if k.endswith("SKILL.md")][0].decode()
        self.assertNotIn("disallowed-tools:", body)

    def test_broken_symlink_rejected(self):
        d = self.tmp / "repo" / "skills" / "broken"
        d.mkdir(parents=True)
        (d / "link.md").symlink_to("/nonexistent")
        entry = Entry(name="broken", source=d, version="1.0.0", kind="skill", manifest={"name": "broken", "version": "1.0.0"})
        with self.assertRaises(ContentError):
            content_mod.render_entry(entry, self.target, None)

    def test_cyclic_symlink_rejected(self):
        d = self.tmp / "repo" / "skills" / "cyclic"
        d.mkdir(parents=True)
        sub = d / "sub"
        sub.mkdir()
        (sub / "link").symlink_to(d)
        entry = Entry(name="cyclic", source=d, version="1.0.0", kind="skill", manifest={"name": "cyclic", "version": "1.0.0"})
        with self.assertRaises(ContentError):
            content_mod.render_entry(entry, self.target, None)

    def test_placeholder_rewritten(self):
        d = self.tmp / "repo" / "skills" / "ph"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text("---\nname: ph\ndescription: t\n---\nPath: ${CLAUDE_PLUGIN_ROOT}/foo\n")
        entry = Entry(name="ph", source=d, version="1.0.0", kind="skill", manifest={"name": "ph", "version": "1.0.0"})
        result = content_mod.render_entry(entry, self.target, None)
        body = [v for k, v in result.items() if k.endswith("SKILL.md")][0].decode()
        self.assertIn("awesome-agency/packages/skills/ph", body)

    def test_absolute_public_path_rejected(self):
        with self.assertRaises(ContentError):
            content_mod._validate_relative_public_path(Path("/etc/passwd"))

    def test_multiline_yaml_parsed(self):
        result = content_mod.render_entry(self.entries["skill-alpha"], self.target, None)
        body = [v for k, v in result.items() if k.endswith("SKILL.md")][0].decode()
        self.assertIn("name: alpha", body)

    def test_executable_mode_from_source(self):
        d = self.tmp / "repo" / "skills" / "exec"
        d.mkdir(parents=True)
        (d / "run.sh").write_text("#!/bin/bash\necho hi")
        (d / "run.sh").chmod(0o755)
        (d / "SKILL.md").write_text("---\nname: exec\ndescription: t\n---\nBody.\n")
        entry = Entry(name="exec", source=d, version="1.0.0", kind="skill", manifest={"name": "exec", "version": "1.0.0"})
        result = content_mod.render_entry(entry, self.target, None)
        modes = content_mod.get_rendered_file_modes()
        self.assertEqual(modes["awesome-agency/packages/skills/exec/run.sh"], 0o755)


# ===========================================================================
# State: hash tracking + preflight
# ===========================================================================

class TestStateHashTracking(_InstallerTestCase):

    def test_sha256_persisted_after_install(self):
        self._install("skill-alpha")
        state = state_mod.load_state(self.target)
        files = state.get("files", {})
        self.assertTrue(len(files) > 0)
        for rel, info in files.items():
            self.assertIn("sha256", info)
            self.assertEqual(len(info["sha256"]), 64)  # SHA256 hex

    def test_mode_persisted_after_install(self):
        self._install("exec" if "exec" in self.entries else "skill-alpha")
        state = state_mod.load_state(self.target)
        for rel, info in state.get("files", {}).items():
            self.assertIn("mode", info)
            self.assertIsInstance(info["mode"], int)

    def test_version_persisted(self):
        self._install("skill-alpha")
        state = state_mod.load_state(self.target)
        self.assertIn("skill-alpha", state["entries"])
        self.assertEqual(state["entries"]["skill-alpha"]["version"], "1.0.0")

    def test_model_persisted(self):
        self._install("agent-beta", model="claude-sonnet-4-20250514")
        state = state_mod.load_state(self.target)
        self.assertEqual(state["entries"]["agent-beta"]["model"], "claude-sonnet-4-20250514")

    def test_disk_changed_since_recorded_conflicts(self):
        self._install("skill-alpha")
        # Tamper with on-disk file (simulates external edit)
        fp = self.target / "skills" / "alpha" / "SKILL.md"
        fp.write_bytes(b"tampered")
        # Re-install should reject the conflicting edit before any write.
        entry = self.entries["skill-alpha"]
        desired = content_mod.render_entry(entry, self.target, None)
        modes = content_mod.get_rendered_file_modes()
        owners = {k: ["skill-alpha"] for k in desired}
        with self.assertRaises(StateError):
            state_mod.plan_operation(
                self.target, desired, owners, file_modes=modes,
                entry_versions={"skill-alpha": entry.version},
            )

    def test_disk_matches_desired_adopted(self):
        self._install("skill-alpha")
        fp = self.target / "skills" / "alpha" / "SKILL.md"
        # Write desired content directly (simulates manual install with same bytes)
        desired = content_mod.render_entry(self.entries["skill-alpha"], self.target, None)
        fp.write_bytes(desired["skills/alpha/SKILL.md"])
        # Re-install should succeed (bytes match)
        modes = content_mod.get_rendered_file_modes()
        owners = {k: ["skill-alpha"] for k in desired}
        op = state_mod.plan_operation(
            self.target, desired, owners, file_modes=modes,
            entry_versions={"skill-alpha": "1.0.0"},
        )
        # Should not raise
        self.assertIsInstance(op, Operation)

    def test_unowned_file_same_bytes_adopted(self):
        # Place a file that matches what skill-alpha would install
        desired = content_mod.render_entry(self.entries["skill-alpha"], self.target, None)
        fp = self.target / "skills" / "alpha" / "SKILL.md"
        fp.parent.mkdir(parents=True)
        fp.write_bytes(desired["skills/alpha/SKILL.md"])
        # Install should adopt
        modes = content_mod.get_rendered_file_modes()
        owners = {k: ["skill-alpha"] for k in desired}
        op = state_mod.plan_operation(
            self.target, desired, owners, file_modes=modes,
            entry_versions={"skill-alpha": "1.0.0"},
        )
        self.assertIsInstance(op, Operation)

    def test_unowned_file_different_bytes_rejects(self):
        fp = self.target / "skills" / "alpha" / "SKILL.md"
        fp.parent.mkdir(parents=True)
        fp.write_bytes(b"different content")
        desired = content_mod.render_entry(self.entries["skill-alpha"], self.target, None)
        modes = content_mod.get_rendered_file_modes()
        owners = {k: ["skill-alpha"] for k in desired}
        with self.assertRaises(StateError):
            state_mod.plan_operation(
                self.target, desired, owners, file_modes=modes,
                entry_versions={"skill-alpha": "1.0.0"},
            )


# ===========================================================================
# State: lifecycle
# ===========================================================================

class TestLifecycle(_InstallerTestCase):
    def test_uninstall_preserves_user_edited_file_and_removes_entry_state(self):
        self._install("skill-alpha")
        path = self.target / "skills" / "alpha" / "SKILL.md"
        path.write_bytes(b"local edit")
        installed = state_mod.load_state(self.target)
        op = state_mod.plan_uninstall(self.target, "skill-alpha", installed["files"], installed)
        state_mod.apply_operation(op, remove_entries={"skill-alpha"})
        self.assertEqual(path.read_bytes(), b"local edit")
        self.assertNotIn("skill-alpha", state_mod.load_state(self.target)["entries"])
        self.assertNotIn("skill-alpha", next(iter(state_mod.load_state(self.target)["files"].values()), {}).get("owners", []))

    def test_cli_uninstall_works_after_marketplace_source_is_removed(self):
        self._install("skill-alpha")
        import install
        source = self.repo / ".claude-plugin" / "marketplace.json"
        project = self.tmp / "project"
        project.mkdir()
        self.target.rename(project / ".opencode")
        source.unlink()
        args = ["uninstall", "skill-alpha", "--repo", str(self.repo), "--project", str(project)]
        self.assertEqual(install.main(args), 0)

    def test_partial_update_keeps_unupdated_owner(self):
        first = self._install("skill-alpha")
        state = state_mod.load_state(self.target)
        state["files"]["skills/alpha/SKILL.md"]["owners"].append("bundle-a")
        state["entries"]["bundle-a"] = {"version": "2.1.0", "kind": "bundle", "model": None}
        state_mod.save_state(self.target, state)
        op = state_mod.plan_operation(
            self.target, first, {key: ["skill-alpha"] for key in first},
            file_modes=content_mod.get_rendered_file_modes(),
        )
        self.assertIn("bundle-a", op.owners_after["skills/alpha/SKILL.md"])

    def test_shared_edited_file_conflicts_atomically_and_uninstall_retains_edit(self):
        self._install("skill-alpha")
        path = self.target / "skills" / "alpha" / "SKILL.md"
        path.write_bytes(b"local edit")
        before = state_mod.load_state(self.target)

        desired = content_mod.render_entry(self.entries["skill-alpha"], self.target, None)
        owners = {rel: ["bundle-b"] for rel in desired}
        with self.assertRaises(StateError):
            state_mod.plan_operation(
                self.target, desired, owners,
                file_modes=content_mod.get_rendered_file_modes(),
            )
        self.assertEqual(path.read_bytes(), b"local edit")
        self.assertEqual(state_mod.load_state(self.target), before)

        with self.assertRaises(StateError):
            state_mod.plan_operation(
                self.target, desired,
                {rel: ["skill-alpha"] for rel in desired},
                file_modes=content_mod.get_rendered_file_modes(),
            )
        self.assertEqual(path.read_bytes(), b"local edit")
        self.assertEqual(state_mod.load_state(self.target), before)

        self._uninstall("skill-alpha")
        self.assertEqual(path.read_bytes(), b"local edit")
        state = state_mod.load_state(self.target)
        self.assertNotIn("skill-alpha", state["entries"])
        self.assertNotIn("skill-alpha", state["files"]["skills/alpha/SKILL.md"]["owners"])


    def test_install_creates_files(self):
        self._install("skill-alpha")
        self.assertTrue((self.target / "skills" / "alpha" / "SKILL.md").exists())

    def test_byte_identical_reinstall(self):
        self._install("skill-alpha")
        fp = self.target / "skills" / "alpha" / "SKILL.md"
        before = fp.read_bytes()
        self._install("skill-alpha")
        after = fp.read_bytes()
        self.assertEqual(before, after)

    def test_update_replaces_matching_old_hash(self):
        self._install("skill-alpha")
        fp = self.target / "skills" / "alpha" / "SKILL.md"
        # Modify source to produce different content
        (self.repo / "skills" / "alpha" / "SKILL.md").write_text("---\nname: alpha\ndescription: Updated\n---\nNew body.\n")
        self.entries = catalog_mod.load_entries(self.repo)
        self._install("skill-alpha")
        self.assertIn(b"New body.", fp.read_bytes())

    def test_update_user_edit_conflicts(self):
        self._install("skill-alpha")
        fp = self.target / "skills" / "alpha" / "SKILL.md"
        fp.write_bytes(b"---\nname: alpha\ndescription: Alpha skill\ntools:\n  - Read\n  - Read*\n---\nMy custom edit.\n")
        # Modify source
        (self.repo / "skills" / "alpha" / "SKILL.md").write_text("---\nname: alpha\ndescription: Updated\n---\nNew body.\n")
        self.entries = catalog_mod.load_entries(self.repo)
        with self.assertRaises(StateError):
            self._install("skill-alpha")
        self.assertEqual(fp.read_bytes(), b"---\nname: alpha\ndescription: Alpha skill\ntools:\n  - Read\n  - Read*\n---\nMy custom edit.\n")

    def test_shared_ownership_retained_on_uninstall(self):
        self._install("bundle-a")
        shared = "skills/bundled-skill/SKILL.md"
        # Add second owner
        state = state_mod.load_state(self.target)
        state["files"][shared]["owners"].append("bundle-b")
        state_mod.save_state(self.target, state)
        self._uninstall("bundle-a")
        self.assertTrue((self.target / shared).exists())

    def test_uninstall_removes_unowned_files(self):
        self._install("skill-alpha")
        self._uninstall("skill-alpha")
        self.assertFalse((self.target / "skills" / "alpha" / "SKILL.md").exists())

    def test_dry_run_zero_writes(self):
        desired = content_mod.render_entry(self.entries["skill-alpha"], self.target, None)
        modes = content_mod.get_rendered_file_modes()
        owners = {k: ["skill-alpha"] for k in desired}
        op = state_mod.plan_operation(self.target, desired, owners, file_modes=modes)
        state_mod.apply_operation(op, dry_run=True)
        self.assertFalse((self.target / "skills" / "alpha" / "SKILL.md").exists())
        # No state file created either
        self.assertFalse((self.target / state_mod.STATE_FILE).exists())

    def test_destination_ancestor_symlink_rejected(self):
        link = self.target / "skills"
        link.symlink_to("/tmp")
        desired = content_mod.render_entry(self.entries["skill-alpha"], self.target, None)
        owners = {k: ["skill-alpha"] for k in desired}
        with self.assertRaises(StateError):
            state_mod.plan_operation(self.target, desired, owners)

    def test_rollback_restores_old_bytes(self):
        self._install("skill-alpha")
        fp = self.target / "skills" / "alpha" / "SKILL.md"
        original = fp.read_bytes()
        # Force a failure during apply by patching os.replace
        with mock.patch("agency.state.os.replace", side_effect=OSError("injected")):
            desired = content_mod.render_entry(self.entries["skill-alpha"], self.target, None)
            modes = content_mod.get_rendered_file_modes()
            owners = {k: ["skill-alpha"] for k in desired}
            op = state_mod.plan_operation(self.target, desired, owners, file_modes=modes)
            with self.assertRaises(StateError):
                state_mod.apply_operation(op)
        # File should be restored to original
        self.assertEqual(fp.read_bytes(), original)

    def test_rollback_restores_deleted_files(self):
        self._install("skill-alpha")
        fp = self.target / "skills" / "alpha" / "SKILL.md"
        # Now uninstall, but inject failure
        entry = self.entries["skill-alpha"]
        installed = content_mod.render_entry(entry, self.target, None)
        state = state_mod.load_state(self.target)
        op = state_mod.plan_uninstall(self.target, "skill-alpha", installed, state)
        # Verify file exists before
        self.assertTrue(fp.exists())
        # The apply should succeed normally (no failure injection for delete-only)
        state_mod.apply_operation(op)
        self.assertFalse(fp.exists())

    def test_state_participates_rollback(self):
        self._install("skill-alpha")
        state_before = (self.target / state_mod.STATE_FILE).read_bytes()
        with mock.patch("agency.state.os.replace", side_effect=OSError("injected")):
            desired = content_mod.render_entry(self.entries["skill-alpha"], self.target, None)
            modes = content_mod.get_rendered_file_modes()
            owners = {k: ["skill-alpha"] for k in desired}
            op = state_mod.plan_operation(self.target, desired, owners, file_modes=modes)
            with self.assertRaises(StateError):
                state_mod.apply_operation(op)
        # State file should be restored
        self.assertEqual((self.target / state_mod.STATE_FILE).read_bytes(), state_before)

    def test_rollback_removes_new_parent_directories(self):
        desired = {"new/nested/one.txt": b"one", "new/nested/two.txt": b"two"}
        op = state_mod.plan_operation(
            self.target, desired,
            {key: ["new-entry"] for key in desired},
        )
        original_replace = state_mod.os.replace
        calls = 0

        def fail_second(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected")
            return original_replace(source, destination)

        with mock.patch("agency.state.os.replace", side_effect=fail_second):
            with self.assertRaises(StateError):
                state_mod.apply_operation(op)
        self.assertFalse((self.target / "new").exists())

    def test_project_target(self):
        project = self.tmp / "myproject"
        project.mkdir()
        target = project / ".opencode"
        target.mkdir()
        entry = self.entries["skill-alpha"]
        desired = content_mod.render_entry(entry, target, None)
        modes = content_mod.get_rendered_file_modes()
        owners = {k: ["skill-alpha"] for k in desired}
        op = state_mod.plan_operation(target, desired, owners, file_modes=modes)
        state_mod.apply_operation(op)
        self.assertTrue((target / "skills" / "alpha" / "SKILL.md").exists())


# ===========================================================================
# State: ownership
# ===========================================================================

class TestOwnership(_InstallerTestCase):

    def test_owners_persisted_in_state(self):
        self._install("skill-alpha")
        state = state_mod.load_state(self.target)
        for info in state["files"].values():
            self.assertIn("skill-alpha", info["owners"])

    def test_shared_ownership(self):
        self._install("skill-alpha")
        self._install("bundle-a")
        state = state_mod.load_state(self.target)
        # Some files may be owned by multiple entries
        for info in state["files"].values():
            self.assertIsInstance(info["owners"], list)

    def test_load_owners_compat(self):
        self._install("skill-alpha")
        owners = state_mod.load_owners(self.target)
        self.assertTrue(len(owners) > 0)
        for rel, owner_list in owners.items():
            self.assertIn("skill-alpha", owner_list)


# ===========================================================================
# YAML edge cases
# ===========================================================================

class TestYAML(_InstallerTestCase):

    def test_multiline_description(self):
        d = self.tmp / "repo" / "skills" / "ml"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text('---\nname: ml\ndescription: |\n  Multi\n  line.\n---\nBody.\n')
        entry = Entry(name="ml", source=d, version="1.0.0", kind="skill", manifest={"name": "ml", "version": "1.0.0"})
        result = content_mod.render_entry(entry, self.target, None)
        body = [v for k, v in result.items() if k.endswith("SKILL.md")][0].decode()
        self.assertIn("name: ml", body)

    def test_quoted_yaml_value(self):
        d = self.tmp / "repo" / "skills" / "q"
        d.mkdir(parents=True)
        (d / "SKILL.md").write_text('---\nname: "quoted"\ndescription: \'A desc\'\n---\nBody.\n')
        entry = Entry(name="q", source=d, version="1.0.0", kind="skill", manifest={"name": "q", "version": "1.0.0"})
        result = content_mod.render_entry(entry, self.target, None)
        body = [v for k, v in result.items() if k.endswith("SKILL.md")][0].decode()
        self.assertIn("name:", body)
        self.assertIn("quoted", body)


class TestRealMarketplace(unittest.TestCase):
    def test_every_published_entry_materializes_real_complete_paths(self):
        repo = Path(__file__).resolve().parents[2]
        entries = catalog_mod.load_entries(repo)
        self.assertEqual(len(entries), 75)
        target = Path(tempfile.mkdtemp())
        try:
            rendered_by_name = {
                name: content_mod.render_entry(entry, target, None)
                for name, entry in entries.items()
            }
            all_paths = set().union(*(files for files in rendered_by_name.values()))
            self.assertTrue(any(path.startswith("awesome-agency/packages/") for path in all_paths))
            self.assertFalse(any(path.startswith("plugins/") for path in all_paths))
            for name, files in rendered_by_name.items():
                self.assertTrue(any(path.startswith("awesome-agency/packages/") for path in files), name)
                for path, data in files.items():
                    if path.startswith(("skills/", "agents/")) and path.endswith((".md", ".json", ".yml", ".yaml", ".js", ".py", ".sh")):
                        self.assertNotIn(b"${CLAUDE_PLUGIN_ROOT}", data, (name, path))
            for bundle_name, entry in entries.items():
                if entry.kind != "bundle":
                    continue
                bundle_files = rendered_by_name[bundle_name]
                for path, data in bundle_files.items():
                    if not path.startswith("skills/") or not path.endswith("/SKILL.md"):
                        continue
                    skill_name = Path(path).parts[1]
                    micro = next((files for other, files in rendered_by_name.items() if entries[other].kind == "skill" and entries[other].source.name == skill_name), None)
                    if micro is not None:
                        self.assertEqual(data, micro[path])
        finally:
            shutil.rmtree(target, ignore_errors=True)


# ===========================================================================
# CLI
# ===========================================================================

class TestCLI(_InstallerTestCase):

    def _run_main(self, argv):
        from install import main
        import io
        old_stdout = sys.stdout
        sys.stdout = buf = io.StringIO()
        try:
            exit_code = main(argv)
        finally:
            sys.stdout = old_stdout
        return exit_code, buf.getvalue()

    def test_list(self):
        code, out = self._run_main(["list", "--repo", str(self.repo)])
        self.assertEqual(code, 0)
        self.assertIn("skill-alpha", out)
        self.assertIn("agent-beta", out)

    def test_install_missing_entry(self):
        code, out = self._run_main(["install", "nope", "--repo", str(self.repo), "--project", str(self.tmp / "proj")])
        self.assertNotEqual(code, 0)

    def test_install_requires_target(self):
        with self.assertRaises(SystemExit):
            self._run_main(["install", "skill-alpha", "--repo", str(self.repo)])

    def test_install_command_writes_state_and_public_file(self):
        code, _ = self._run_main([
            "install", "skill-alpha", "--repo", str(self.repo),
            "--project", str(self.tmp / "project"),
        ])
        self.assertEqual(code, 0)
        target = self.tmp / "project" / ".opencode"
        self.assertTrue((target / "skills" / "alpha" / "SKILL.md").is_file())
        self.assertTrue((target / state_mod.STATE_FILE).is_file())

    def test_partial_uninstall_removes_only_the_removed_entry_public_file(self):
        project = self.tmp / "partial-project"
        self.assertEqual(self._run_main([
            "install", "doublecheck", "--repo", str(self.repo), "--project", str(project),
        ])[0], 0)
        self.assertEqual(self._run_main([
            "install", "doublecheck-agent", "--repo", str(self.repo), "--project", str(project),
        ])[0], 0)
        target = project / ".opencode"
        skill = target / "skills" / "doublecheck" / "SKILL.md"
        agent = target / "agents" / "doublecheck-agent.md"
        self.assertTrue(skill.is_file())
        self.assertTrue(agent.is_file())

        self.assertEqual(self._run_main([
            "uninstall", "doublecheck-agent", "--repo", str(self.repo), "--project", str(project),
        ])[0], 0)
        self.assertTrue(skill.is_file())
        self.assertFalse(agent.exists())

    def test_conflicting_target_selectors_exit_before_writing(self):
        project = self.tmp / "conflicting-project"
        with self.assertRaises(SystemExit):
            self._run_main([
                "install", "skill-alpha", "--repo", str(self.repo),
                "--project", str(project), "--global",
            ])
        self.assertFalse((project / ".opencode").exists())
        self.assertFalse((self.tmp / "xdg" / "opencode").exists())

    def test_update_without_names_only_updates_persisted_entries(self):
        project = self.tmp / "update-project"
        self.assertEqual(self._run_main([
            "install", "skill-alpha", "--repo", str(self.repo), "--project", str(project),
        ])[0], 0)
        self.assertEqual(self._run_main([
            "update", "--repo", str(self.repo), "--project", str(project),
        ])[0], 0)
        target = project / ".opencode"
        self.assertTrue((target / "skills" / "alpha" / "SKILL.md").is_file())
        self.assertFalse((target / "agents" / "beta.md").exists())
        runtime = json.loads((target / "awesome-agency" / "runtime.json").read_text(encoding="utf-8"))
        self.assertEqual([item["name"] for item in runtime["entries"]], ["skill-alpha"])

    def test_named_uninstalled_update_is_rejected_without_writing(self):
        project = self.tmp / "uninstalled-update-project"
        code, _ = self._run_main([
            "update", "agent-beta", "--repo", str(self.repo), "--project", str(project),
        ])
        self.assertNotEqual(code, 0)
        self.assertFalse((project / ".opencode").exists())

    def test_update_empty_target_does_not_install_catalog_entries(self):
        project = self.tmp / "empty-update-project"
        self.assertEqual(self._run_main([
            "update", "--repo", str(self.repo), "--project", str(project),
        ])[0], 0)
        self.assertFalse((project / ".opencode").exists())


if __name__ == "__main__":
    unittest.main()
