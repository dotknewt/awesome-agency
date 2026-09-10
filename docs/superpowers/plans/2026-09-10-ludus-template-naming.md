# Ludus Template Naming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a canonical Ludus template naming skill, a deterministic validator, and complete bundle and marketplace integration.

**Architecture:** Keep naming judgment and migration procedure in a standalone pooled skill, with syntax enforcement in a dependency-free Python CLI shipped inside that skill. Update the two existing template-maintenance skills to reconstruct canonical names, then expose the new skill through the Ludus bundle, OpenCode installer, generated marketplace, CI, and release metadata.

**Tech Stack:** Markdown Agent Skills, Python 3 standard library, repository shell validators, generated JSON marketplace metadata, GitHub Actions YAML

**Spec:** `docs/superpowers/specs/2026-09-10-ludus-template-naming-design.md`

## Global Constraints

- Scope is the `ludus-toolkit` naming guidance and validation; do not migrate `dotknewt/awesome-ludus-sauce` templates.
- Hyphens separate semantic fields; underscores join semantic parts within fields.
- Numeric release components use dots; semantic alphanumeric release combinations use underscores.
- Every name ends in an explicit lowercase two-letter locale, including default `us`.
- Linux shape: `<os>-<release>-<arch>-<role>[-<qualifier>...]-<locale>`.
- Windows client shape: `windows-<release>-<arch>[-<qualifier>...]-<locale>`.
- Windows Server shape: `windows-server-<release>-<arch>[-<qualifier>...]-<locale>`.
- Supported families are `ubuntu`, `debian`, `kali`, `windows`, and `windows-server`; supported architectures are `x64` and `arm64`; supported Linux roles are `desktop` and `server`.
- The validator uses only the Python standard library, reports every supplied name, and never rewrites names.
- The directory and top-level `.pkr.hcl` basenames match; the built name is exactly `<basename>-template`.
- Standalone micro-installs must be self-contained; existing maintenance skills must not assume access to a sibling plugin root.
- Treat `.claude-plugin/marketplace.json` as generated output and never hand-edit it.
- Bump `ludus-toolkit` from `0.3.0` to `0.4.0` and add matching release notes in the same change.
- Preserve unrelated work, including the untracked `plan.md`.
- Do not create commits unless the user explicitly requests commits before or during execution.

## File Map

- Create `skills/ludus-template-naming/SKILL.md`: canonical grammar, semantic classification workflow, safe rename procedure, and validator usage.
- Create `skills/ludus-template-naming/scripts/validate_template_name.py`: syntax-only command-line validator.
- Create `.github/scripts/test-ludus-template-naming.py`: dependency-free subprocess regression tests for valid, invalid, and mixed inputs.
- Modify `skills/change-template-input-language/SKILL.md`: replace position-preserving locale renames with canonical reconstruction.
- Modify `skills/update-os-template/SKILL.md`: replace source-style preservation with canonical reconstruction.
- Create `plugins/ludus-toolkit/skills/ludus-template-naming`: relative symlink to the pooled skill.
- Modify `plugins/ludus-toolkit/opencode/install.py`: install seven skills and update CLI text.
- Modify `.github/scripts/test-ludus-opencode-install.py`: expect seven skills and verify the validator is copied byte-for-byte.
- Modify `plugins/ludus-toolkit/opencode/README.md`: document seven installed skills.
- Modify `.github/workflows/validate.yml`: run the naming validator regression test in CI.
- Modify `plugins/ludus-toolkit/README.md`: list the new skill.
- Modify `plugins/ludus-toolkit/.claude-plugin/plugin.json`: bump version and mention template naming.
- Modify `plugins/ludus-toolkit/RELEASE-NOTES.md`: explain why canonical naming and validation were added.
- Regenerate `.claude-plugin/marketplace.json`: add the standalone skill entry from the source frontmatter.

---

### Task 1: Validator CLI

**Files:**
- Create: `.github/scripts/test-ludus-template-naming.py`
- Create: `skills/ludus-template-naming/scripts/validate_template_name.py`

**Interfaces:**
- Consumes: one or more CLI name arguments.
- Produces: `validate_name(name: str) -> str | None`, where `None` means valid and a string is the actionable rejection reason; CLI exit `0` only when all arguments are valid.

