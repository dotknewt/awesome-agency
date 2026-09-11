#!/usr/bin/env python3
"""Validate the OpenCode projection of every marketplace entry.

This is intentionally separate from ``check-host-compat.py``.  Claude Code and
Copilot consume the marketplace directly; OpenCode consumes generated files from
the Python installer and a JavaScript runtime adapter.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "opencode"))

from agency.catalog import load_entries  # noqa: E402
from agency.config import render_configuration  # noqa: E402
from agency.content import _parse_frontmatter, render_entry  # noqa: E402
from agency.state import plan_operation  # noqa: E402


def fail(message: str) -> "NoReturn":
    raise RuntimeError(message)


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    try:
        value, _body = _parse_frontmatter(text)
    except ValueError:
        return {}
    return value


def check_public_files(name: str, rendered: dict[str, bytes]) -> None:
    for relative, data in rendered.items():
        path = Path(relative)
        if path.is_absolute() or ".." in path.parts:
            fail(f"{name}: installer emitted unsafe path {relative}")
        public_component = path.parts and path.parts[0] in {"skills", "agents", "commands"}
        if public_component and b"${CLAUDE_PLUGIN_ROOT}" in data:
            fail(f"{name}: unresolved CLAUDE_PLUGIN_ROOT in {relative}")
        requires_frontmatter = public_component and (
            (path.parts[0] == "skills" and path.name == "SKILL.md")
            or (path.parts[0] in {"agents", "commands"} and path.suffix == ".md")
        )
        if requires_frontmatter:
            frontmatter_text = data.decode("utf-8")
            if not frontmatter_text.startswith("---\n"):
                fail(f"{name}: {relative} has no OpenCode frontmatter")


def merge_rendered(
    desired: dict[str, bytes],
    owners: dict[str, list[str]],
    name: str,
    rendered: dict[str, bytes],
    owner_names: list[str],
) -> None:
    """Merge one rendered contribution without hiding byte-level collisions."""
    for relative, data in rendered.items():
        if relative in desired and desired[relative] != data:
            fail(f"joint install collision: {name} disagrees on {relative}")
        desired[relative] = data
        path_owners = owners.setdefault(relative, [])
        for owner in owner_names:
            if owner not in path_owners:
                path_owners.append(owner)


def hook_files(source: Path):
    yield from (path for path in source.rglob("hooks.json") if path.is_file())


def mcp_files(source: Path):
    for pattern in (".mcp.json", "opencode.json"):
        yield from (path for path in source.rglob(pattern) if path.is_file())


def _hook_declarations(metadata: dict) -> dict[str, dict]:
    declarations = metadata.get("hook_declarations", [])
    if not isinstance(declarations, list):
        fail("opencode.hook_declarations must be a list")
    result = {}
    for declaration in declarations:
        if not isinstance(declaration, dict) or not isinstance(declaration.get("source"), str):
            fail(f"invalid OpenCode hook declaration: {declaration!r}")
        source = declaration["source"].removeprefix("./")
        if source in result:
            fail(f"duplicate OpenCode hook declaration: {source}")
        result[source] = declaration
    return result


def check_hook_declaration(path: Path, metadata: dict) -> None:
    relative = path.relative_to(ROOT).as_posix()
    declaration = _hook_declarations(metadata).get(relative)
    if declaration is None:
        fail(f"{relative}: missing OpenCode hook declaration metadata")
    expected = declaration.get("sha256")
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != expected:
        fail(
            f"{relative}: hook declaration changed (expected sha256 {expected}, found {actual}); "
            "review the adapter and runtime tests, then update host-compat metadata"
        )
    adapter = declaration.get("adapter")
    if not isinstance(adapter, str) or not (ROOT / adapter).is_file():
        fail(f"{relative}: hook declaration has no usable adapter path")
    for test_path in declaration.get("coverage", []):
        coverage_path = ROOT / test_path
        if not coverage_path.is_file():
            fail(f"{relative}: missing declared hook coverage test {test_path}")
    for test_name in declaration.get("test_names", []):
        if not any(test_name in (ROOT / test_path).read_text(encoding="utf-8")
                   for test_path in declaration.get("coverage", [])):
            fail(f"{relative}: declared runtime test is absent: {test_name}")


def check_hook_declaration_metadata(metadata: dict) -> None:
    declarations = _hook_declarations(metadata)
    for relative in declarations:
        path = ROOT / relative
        if not path.is_file():
            fail(f"OpenCode hook declaration points at missing source: {relative}")
        check_hook_declaration(path, metadata)


def check_source_constructs(entry, metadata: dict) -> None:
    hooks = metadata["hook_adapters"]
    hook_fields = set(metadata["hook_fields"])
    mcp_fields = set(metadata["mcp_server_fields"])
    for path in hook_files(entry.source):
        check_hook_declaration(path, metadata)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            fail(f"{entry.name}: invalid hooks JSON {path}: {error}")
        events = data.get("hooks")
        if not isinstance(events, dict):
            fail(f"{entry.name}: {path} must contain an object named hooks")
        for event, groups in events.items():
            adapter = hooks.get(event)
            if adapter is None:
                fail(f"{entry.name}: unsupported future hook event {event!r} in {path}")
            if not isinstance(groups, list):
                fail(f"{entry.name}: hook event {event} must contain a list")
            for group in groups:
                if not isinstance(group, dict):
                    fail(f"{entry.name}: hook group for {event} is not an object")
                unknown = set(group) - {"matcher", "hooks"}
                if unknown:
                    fail(f"{entry.name}: unsupported hook group fields {sorted(unknown)} in {path}")
                for hook in group.get("hooks", []):
                    if not isinstance(hook, dict):
                        fail(f"{entry.name}: hook action for {event} is not an object")
                    unknown = set(hook) - hook_fields
                    if unknown:
                        fail(f"{entry.name}: unsupported hook fields {sorted(unknown)} in {path}")
            if adapter.get("status") == "adapter" and adapter.get("runtime") != metadata["runtime_adapter"]:
                fail(f"{entry.name}: hook {event} adapter does not match the canonical runtime adapter")

    for path in mcp_files(entry.source):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            fail(f"{entry.name}: invalid MCP JSON {path}: {error}")
        servers = data.get("mcpServers", data.get("mcp", {}))
        if not isinstance(servers, dict):
            fail(f"{entry.name}: {path} MCP section must be an object")
        for server, value in servers.items():
            if not isinstance(value, dict):
                fail(f"{entry.name}: MCP server {server} is not an object")
            unknown = set(value) - mcp_fields
            if unknown:
                fail(f"{entry.name}: unsupported MCP fields {sorted(unknown)} in {path}")


def check_projection(metadata: dict) -> tuple[int, list[str]]:
    entries = load_entries(ROOT)
    if len(entries) != metadata["expected_entries"]:
        fail(f"expected {metadata['expected_entries']} marketplace entries, found {len(entries)}")
    check_hook_declaration_metadata(metadata)
    rendered_by_name: dict[str, dict[str, bytes]] = {}
    with tempfile.TemporaryDirectory(prefix="awesome-agency-opencode-check-") as temp:
        target = Path(temp)
        for name, entry in sorted(entries.items()):
            rendered = render_entry(entry, target, None)
            check_public_files(name, rendered)
            check_source_constructs(entry, metadata)
            rendered_by_name[name] = rendered

        owners: dict[str, list[str]] = {}
        desired: dict[str, bytes] = {}
        for name, rendered in rendered_by_name.items():
            merge_rendered(desired, owners, name, rendered, [name])
        contribution = render_configuration(list(entries.values()), target, None)
        check_public_files("automatic-runtime", contribution)
        merge_rendered(desired, owners, "automatic-runtime", contribution, sorted(entries))
        plan_operation(target, desired, owners)

        explicit = set()
        for entry in entries.values():
            skill_files = [entry.source / "SKILL.md"]
            if entry.kind == "bundle":
                skill_files = list(entry.source.rglob("SKILL.md"))
            for source in skill_files:
                if source.is_file() and frontmatter(source).get("disable-model-invocation") is True:
                    explicit.add(source.parent.name)
        commands = {
            Path(relative).stem
            for rendered in rendered_by_name.values()
            for relative in rendered
            if relative.startswith("commands/") and relative.endswith(".md")
        }
        missing = sorted(explicit - commands)
        if missing:
            fail(f"explicit skills missing generated OpenCode commands: {', '.join(missing)}")
    return len(entries), sorted(explicit)


def expected_installed_files(entries, target: Path, project: Path) -> set[str]:
    expected = set()
    for entry in entries.values():
        expected.update(render_entry(entry, target, None))
    previous = os.environ.get("XDG_CONFIG_HOME")
    os.environ["XDG_CONFIG_HOME"] = str(project.parent / "isolated-global-config")
    try:
        expected.update(render_configuration(list(entries.values()), target, project))
    finally:
        if previous is None:
            os.environ.pop("XDG_CONFIG_HOME", None)
        else:
            os.environ["XDG_CONFIG_HOME"] = previous
    return expected


def assert_installed_artifacts(target: Path, expected_names: set[str], expected_files: set[str]) -> None:
    state_path = target / "awesome-agency/state.json"
    runtime_path = target / "awesome-agency/runtime.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"joint install did not produce readable managed state/runtime: {error}")
    actual_names = set(state.get("entries", {}))
    runtime_names = {entry.get("name") for entry in runtime.get("entries", [])}
    if actual_names != expected_names:
        fail(f"joint install state entries differ: missing={sorted(expected_names - actual_names)}, extra={sorted(actual_names - expected_names)}")
    if runtime_names != expected_names:
        fail(f"joint install runtime entries differ: missing={sorted(expected_names - runtime_names)}, extra={sorted(runtime_names - expected_names)}")
    actual_files = set(state.get("files", {}))
    if actual_files != expected_files:
        fail(f"joint install file set differs: missing={sorted(expected_files - actual_files)}, extra={sorted(actual_files - expected_files)}")
    for relative in actual_files:
        path = target / relative
        if not path.is_file() or path.is_symlink():
            fail(f"joint install public/managed artifact is missing or symlinked: {relative}")
        if relative != "awesome-agency/runtime.json" and str(ROOT).encode() in path.read_bytes():
            fail(f"joint install artifact retains a source-checkout path: {relative}")


def assert_debug_config(output: bytes, plugin_path: Path, synthetic_server: str) -> dict:
    try:
        config = json.loads(output.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        fail(f"OpenCode debug config was not JSON: {error}")
    plugins = config.get("plugin", [])
    plugin_uri = plugin_path.resolve().as_uri()
    accepted = {str(plugin_path.resolve()), plugin_uri}
    if not isinstance(plugins, list) or len(plugins) != 1 or plugins[0] not in accepted:
        fail(
            "OpenCode debug config plugin list was not exactly the generated local plugin: "
            f"expected one of {sorted(accepted)!r}, found {plugins!r}"
        )
    server = config.get("mcp", {}).get(synthetic_server)
    if not isinstance(server, dict) or server.get("enabled") is not False:
        fail(f"OpenCode config hook did not inject disabled synthetic MCP server {synthetic_server!r}")
    return config


def assert_discovered_skills(output: bytes, expected_skills: set[str]) -> None:
    try:
        discovered = json.loads(output.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        fail(f"OpenCode debug skill output was not JSON: {error}")
    names = {item.get("name") for item in discovered if isinstance(item, dict)}
    missing = expected_skills - names
    if missing:
        fail(f"OpenCode skill discovery missed installed skills: {', '.join(sorted(missing))}")


def assert_discovered_agent(output: bytes, name: str, expected_permissions: dict[str, str]) -> dict:
    try:
        agent = json.loads(output.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        fail(f"OpenCode debug agent {name} output was not JSON: {error}")
    if not isinstance(agent, dict):
        fail(f"OpenCode debug agent {name} output was not an object")
    model = agent.get("model")
    if model != {"providerID": "openai", "modelID": "gpt-5.6-sol"}:
        fail(f"OpenCode agent {name} model differs: {model!r}")
    permissions = agent.get("permission")
    if not isinstance(permissions, list):
        fail(f"OpenCode agent {name} has no permission rule list: {permissions!r}")
    for index, rule in enumerate(permissions):
        if (
            not isinstance(rule, dict)
            or not isinstance(rule.get("permission"), str)
            or not isinstance(rule.get("pattern"), str)
            or rule.get("action") not in {"allow", "ask", "deny"}
        ):
            fail(f"OpenCode agent {name} has malformed permission rule {index}: {rule!r}")
    for permission, expected in expected_permissions.items():
        direct = [
            rule for rule in permissions
            if rule["permission"] == permission and rule["pattern"] == "*"
        ]
        if not direct or direct[-1]["action"] != expected:
            actual = direct[-1]["action"] if direct else None
            fail(
                f"OpenCode agent {name} permission {permission!r} lacks the required "
                f"global {expected!r} rule: found {actual!r}"
            )
        actual = None
        for rule in permissions:
            if rule["pattern"] == "*" and rule["permission"] in {"*", permission}:
                actual = rule["action"]
        if actual != expected:
            fail(
                f"OpenCode agent {name} effective permission {permission!r} differs: "
                f"expected {expected!r}, found {actual!r}"
            )
    return agent


def isolated_environment(root: Path) -> dict[str, str]:
    """Return an environment that cannot inject OpenCode config or Node modules."""
    env = {
        key: value for key, value in os.environ.items()
        if not key.startswith("OPENCODE_") and key not in {"NODE_PATH", "NODE_OPTIONS"}
    }
    env.update({
        "HOME": str(root / "home"),
        "XDG_CONFIG_HOME": str(root / "config"),
        "XDG_DATA_HOME": str(root / "data"),
        "XDG_CACHE_HOME": str(root / "cache"),
        "XDG_STATE_HOME": str(root / "state"),
        "LUDUS_URL": "",
        "LUDUS_API_KEY": "",
    })
    return env


def isolated_project(root: Path, name: str) -> Path:
    project = root / name
    project.mkdir()
    (project / "opencode.json").write_text(
        json.dumps({"$schema": "https://opencode.ai/config.json", "mcp": {
            "ludus": {"enabled": False}, "obsidian": {"enabled": False}
        }}), encoding="utf-8"
    )
    return project


def install_entries(project: Path, entries: dict, env: dict[str, str]) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "opencode/install.py"), "install", *sorted(entries),
         "--project", str(project)], cwd=ROOT, env=env,
        check=False, capture_output=True, text=True,
    )
    if result.returncode != 0:
        fail(f"OpenCode install failed for {len(entries)} entries:\n{result.stderr}")


def run_runtime_discovery(metadata: dict) -> None:
    binary = metadata["binary"]
    with tempfile.TemporaryDirectory(prefix="awesome-agency-opencode-runtime-") as temp:
        root = Path(temp)
        env = isolated_environment(root)
        try:
            version = subprocess.run(
                [binary, "--version"], env=env, check=True, capture_output=True, text=True,
            ).stdout.strip()
        except (OSError, subprocess.CalledProcessError) as error:
            fail(f"cannot execute pinned OpenCode discovery binary {binary}: {error}")
        if version != metadata["version"]:
            fail(f"OpenCode version mismatch: expected {metadata['version']}, found {version}")
        entries = load_entries(ROOT)
        project = isolated_project(root, "all-entries")
        target = project / ".opencode"
        install_entries(project, entries, env)
        assert_installed_artifacts(
            target,
            set(entries),
            expected_installed_files(entries, target, project),
        )
        all_config_path = project / "opencode.json"
        all_config = json.loads(all_config_path.read_text(encoding="utf-8"))
        all_config["plugin"] = [(target / "plugins/awesome-agency.js").resolve().as_uri()]
        all_config_path.write_text(json.dumps(all_config, indent=2) + "\n", encoding="utf-8")
        startup = subprocess.run(
            [binary, "debug", "startup"], cwd=project, env=env,
            check=False, capture_output=True, text=True,
        )
        if startup.returncode != 0:
            fail(f"OpenCode {version} isolated startup failed:\n{startup.stderr}")
        if "opencode" not in startup.stdout.lower() and not startup.stdout.strip():
            fail("OpenCode startup produced no measurable output")

        # Keep the real config-hook proof small enough for debug config's bounded output.
        runtime_project = isolated_project(root, "runtime-plugin")
        runtime_entries = {
            "doublecheck": entries["doublecheck"],
            "doublecheck-agent": entries["doublecheck-agent"],
        }
        runtime_target = runtime_project / ".opencode"
        install_entries(runtime_project, runtime_entries, env)
        runtime_path = runtime_target / "awesome-agency/runtime.json"
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
        synthetic_server = "awesome-agency-smoke-disabled"
        runtime.setdefault("mcp", {})[synthetic_server] = {
            "type": "local",
            "command": ["node", "-e", "process.exit(0)"],
            "enabled": False,
        }
        runtime_path.write_text(json.dumps(runtime, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        config_path = runtime_project / "opencode.json"
        user_config = json.loads(config_path.read_text(encoding="utf-8"))
        plugin_path = (runtime_target / "plugins/awesome-agency.js").resolve()
        user_config["plugin"] = [plugin_path.as_uri()]
        config_path.write_text(json.dumps(user_config, indent=2) + "\n", encoding="utf-8")
        config = subprocess.run(
            [binary, "debug", "config"], cwd=runtime_project, env=env,
            check=False, capture_output=True,
        )
        if config.returncode != 0:
            fail(f"OpenCode debug config failed:\n{config.stderr.decode(errors='replace')}")
        assert_debug_config(config.stdout, plugin_path, synthetic_server)
        runtime_startup = subprocess.run(
            [binary, "debug", "startup"], cwd=runtime_project, env=env,
            check=False, capture_output=True, text=True,
        )
        if runtime_startup.returncode != 0:
            fail(f"OpenCode local-plugin startup failed:\n{runtime_startup.stderr}")
        skill = subprocess.run(
            [binary, "debug", "skill"], cwd=runtime_project, env=env,
            check=False, capture_output=True,
        )
        if skill.returncode != 0:
            fail(f"OpenCode skill discovery failed:\n{skill.stderr.decode(errors='replace')}")
        assert_discovered_skills(skill.stdout, {"doublecheck", "subagent-model-policy"})
        agent = subprocess.run(
            [binary, "debug", "agent", "doublecheck"], cwd=runtime_project, env=env,
            check=False, capture_output=True,
        )
        if agent.returncode != 0 or b"doublecheck" not in agent.stdout:
            fail(f"OpenCode agent discovery did not expose the installed projection:\n{agent.stderr.decode(errors='replace')}")
        for name, permissions in {
            "sdd-worker": {"task": "deny", "subagent_dispatch": "deny"},
            "sdd-reviewer": {"edit": "deny", "bash": "deny", "task": "deny", "subagent_dispatch": "deny"},
        }.items():
            discovered = subprocess.run(
                [binary, "debug", "agent", name], cwd=runtime_project, env=env,
                check=False, capture_output=True,
            )
            if discovered.returncode != 0:
                fail(f"OpenCode agent discovery failed for {name}:\n{discovered.stderr.decode(errors='replace')}")
            assert_discovered_agent(discovered.stdout, name, permissions)
    print(
        f"OpenCode {version} isolated startup/discovery passed "
        "(installed TS dispatcher + host SDK loaded, local plugin enabled, "
        "temporary HOME/XDG, no MCP credentials)"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", action="store_true", help="also run the pinned OpenCode binary in an isolated environment")
    args = parser.parse_args()
    matrix = json.loads((ROOT / ".github/host-compat.json").read_text(encoding="utf-8"))
    metadata = matrix.get("opencode")
    if not isinstance(metadata, dict):
        fail("host-compat.json has no opencode metadata")
    count, explicit = check_projection(metadata)
    print(f"OpenCode projection OK: {count} entries rendered; {len(explicit)} explicit skills have commands")
    if args.runtime:
        run_runtime_discovery(metadata)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"::error::{error}", file=sys.stderr)
        raise SystemExit(1)
