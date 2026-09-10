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