- [ ] **Step 1: Write the failing subprocess test**

Create `.github/scripts/test-ludus-template-naming.py` with these exact case groups and a helper that preserves stdout, stderr, and exit status:

```python
#!/usr/bin/env python3
"""Exercise the Ludus template-name validator as an external command."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "skills" / "ludus-template-naming" / "scripts" / "validate_template_name.py"

VALID_NAMES = (
    "ubuntu-24.04.2-x64-desktop-no",
    "ubuntu-24.04.2-x64-desktop-no-template",
    "debian-13.2-x64-server-no",
    "kali-2024.4-x64-desktop-no",
    "windows-11_22h2-x64-enterprise-no",
    "windows-server-2019-x64-no_security_updates-us",
    "windows-server-2019-x64-no_security_updates-no",
    "windows-11_22h2-arm64-us",
)

INVALID_NAMES = {
    "ubuntu-24.04.2-x64-no-desktop": "Linux role must be desktop or server",
    "debian-13-2-x64-server-no": "numeric release components must use dots",
    "windows-server-2019-x64-no-security-updates": "final locale must be two lowercase letters",
    "windows-server-2019-x64-no-security-updates-us": "write the multiword qualifier as no_security_updates",
    "windows-server-2019-x64-no_security_updates": "final locale must be two lowercase letters",
    "Ubuntu-24.04.2-x64-desktop-no": "lowercase ASCII",
    "fedora-41-x64-desktop-us": "unknown OS family",
    "ubuntu-24.04.2-amd64-desktop-us": "architecture must be x64 or arm64",
    "ubuntu-24.04.2-x64-workstation-us": "Linux role must be desktop or server",
    "ubuntu-24..04-x64-desktop-us": "repeated separator",
    "ubuntu-24.04.2-x64-desktop_us": "expected Linux shape",
    "ubuntu-24.04.2-x64-desktop-us-template-template": "-template is allowed only as one terminal suffix",
    "ubuntu-template-24.04.2-x64-desktop-us": "-template is allowed only as one terminal suffix",
    "windows-11_22h2-x64-enterprise-no-extra": "final locale must be two lowercase letters",
    "debian-13_2-x64-server-us": "numeric release components must use dots",
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
```

- [ ] **Step 2: Run the test and verify RED**

Run: `python3 .github/scripts/test-ludus-template-naming.py`

Expected: FAIL because `skills/ludus-template-naming/scripts/validate_template_name.py` does not exist.

- [ ] **Step 3: Implement the minimal validator**

Create `skills/ludus-template-naming/scripts/validate_template_name.py` with this structure and validation order so errors stay deterministic:

