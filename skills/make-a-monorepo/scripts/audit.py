#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""audit.py — run the mechanically-checkable portion of make-a-monorepo's audit checklist.

Implements the checks from references/audit-checklist.md that don't require human judgment:

  1. json_validity     — every JSON file the convention expects (.mcp.json,
                          .claude/settings.json, mcp-servers/registry.json,
                          schemas/*.schema.json) parses as valid JSON, and
                          registry.json / schema files carry a "$schema_version" field.
  2. naming             — kebab-case naming for top-level convention dirs/files, plus the
                          specific patterns documented in CLAUDE.md: mcp-servers/<domain>-mcp,
                          schemas/<entity>.schema.json, reports/YYYY-MM-DD-<slug>.md.
  3. gitignore          — .gitignore exists and contains the three required entries
                          (.env, .claude/settings.local.json, .claude/CLAUDE.local.md).
  4. env_not_tracked    — `git ls-files -- .env` returns nothing (skipped, not failed, if the
                          target isn't a git repo).
  5. conventional_commits — the last 10 commit subjects match a conventional-commit prefix
                          (skipped, not failed, if the target isn't a git repo or has no commits).

This script does NOT judge CLAUDE.md prose quality, agent/skill hygiene, or anything else that
needs human read-and-decide. Those parts of the checklist stay manual. See
references/audit-checklist.md for the full checklist this covers a slice of.

Output: a single JSON object on stdout — one entry per check group, a "summary", and a top-level
"passed" boolean. All progress notes, warnings, and skip reasons go to stderr so stdout stays
machine-parseable.

Exit codes:
  0  PASS  — ran successfully, every check that ran passed (skips don't count against this)
  1  ERROR — couldn't run at all (bad --path, not a directory, etc.)
  2  (reserved by argparse for CLI usage errors, e.g. unknown flags)
  3  FAIL  — ran successfully, at least one check found a violation

Examples:
  python3 scripts/audit.py
  python3 scripts/audit.py --path ../some-other-monorepo
  python3 scripts/audit.py --path . --indent 0 > report.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

EXIT_PASS = 0
EXIT_ERROR = 1
EXIT_FAIL = 3

KEBAB_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MCP_DIR_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*-mcp$")
SCHEMA_FILE_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*\.schema\.json$")
REPORT_FILE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9]+(-[a-z0-9]+)*\.md$")

CONVENTIONAL_COMMIT_RE = re.compile(
    r"^(feat|fix|docs|refactor|test|chore|style|perf|build|ci|revert)(\([^)]+\))?!?: .+"
)

REQUIRED_GITIGNORE_ENTRIES = [
    ".env",
    ".claude/settings.local.json",
    ".claude/CLAUDE.local.md",
]

# Files/dirs at the repo root (and other convention-governed locations) that are allowed to
# deviate from kebab-case because the convention itself calls for a different casing.
NAMING_EXEMPT = {
    "CLAUDE.md",
    "DECISIONS.md",
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    ".gitignore",
    ".gitkeep",
    ".env",
    ".env.example",
    ".mcp.json",
    "pyproject.toml",
    "settings.json",
    "settings.local.json",
    "registry.json",
    "server.py",
}

NOISE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "dist", "build", ".cache"}


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def strip_ext(name: str) -> str:
    """Strip the longest known extension so 'foo.schema.json' -> 'foo', not 'foo.schema'."""
    for suffix in (".schema.json", ".md", ".json", ".py", ".toml", ".yml", ".yaml", ".sh"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def check_json_validity(root: Path) -> dict[str, Any]:
    results = []
    candidates = [root / ".mcp.json", root / ".claude" / "settings.json", root / "mcp-servers" / "registry.json"]
    schemas_dir = root / "schemas"
    if schemas_dir.is_dir():
        candidates.extend(sorted(schemas_dir.glob("*.schema.json")))

    for path in candidates:
        rel = str(path.relative_to(root))
        if not path.exists():
            results.append({"path": rel, "status": "skip", "detail": "file does not exist"})
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            results.append({"path": rel, "status": "fail", "detail": f"invalid JSON: {exc}"})
            continue

        detail = "valid JSON"
        status = "pass"
        needs_schema_version = path.name == "registry.json" or path.name.endswith(".schema.json")
        if needs_schema_version:
            if not isinstance(data, dict) or "$schema_version" not in data:
                status = "fail"
                detail = "valid JSON but missing required '$schema_version' field"
            else:
                detail = "valid JSON with '$schema_version' field"
        results.append({"path": rel, "status": status, "detail": detail})

    failed = sum(1 for r in results if r["status"] == "fail")
    return {"results": results, "passed": failed == 0}


def check_naming(root: Path) -> dict[str, Any]:
    results = []

    def record(rel: str, ok: bool, expected: str) -> None:
        results.append(
            {
                "path": rel,
                "status": "pass" if ok else "fail",
                "detail": "matches convention" if ok else f"does not match expected pattern: {expected}",
            }
        )

    # Generic kebab-case scan over the top-level convention directories/files.
    top_level_dirs = ["mcp-servers", "schemas", "resources", "reports", "docs", "tests"]
    top_level_dirs += [str(Path(".claude") / d) for d in ("agents", "commands", "skills")]

    for entry in sorted(root.iterdir()):
        if entry.name in NOISE_DIRS or entry.name in NAMING_EXEMPT:
            continue
        if entry.name.startswith("."):
            continue
        base = strip_ext(entry.name)
        record(entry.name, bool(KEBAB_RE.match(base)), "kebab-case")

    for rel_dir in top_level_dirs:
        d = root / rel_dir
        if not d.is_dir():
            continue
        for entry in sorted(d.iterdir()):
            if entry.name in NAMING_EXEMPT or entry.name.startswith("."):
                continue
            rel = str(entry.relative_to(root))
            base = strip_ext(entry.name)
            if not KEBAB_RE.match(base):
                record(rel, False, "kebab-case")

    # Specific patterns called out in the checklist.
    mcp_dir = root / "mcp-servers"
    if mcp_dir.is_dir():
        for entry in sorted(mcp_dir.iterdir()):
            if entry.is_dir():
                rel = str(entry.relative_to(root))
                record(rel, bool(MCP_DIR_RE.match(entry.name)), "<domain>-mcp")

    schemas_dir = root / "schemas"
    if schemas_dir.is_dir():
        for entry in sorted(schemas_dir.iterdir()):
            if entry.is_file() and entry.name != ".gitkeep":
                rel = str(entry.relative_to(root))
                record(rel, bool(SCHEMA_FILE_RE.match(entry.name)), "<entity>.schema.json")

    reports_dir = root / "reports"
    if reports_dir.is_dir():
        for entry in sorted(reports_dir.iterdir()):
            if entry.is_file() and entry.name != ".gitkeep":
                rel = str(entry.relative_to(root))
                record(rel, bool(REPORT_FILE_RE.match(entry.name)), "YYYY-MM-DD-<slug>.md")

    failed = sum(1 for r in results if r["status"] == "fail")
    return {"results": results, "passed": failed == 0}


def check_gitignore(root: Path) -> dict[str, Any]:
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return {
            "results": [{"path": ".gitignore", "status": "fail", "detail": "file does not exist"}],
            "passed": False,
        }

    lines = {line.strip() for line in gitignore.read_text(encoding="utf-8").splitlines()}
    results = []
    for entry in REQUIRED_GITIGNORE_ENTRIES:
        ok = entry in lines
        results.append(
            {
                "entry": entry,
                "status": "pass" if ok else "fail",
                "detail": "present" if ok else "missing from .gitignore",
            }
        )
    failed = sum(1 for r in results if r["status"] == "fail")
    return {"results": results, "passed": failed == 0}


def run_git(root: Path, args: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def is_git_repo(root: Path) -> bool:
    code, out, _ = run_git(root, ["rev-parse", "--is-inside-work-tree"])
    return code == 0 and out.strip() == "true"


def check_env_not_tracked(root: Path) -> dict[str, Any]:
    if not is_git_repo(root):
        log("env_not_tracked: skipped, target is not a git repository")
        return {"status": "skip", "detail": "not a git repository", "passed": True}

    code, out, err = run_git(root, ["ls-files", "--", ".env"])
    if code != 0:
        log(f"env_not_tracked: skipped, 'git ls-files' failed: {err.strip()}")
        return {"status": "skip", "detail": f"git ls-files failed: {err.strip()}", "passed": True}

    tracked = out.strip()
    if tracked:
        return {"status": "fail", "detail": "'.env' is tracked by git — remove it from version control", "passed": False}
    return {"status": "pass", "detail": "'.env' is not tracked", "passed": True}


def check_conventional_commits(root: Path) -> dict[str, Any]:
    if not is_git_repo(root):
        log("conventional_commits: skipped, target is not a git repository")
        return {"results": [], "status": "skip", "detail": "not a git repository", "passed": True}

    code, out, err = run_git(root, ["log", "-10", "--format=%H%x1f%s"])
    if code != 0:
        log(f"conventional_commits: skipped, 'git log' failed: {err.strip()}")
        return {"results": [], "status": "skip", "detail": f"git log failed: {err.strip()}", "passed": True}

    lines = [line for line in out.split("\n") if line.strip()]
    if not lines:
        log("conventional_commits: skipped, repository has no commits")
        return {"results": [], "status": "skip", "detail": "no commits found", "passed": True}

    results = []
    for line in lines:
        sha, _, subject = line.partition("\x1f")
        ok = bool(CONVENTIONAL_COMMIT_RE.match(subject))
        results.append(
            {
                "sha": sha[:10],
                "subject": subject,
                "status": "pass" if ok else "fail",
                "detail": "matches conventional-commit format" if ok else "does not start with a conventional-commit type (feat/fix/docs/refactor/test/chore/style/perf/build/ci/revert)",
            }
        )
    failed = sum(1 for r in results if r["status"] == "fail")
    return {"results": results, "status": "ran", "passed": failed == 0}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="audit.py",
        description="Run the mechanically-checkable portion of make-a-monorepo's audit checklist.",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--path",
        metavar="DIR",
        default=".",
        help="Directory to audit (default: current directory).",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="Indent level for the JSON printed to stdout (default: 2). Use 0 for compact output.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    root = Path(args.path).resolve()
    if not root.is_dir():
        log(f"error: --path '{args.path}' is not a directory")
        return EXIT_ERROR

    log(f"auditing {root}")

    json_validity = check_json_validity(root)
    naming = check_naming(root)
    gitignore = check_gitignore(root)
    env_not_tracked = check_env_not_tracked(root)
    conventional_commits = check_conventional_commits(root)

    checks = {
        "json_validity": json_validity,
        "naming": naming,
        "gitignore": gitignore,
        "env_not_tracked": env_not_tracked,
        "conventional_commits": conventional_commits,
    }

    all_passed = all(group["passed"] for group in checks.values())

    total = 0
    passed_count = 0
    failed_count = 0
    for group in checks.values():
        if "results" in group:
            for r in group["results"]:
                total += 1
                if r["status"] == "pass":
                    passed_count += 1
                elif r["status"] == "fail":
                    failed_count += 1
        elif "status" in group and group["status"] != "skip":
            total += 1
            if group["status"] == "pass":
                passed_count += 1
            elif group["status"] == "fail":
                failed_count += 1

    report = {
        "target": str(root),
        "checks": checks,
        "summary": {
            "total_checks": total,
            "passed": passed_count,
            "failed": failed_count,
        },
        "passed": all_passed,
    }

    indent = args.indent if args.indent > 0 else None
    print(json.dumps(report, indent=indent))

    verdict = "PASS" if all_passed else "FAIL"
    log(f"{verdict}: {passed_count}/{total} mechanical checks passed")

    return EXIT_PASS if all_passed else EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
