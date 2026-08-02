#!/usr/bin/env python3
"""
check_preconditions.py — gate for evidence-linked work objects.

Verifies that a work/<id>-<slug>/ directory actually satisfies the
preconditions for a status transition (e.g. draft -> in-review,
in-review -> approved) instead of letting an agent assert it.

This does not trust prose. It checks:
  - required files exist and are non-empty
  - run-manifest.json is valid JSON with the required keys
  - commit_after in run-manifest.json matches the actual current
    HEAD of the repo the work dir lives in (git-aware check)
  - commit_before exists in history, diff.patch parses as real git
    diff output, and every path it touches is among the files git
    reports changed between commit_before and commit_after (a
    name-level consistency check — a path-filtered diff passes, a
    hand-written or mismatched diff does not)
  - for in-review -> approved: review.md exists, has YAML frontmatter
    whose status field is 'approved', and its body references each
    evidence file by name (a crude but effective check that the
    reviewer didn't write a generic "looks good")

Exit code 0 = preconditions satisfied. Non-zero = blocked, with a
human-readable reason on stderr. Agents should treat a non-zero exit
as a hard stop, not a warning to note and continue past.

Usage:
    python check_preconditions.py <work_dir> --transition in-review
    python check_preconditions.py <work_dir> --transition approved
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REQUIRED_FOR_IN_REVIEW = [
    "spec.md",
    "evidence/diff.patch",
    "evidence/test-output.txt",
    "evidence/run-manifest.json",
]

REQUIRED_FOR_APPROVED = REQUIRED_FOR_IN_REVIEW + ["review.md"]


def fail(msg: str) -> None:
    print(f"BLOCKED: {msg}", file=sys.stderr)
    sys.exit(1)


def check_files_exist(work_dir: Path, required: list[str]) -> None:
    missing = [f for f in required if not (work_dir / f).is_file()]
    if missing:
        fail(f"missing required file(s): {', '.join(missing)}")
    empty = [f for f in required if (work_dir / f).stat().st_size == 0]
    if empty:
        fail(f"required file(s) present but empty: {', '.join(empty)}")


def load_manifest(work_dir: Path) -> dict:
    manifest_path = work_dir / "evidence" / "run-manifest.json"
    try:
        data = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as e:
        fail(f"run-manifest.json is not valid JSON: {e}")
    required_keys = {"commit_before", "commit_after", "branch",
                      "generated_at", "diff_command", "test_command"}
    missing_keys = required_keys - data.keys()
    if missing_keys:
        fail(f"run-manifest.json missing key(s): {', '.join(sorted(missing_keys))}")
    return data


def find_repo_root(work_dir: Path) -> Path:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=work_dir, capture_output=True, text=True, check=True,
        )
        return Path(out.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        fail("could not resolve a git repo root from the work directory "
             "(is this folder inside the repo it's tracking evidence for?)")


def check_sha_matches_head(repo_root: Path, manifest: dict) -> None:
    out = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root, capture_output=True, text=True,
    )
    if out.returncode != 0:
        fail("could not read HEAD of the repo — is it a valid git repo?")
    current_head = out.stdout.strip()
    manifest_sha = manifest["commit_after"]

    # Accept short-SHA prefixes too.
    if not current_head.startswith(manifest_sha) and not manifest_sha.startswith(current_head):
        fail(
            f"run-manifest.json commit_after ({manifest_sha}) does not match "
            f"the repo's current HEAD ({current_head}). Evidence is stale — "
            f"regenerate diff.patch and test-output.txt against HEAD, or "
            f"note explicitly that HEAD moved since evidence was captured."
        )

    # Confirm the SHA actually exists in history (not fabricated).
    check = subprocess.run(
        ["git", "cat-file", "-e", manifest_sha],
        cwd=repo_root, capture_output=True,
    )
    if check.returncode != 0:
        fail(f"commit_after ({manifest_sha}) does not exist in this repo's history")


def check_diff_consistency(repo_root: Path, work_dir: Path, manifest: dict) -> None:
    commit_before = manifest["commit_before"]
    commit_after = manifest["commit_after"]

    check = subprocess.run(
        ["git", "cat-file", "-e", commit_before],
        cwd=repo_root, capture_output=True,
    )
    if check.returncode != 0:
        fail(f"commit_before ({commit_before}) does not exist in this repo's history")

    patch_text = (work_dir / "evidence" / "diff.patch").read_text(errors="replace")
    patch_paths = set(re.findall(r"^diff --git a/.* b/(.*)$", patch_text, re.MULTILINE))
    if not patch_paths:
        fail("diff.patch does not look like git diff output (no 'diff --git' "
             "headers) — evidence must be captured from the real command, "
             "not written by hand")

    out = subprocess.run(
        ["git", "diff", "--name-only", f"{commit_before}..{commit_after}"],
        cwd=repo_root, capture_output=True, text=True,
    )
    if out.returncode != 0:
        fail(f"could not compute git diff --name-only "
             f"{commit_before}..{commit_after}: {out.stderr.strip()}")
    expected = set(out.stdout.splitlines())
    extras = sorted(patch_paths - expected)
    if extras:
        fail("diff.patch touches file(s) not changed between commit_before "
             f"and commit_after: {', '.join(extras)}. Recapture the diff "
             "with the real diff_command from run-manifest.json.")


def check_review_references_evidence(work_dir: Path) -> None:
    review_text = (work_dir / "review.md").read_text()
    lines = review_text.splitlines()
    if not lines or lines[0].strip() != "---":
        fail("review.md has no YAML frontmatter (file must start with '---')")
    try:
        end = next(i for i, line in enumerate(lines[1:], start=1)
                   if line.strip() == "---")
    except StopIteration:
        fail("review.md frontmatter is never closed with '---'")
    frontmatter = "\n".join(lines[1:end])
    match = re.search(r"^status:\s*(\S+)", frontmatter, re.MULTILINE)
    if not match:
        fail("review.md frontmatter has no status field")
    decision = match.group(1)
    if decision != "approved":
        fail(f"review.md decision is '{decision}', not 'approved' — "
             "the approved transition requires an approving review")

    evidence_files = [
        p.name for p in (work_dir / "evidence").iterdir() if p.is_file()
    ]
    unreferenced = [f for f in evidence_files if f not in review_text]
    if unreferenced:
        fail(
            "review.md does not mention these evidence file(s) by name: "
            f"{', '.join(unreferenced)}. A review must cite what it "
            "inspected, not summarize generally."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work_dir", type=Path)
    parser.add_argument(
        "--transition", required=True, choices=["in-review", "approved"]
    )
    args = parser.parse_args()

    work_dir: Path = args.work_dir.resolve()
    if not work_dir.is_dir():
        fail(f"{work_dir} is not a directory")

    if args.transition == "in-review":
        check_files_exist(work_dir, REQUIRED_FOR_IN_REVIEW)
        manifest = load_manifest(work_dir)
        repo_root = find_repo_root(work_dir)
        check_sha_matches_head(repo_root, manifest)
        check_diff_consistency(repo_root, work_dir, manifest)
        print(f"OK: {work_dir.name} satisfies preconditions for 'in-review'.")

    elif args.transition == "approved":
        check_files_exist(work_dir, REQUIRED_FOR_APPROVED)
        manifest = load_manifest(work_dir)
        repo_root = find_repo_root(work_dir)
        check_sha_matches_head(repo_root, manifest)
        check_diff_consistency(repo_root, work_dir, manifest)
        check_review_references_evidence(work_dir)
        print(f"OK: {work_dir.name} satisfies preconditions for 'approved'.")

    sys.exit(0)


if __name__ == "__main__":
    main()