```python
#!/usr/bin/env python3
"""Validate canonical Ludus template basenames and built names."""

from __future__ import annotations

import argparse
import re
import sys


LINUX_FAMILIES = {"ubuntu", "debian", "kali"}
ARCHITECTURES = {"x64", "arm64"}
LINUX_ROLES = {"desktop", "server"}
ALLOWED_NAME = re.compile(r"^[a-z0-9._-]+$")
RELEASE = re.compile(r"^[0-9]+(?:\.[0-9]+)*(?:_[a-z0-9]*[a-z][a-z0-9]*)*$")
QUALIFIER = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
LOCALE = re.compile(r"^[a-z]{2}$")


def validate_name(name: str) -> str | None:
    if not name or not name.isascii() or not ALLOWED_NAME.fullmatch(name):
        return "name must use lowercase ASCII letters, digits, dots, underscores, and hyphens"
    if any(separator in name for separator in ("--", "__", "..")):
        return "name contains a repeated separator"

    suffix_count = name.count("-template")
    if suffix_count:
        if suffix_count != 1 or not name.endswith("-template"):
            return "-template is allowed only as one terminal suffix"
        name = name.removesuffix("-template")
        if "-template" in name:
            return "built name must contain exactly one terminal -template suffix"

    fields = name.split("-")
    if not fields or fields[0] not in LINUX_FAMILIES | {"windows"}:
        return "unknown OS family; expected ubuntu, debian, kali, windows, or windows-server"

    if fields[0] in LINUX_FAMILIES:
        if (
            len(fields) >= 6
            and fields[1].isdigit()
            and fields[2].isdigit()
            and fields[3] in ARCHITECTURES
        ):
            return "numeric release components must use dots"
        if len(fields) < 5:
            return "expected Linux shape: <os>-<release>-<arch>-<role>[-<qualifier>...]-<locale>"
        release, arch, role = fields[1:4]
        qualifiers = fields[4:-1]
    elif len(fields) > 1 and fields[1] == "server":
        if len(fields) < 5:
            return "expected Windows Server shape: windows-server-<release>-<arch>[-<qualifier>...]-<locale>"
        release, arch = fields[2:4]
        role = None
        qualifiers = fields[4:-1]
    else:
        if len(fields) < 4:
            return "expected Windows client shape: windows-<release>-<arch>[-<qualifier>...]-<locale>"
        release, arch = fields[1:3]
        role = None
        qualifiers = fields[3:-1]

    locale = fields[-1]
    if not LOCALE.fullmatch(locale):
        return "final locale must be two lowercase letters"
    if not RELEASE.fullmatch(release):
        if re.fullmatch(r"[0-9]+(?:_[0-9]+)+", release):
            return "numeric release components must use dots"
        return "release must start with digits and use dots for numeric parts or underscores for semantic alphanumeric parts"
    if arch not in ARCHITECTURES:
        return "architecture must be x64 or arm64"
    if role is not None and role not in LINUX_ROLES:
        return "Linux role must be desktop or server"
    ambiguous_qualifier = ["no", "security", "updates"]
    if any(
        qualifiers[index : index + 3] == ambiguous_qualifier
        for index in range(len(qualifiers) - 2)
    ):
        return "write the multiword qualifier as no_security_updates"
    if any(not QUALIFIER.fullmatch(qualifier) for qualifier in qualifiers):
        return "qualifiers must use lowercase alphanumerics with underscores inside a field"
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate canonical Ludus template basenames and built names."
    )
    parser.add_argument("names", metavar="NAME", nargs="+")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    failed = False
    for name in args.names:
        reason = validate_name(name)
        if reason is None:
            print(f"valid: {name}")
        else:
            print(f"invalid: {name}: {reason}", file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

While implementing, resolve any mismatch between a test's expected error and the specified validation order by preserving the most actionable error. Do not broaden accepted families, architectures, roles, release forms, or locale syntax.

- [ ] **Step 4: Make both scripts executable and run GREEN**

Run:

```bash
chmod +x skills/ludus-template-naming/scripts/validate_template_name.py
chmod +x .github/scripts/test-ludus-template-naming.py
python3 .github/scripts/test-ludus-template-naming.py
```

Expected: `Ludus template naming checks passed` and exit `0`.

- [ ] **Step 5: Exercise the documented direct CLI contract**

Run:

```bash
python3 skills/ludus-template-naming/scripts/validate_template_name.py \
  ubuntu-24.04.2-x64-desktop-no \
  windows-server-2019-x64-no_security_updates-us-template
```

Expected: two `valid:` lines and exit `0`.

### Task 2: Naming Guidance And Maintenance-Skill Integration

**Files:**
- Create: `skills/ludus-template-naming/SKILL.md`
- Modify: `skills/change-template-input-language/SKILL.md:22-46,61-75,159-182`
- Modify: `skills/update-os-template/SKILL.md:24-65,101-123`

**Interfaces:**
- Consumes: a legacy or proposed Ludus template basename plus evidence from the template directory.
- Produces: a canonical basename, matching `.pkr.hcl` basename, `<basename>-template` built name, and updated exact references; invokes `scripts/validate_template_name.py` for syntax checks.

- [ ] **Step 1: Run RED guidance scenarios without the new skill**

Dispatch three fresh general-purpose subagents. Tell each to use only the currently shipped `change-template-input-language` or `update-os-template` skill and not to read `docs/superpowers/`. Use these prompts:

```text
Scenario A: A template directory is ubuntu-24.04.2-x64-us-desktop. Its Ubuntu
autoinstall keyboard is us with an empty variant. Describe the exact rename and
vm_name changes needed to switch only the keyboard to standard Norwegian.
```

```text
Scenario B: A source template is debian-13-2-x64-no-server, where installer
evidence proves no is the Norwegian keyboard token and server is the role.
Describe the target basename for release 13.6.0 without changing any other
semantics.
```

```text
Scenario C: A source template is win2019-server-x64-no-security-updates and its
installer uses a US keyboard. Describe whether no is a locale or part of a
feature qualifier, then give a canonical directory name and vm_name.
```

Record the outputs in the execution log, not in the repository. RED is established when Scenario A or B preserves legacy field order/separators, or Scenario C cannot derive the canonical shape from existing shipped guidance. If all three already produce the approved grammar, stop and report that the proposed skill has no observed guidance gap before authoring it.

- [ ] **Step 2: Write the standalone naming skill**

Create `skills/ludus-template-naming/SKILL.md` with imperative/infinitive prose and the following concrete content:

```markdown
---
name: ludus-template-naming
description: Use when naming, renaming, reviewing, or validating Ludus Packer OS templates, especially when legacy names have ambiguous locale, role, edition, release, or feature tokens such as no or no-security-updates.
---

# Ludus Template Naming

Apply one canonical grammar to Ludus Packer template directories, top-level
`.pkr.hcl` files, `vm_name` values, and exact consuming references. Preserve the
template's semantics; normalize only their representation.

## Canonical Grammar

Use hyphens between semantic fields and underscores within one semantic field.
Use lowercase ASCII throughout. Keep numeric release components dot-separated,
and join semantic alphanumeric release parts with underscores.

| Family | Shape |
| --- | --- |
| Linux | `<os>-<release>-<arch>-<role>[-<qualifier>...]-<locale>` |
| Windows client | `windows-<release>-<arch>[-<qualifier>...]-<locale>` |
| Windows Server | `windows-server-<release>-<arch>[-<qualifier>...]-<locale>` |

Accept `ubuntu`, `debian`, `kali`, `windows`, and `windows-server`. Use `x64`
or `arm64` for architecture. Require `desktop` or `server` as the Linux role.
Encode Windows Server's role in the family prefix and omit a separate role from
Windows client names.

Require a final lowercase two-letter locale token, including default `us`.
Treat that token as filename metadata only. Validate the physical keyboard,
XKB layout and variant, or Windows InputLocale independently.

Use dots for numeric releases such as `24.04.2`, `13.2`, and `2024.4`. Use an
underscore when a release combines a numeric product release with a semantic
alphanumeric part, as in `11_22h2`. Use underscores for multiword qualifiers,
as in `no_security_updates`; keep distinct qualifiers as separate hyphen fields.

## Examples

```text
ubuntu-24.04.2-x64-desktop-no
debian-13.2-x64-server-no
kali-2024.4-x64-desktop-no
windows-11_22h2-x64-enterprise-no
windows-server-2019-x64-no_security_updates-us
windows-server-2019-x64-no_security_updates-no
```

Set the top-level `.pkr.hcl` basename equal to the directory basename. Set the
built template name to that basename plus exactly one `-template` suffix.

## Classification Workflow

1. Inspect the complete template directory, top-level `.pkr.hcl`, installer
   answer files, and exact consuming references before interpreting a legacy
   basename.
2. Classify the OS family, release, architecture, Linux role when applicable,
   qualifiers, and locale from file content rather than token position.
3. Ask one short question when evidence does not resolve a token. Never assume
   `no` means Norwegian; it can belong to `no_security_updates`.
4. Construct the basename with the family-specific shape and separators above.
5. Stop if the target directory or target `.pkr.hcl` already exists.
6. Rename the directory and top-level `.pkr.hcl`, set `vm_name`, and update
   exact old-name references. Do not blindly replace short tokens.
7. Search for the old full basename and inspect every remaining match.

Do not change locale, role, edition, feature, release, or architecture merely
to satisfy naming. Do not create backward-compatible aliases unless explicitly
requested.

## Validate Names

Resolve `scripts/validate_template_name.py` relative to this `SKILL.md`, not
relative to the caller's current working directory. Execute that resolved path
on both the basename and built name:

```bash
python3 /absolute/resolved/skill/path/scripts/validate_template_name.py \
  ubuntu-24.04.2-x64-desktop-no \
  ubuntu-24.04.2-x64-desktop-no-template
```

Interpret validator success as syntax validation only. Manually verify that
the final locale matches installer evidence, directory and `.pkr.hcl` basenames
match, `vm_name` is exact, and all consuming references were updated. The
validator never reads HCL, infers semantics, or renames files.

## Common Mistakes

| Mistake | Correction |
| --- | --- |
| Put locale before Linux role | Put locale in the final field |
| Write `13-2` or `13_2` | Write numeric release `13.2` |
| Write `no-security-updates` | Write one qualifier `no_security_updates` |
| Omit default US locale | Append explicit `us` |
| Infer locale from `no` alone | Inspect installer keyboard configuration |
| Add `-template` to files | Add it only to the built `vm_name` |

## Completion Report

Report the old and new basenames, semantic field classification and evidence,
every renamed or edited file, updated references, validator results, and checks
that could not run.
```

- [ ] **Step 3: Update locale-change guidance to reconstruct names**

In `skills/change-template-input-language/SKILL.md`:

- Replace “Preserve all other basename components exactly” with a concise standalone grammar summary covering family shapes, dots for numeric releases, underscores within semantic fields, Linux role position, and final explicit locale.
- Replace Required Rename step 1 with classification from directory contents followed by full canonical reconstruction. Use `ubuntu-24.04.2-x64-us-desktop` to `ubuntu-24.04.2-x64-desktop-no` as the legacy-to-canonical example.
- Keep collision checks, directory and `.pkr.hcl` renames, in-place behavior, and release-neutral support-file rules unchanged.
- Add verification of both canonical basename and built name using the grammar summary; do not reference the sibling naming skill's script because this skill is independently installable.
- Keep keyboard-system distinctions and all OS-specific answer-file guidance unchanged.

- [ ] **Step 4: Update OS-release guidance to reconstruct names**

In `skills/update-os-template/SKILL.md`:

- Keep candidate matching by architecture, role, locale, edition, and feature semantics.
- Replace source-style preservation in Workflow step 5 with full canonical reconstruction using the three family shapes.
- State that numeric releases use dots, semantic alphanumeric release parts use underscores, multiword qualifiers use underscores, and locale is always final.
- Add examples converting legacy `debian-13-2-x64-no-server` to `debian-13.6.0-x64-server-no` and preserving `windows-server-2019-x64-no_security_updates-us` qualifiers and locale during a release change.
- Add manual canonical-name checks to Verification without assuming the sibling naming validator exists.
- Preserve all ISO, checksum, Debian archive, Ubuntu source-label, and minimal release-edit rules.

- [ ] **Step 5: Validate skill structure and frontmatter**

Run:

```bash
python3 .claude/skills/skill-development/scripts/validate_skill.py skills/ludus-template-naming/SKILL.md
bash hooks/hooks-toolkit/scripts/validate-skill-frontmatter.sh skills/ludus-template-naming/SKILL.md
bash hooks/hooks-toolkit/scripts/validate-skill-frontmatter.sh skills/change-template-input-language/SKILL.md
bash hooks/hooks-toolkit/scripts/validate-skill-frontmatter.sh skills/update-os-template/SKILL.md
```

Expected: all four commands exit `0`; the Python validator reports no broken `scripts/validate_template_name.py` reference.

- [ ] **Step 6: Run GREEN guidance scenarios**

Dispatch three fresh general-purpose subagents with the same Scenario A, B, and C prompts from Step 1. Explicitly tell them to read the modified relevant maintenance skill and `skills/ludus-template-naming/SKILL.md` first.

Expected:

- Scenario A returns `ubuntu-24.04.2-x64-desktop-no` and `ubuntu-24.04.2-x64-desktop-no-template` without changing display/system locale.
- Scenario B returns `debian-13.6.0-x64-server-no`.
- Scenario C identifies `no_security_updates` as a qualifier, uses explicit locale `us`, and returns `windows-server-2019-x64-no_security_updates-us` plus its `-template` built name.

- [ ] **Step 7: Perform qualitative skill review**

Dispatch a fresh general-purpose reviewer with this prompt:

```text
Review skills/ludus-template-naming/SKILL.md against
docs/superpowers/specs/2026-09-10-ludus-template-naming-design.md and the
repository's skill-development conventions. Check trigger specificity,
imperative prose, progressive disclosure, self-contained resources, canonical
grammar accuracy, ambiguity safeguards, and validator instructions. Report only
concrete findings with file and line references; do not edit files.
```

Fix every concrete correctness or portability finding, rerun Step 5, and rerun the affected GREEN scenario. Do not add speculative complexity or duplicate the full skill into either maintenance skill.

### Task 3: Bundle And OpenCode Packaging

**Files:**
- Create: `plugins/ludus-toolkit/skills/ludus-template-naming` symlink
- Modify: `plugins/ludus-toolkit/opencode/install.py:17-24,180-183`
- Modify: `.github/scripts/test-ludus-opencode-install.py:20-27,69-80`
- Modify: `plugins/ludus-toolkit/opencode/README.md:3-6,53-57`
- Modify: `plugins/ludus-toolkit/README.md:3-9`

**Interfaces:**
- Consumes: pooled skill tree at `skills/ludus-template-naming/`.
- Produces: bundle-local symlink and a real-file OpenCode installation containing `SKILL.md` and `scripts/validate_template_name.py` byte-for-byte.

- [ ] **Step 1: Extend the installer test first**

Add `"ludus-template-naming"` to `SKILL_NAMES` in `.github/scripts/test-ludus-opencode-install.py`. Change the repeat assertion to:

```python
assert "7 skill(s) already current" in repeat.stdout
```

After the first `assert_installed(clean)`, add an explicit executable-resource assertion:

```python
installed_validator = (
    clean
    / ".opencode"
    / "skills"
    / "ludus-template-naming"
    / "scripts"
    / "validate_template_name.py"
)
source_validator = SKILL_SOURCE / "ludus-template-naming" / "scripts" / "validate_template_name.py"
assert installed_validator.read_bytes() == source_validator.read_bytes()
```

- [ ] **Step 2: Run the focused test and verify RED**

Fetch the same schema CI uses and run the installer test:

```bash
curl --fail --silent --show-error --location \
  https://opencode.ai/config.json \
  --output /tmp/opencode-schema.json
python3 .github/scripts/test-ludus-opencode-install.py /tmp/opencode-schema.json
```

Expected: FAIL because the new bundle symlink and installer entry do not exist yet.

- [ ] **Step 3: Add the bundle symlink and installer entry**

Run:

```bash
test -d plugins/ludus-toolkit/skills
ln -s ../../../skills/ludus-template-naming plugins/ludus-toolkit/skills/ludus-template-naming
```

Add `"ludus-template-naming"` to `SKILL_NAMES` in `plugins/ludus-toolkit/opencode/install.py`, preserving alphabetical order. Change the argparse description from “six skills” to “seven skills.”

- [ ] **Step 4: Update bundle and OpenCode documentation**

In `plugins/ludus-toolkit/README.md`, add `ludus-template-naming` to the linked Skills list and describe the toolkit as covering OS template naming and maintenance.

In `plugins/ludus-toolkit/opencode/README.md`, change both occurrences of “six” to “seven.” Keep the instruction to copy complete skill directories so the validator script is included.

- [ ] **Step 5: Run GREEN and inspect materialization**

Run:

```bash
python3 .github/scripts/test-ludus-opencode-install.py /tmp/opencode-schema.json
test -L plugins/ludus-toolkit/skills/ludus-template-naming
test "$(readlink plugins/ludus-toolkit/skills/ludus-template-naming)" = "../../../skills/ludus-template-naming"
```

Expected: installer checks pass, the bundle path is a symlink, and its target is the pooled skill.

### Task 4: CI, Release, And Marketplace Integration

**Files:**
- Modify: `.github/workflows/validate.yml:26-33`
- Modify: `plugins/ludus-toolkit/.claude-plugin/plugin.json:3-4`
- Modify: `plugins/ludus-toolkit/RELEASE-NOTES.md:1-3`
- Regenerate: `.claude-plugin/marketplace.json`

**Interfaces:**
- Consumes: the tested pooled skill and bundle symlink from prior tasks.
- Produces: CI enforcement, `ludus-toolkit` version `0.4.0`, matching release notes, and a generated `ludus-template-naming` micro-entry at version `1.0.0`.

- [ ] **Step 1: Add the validator regression test to CI**

In the `opencode` job, add this step before the JSON Schema dependency installation:

```yaml
      - name: Validate Ludus template naming
        run: python .github/scripts/test-ludus-template-naming.py
```

Keep the existing OpenCode schema and installer test unchanged apart from the seven-skill assertions already made.

- [ ] **Step 2: Bump bundle metadata and write release rationale**

In `plugins/ludus-toolkit/.claude-plugin/plugin.json`, set `"version": "0.4.0"` and expand the description's OS-template phrase to include canonical template naming without changing repository, author, license, or keywords.

Insert this release entry above v0.3.0 in `plugins/ludus-toolkit/RELEASE-NOTES.md`:

```markdown
## v0.4.0 (2026-09-10)

### Skills

- **Ludus OS templates now have one canonical, machine-checkable naming
  grammar.** Legacy names used the same short tokens for locale and feature
  meaning and varied field order by OS family, making maintenance workflows
  prone to silent misclassification. The new `ludus-template-naming` skill and
  dependency-free validator require explicit final locales, semantic field
  ordering, and unambiguous separators; the locale-change and OS-update skills
  now reconstruct that form instead of preserving legacy positions.
```

- [ ] **Step 3: Regenerate marketplace output**

Run: `python3 .github/scripts/generate-marketplace.py`

Inspect `.claude-plugin/marketplace.json` and confirm the generated entry has:

```json
{
  "name": "ludus-template-naming",
  "version": "1.0.0",
  "source": "./skills/ludus-template-naming",
  "strict": false
}
```

The generated entry also contains the description derived from `SKILL.md`; do not edit the JSON directly.

- [ ] **Step 4: Run focused release and marketplace checks**

Run:

```bash
python3 .github/scripts/generate-marketplace.py --check
python3 .github/scripts/check-plugin-root-refs.py
python3 .github/scripts/check-host-compat.py
python3 hooks/steward/scripts/release-notes-audit.py --all
bash hooks/hooks-toolkit/scripts/validate-plugin-json.sh plugins/ludus-toolkit/.claude-plugin/plugin.json
```

Expected: every command exits `0`; host compatibility recognizes the standalone skill without a new exception.

### Task 5: Full Verification

**Files:**
- Verify all files from Tasks 1-4; make no unrelated edits.

**Interfaces:**
- Consumes: completed implementation.
- Produces: fresh evidence that behavior, packaging, manifests, release metadata, and formatting pass repository checks.

- [ ] **Step 1: Run behavior and installer tests**

Run:

```bash
python3 .github/scripts/test-ludus-template-naming.py
python3 .github/scripts/test-ludus-opencode-install.py /tmp/opencode-schema.json
```

Expected: both scripts print their success messages and exit `0`.

- [ ] **Step 2: Run all relevant manifest and portability checks**

Run:

```bash
python3 .claude/skills/skill-development/scripts/validate_skill.py skills/ludus-template-naming/SKILL.md
bash hooks/hooks-toolkit/scripts/validate-skill-frontmatter.sh skills/ludus-template-naming/SKILL.md
python3 .github/scripts/generate-marketplace.py --check
python3 .github/scripts/check-plugin-root-refs.py
python3 .github/scripts/check-host-compat.py
python3 hooks/steward/scripts/release-notes-audit.py --all
bash hooks/hooks-toolkit/scripts/validate-plugin-json.sh plugins/ludus-toolkit/.claude-plugin/plugin.json
```

Expected: every command exits `0`.

- [ ] **Step 3: Check symlinks and whitespace**

Run:

```bash
test -z "$(find plugins agents -xtype l -print)"
git diff --check
```

Expected: no broken symlinks and no whitespace errors.

- [ ] **Step 4: Review scope and generated changes**

Run:

```bash
git status --short
git diff --stat
git diff -- \
  skills/ludus-template-naming \
  skills/change-template-input-language/SKILL.md \
  skills/update-os-template/SKILL.md \
  plugins/ludus-toolkit \
  .github/scripts/test-ludus-template-naming.py \
  .github/scripts/test-ludus-opencode-install.py \
  .github/workflows/validate.yml \
  .claude-plugin/marketplace.json
```

Confirm that `plan.md` and external `awesome-ludus-sauce` content remain untouched, all canonical examples match the approved spec, `plugin.json` and release notes both say `0.4.0`, and marketplace changes are generator-produced only.

- [ ] **Step 5: Report results**

Report the canonical grammar delivered, validator and skill-test outcomes, bundle/OpenCode integration, marketplace entry, version bump, all verification commands and results, and any checks that could not run. Do not claim completion if any required command failed.
