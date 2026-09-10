# Ludus Template Naming Standard - Design

**Date:** 2026-09-10
**Status:** Approved
**Scope:** `ludus-toolkit` naming guidance and validation

## Problem

The Ludus template-maintenance skills currently preserve each source template's
basename order. That permits semantically equivalent templates to use different
orders and separators. It also makes short tokens ambiguous. For example, `no`
in `win2019-server-x64-no-security-updates` means "no security updates," while
the same token elsewhere identifies a Norwegian keyboard layout.

The current `awesome-ludus-sauce/templates/` corpus demonstrates the drift:

- `ubuntu-24.04.2-x64-no-desktop` puts locale before role.
- `debian-13-2-x64-no-server` uses hyphens both between fields and inside the
  release.
- `win11-22h2-x64-no-enterprise` combines the Windows product and release in a
  family-specific form.
- `win2019-server-x64-no-security-updates` cannot be parsed reliably without
  knowing that `no-security-updates` is one qualifier.

Directory names become user-facing built template names through `vm_name`, and
range configurations refer to those built names exactly. The toolkit therefore
needs one documented grammar and a deterministic validator before a separate
repository attempts a bulk migration.

## Decision

Add a dedicated, independently installable `ludus-template-naming` skill to the
`ludus-toolkit` bundle. The skill owns the canonical grammar, the procedure for
deriving semantic fields from legacy templates, and a dependency-free Python
validator. Existing locale-change and OS-update skills will adopt the canonical
order rather than preserving legacy token positions.

The validator checks names but never rewrites them. Legacy names can be
semantically ambiguous, so automatic canonicalization could silently turn a
feature qualifier into a locale or infer the wrong keyboard layout.

### Alternatives considered

- **Share naming assets between the two existing maintenance skills.** This
  avoids a new skill but adds symlink and packaging coupling, and users cannot
  discover naming as an independent operation. Rejected.
- **Put the validator only at the bundle root and duplicate prose.** This uses
  fewer files, but standalone micro-installs lose executable validation and the
  duplicated standard can drift. Rejected.

## Canonical Grammar

Hyphens separate semantic fields. Underscores join multiple words or semantic
parts inside one field. All characters are lowercase ASCII.

The supported family shapes are:

```text
Linux:
  <os>-<release>-<arch>-<role>[-<qualifier>...]-<locale>

Windows client:
  windows-<release>-<arch>[-<qualifier>...]-<locale>

Windows Server:
  windows-server-<release>-<arch>[-<qualifier>...]-<locale>
```

The first validator version supports the current corpus families `ubuntu`,
`debian`, `kali`, `windows`, and `windows-server`. Adding a new OS family
requires an explicit schema update rather than silently accepting an unknown
shape.

### Field rules

- `os`: a known lowercase family identifier. `windows-server` is an intentional
  compound family prefix.
- `release`: starts with a digit. Purely numeric components use dots, such as
  `24.04.2`, `13.2`, and `2024.4`. An underscore joins a semantic release part
  that contains letters, such as `11_22h2`. Hyphens never occur inside the
  release field.
- `arch`: a supported lowercase architecture token, initially `x64` or `arm64`.
- `role`: required for the supported Linux families and initially limited to
  `desktop` or `server`. Windows uses family-specific shapes: Windows client
  omits a role, while Windows Server encodes `server` in its family prefix.
- `qualifier`: optional and placed after role, or after architecture when the
  family shape has no role. A multiword qualifier uses underscores, for example
  `no_security_updates`. Multiple distinct qualifiers may remain separate
  hyphen-delimited fields.
- `locale`: required as the final field for every template, including the
  default locale. It is a lowercase two-letter country-style naming token such
  as `us` or `no`. The skill must validate the token against the requested
  keyboard layout separately; filename tokens, XKB identifiers, and Windows
  input locales are not interchangeable identifier systems.

The template directory basename and top-level `.pkr.hcl` basename must be
identical. The built template name is exactly the canonical basename followed
by `-template`.

### Examples

```text
ubuntu-24.04.2-x64-desktop-no
ubuntu-24.04.2-x64-desktop-no-template
debian-13.2-x64-server-no
kali-2024.4-x64-desktop-no
windows-11_22h2-x64-enterprise-no
windows-server-2019-x64-no_security_updates-us
windows-server-2019-x64-no_security_updates-no
```

The required Ubuntu conversion is:

```text
Directory and Packer basename:
  ubuntu-24.04.2-x64-no-desktop
  -> ubuntu-24.04.2-x64-desktop-no

Built template name:
  ubuntu-24.04.2-x64-desktop-no-template
```

## Naming Workflow

The naming skill will instruct an agent to perform these steps:

1. Inspect the complete template directory, `.pkr.hcl`, installer answer files,
   and consuming references before interpreting the legacy basename.
2. Classify each semantic field. Do not infer locale from token position; use
   installer keyboard settings and other template content as evidence.
3. Ask one short question when a token remains ambiguous. In particular, do not
   treat `no` as Norwegian when it belongs to `no_security_updates`.
4. Construct the canonical basename with family-specific field order and the
   approved separator rules.
5. Stop if the target directory or target `.pkr.hcl` already exists.
6. Rename the directory and top-level `.pkr.hcl`, set `vm_name` to the canonical
   basename plus `-template`, and update exact old-name references.
7. Run the validator on both the basename and built template name.
8. Search for the old full basename and inspect every remaining match before
   reporting completion.

The workflow changes no locale, role, edition, feature, release, or architecture
merely to satisfy naming. It normalizes representation of the template's
existing semantics.

## Validator Contract

Add `skills/ludus-template-naming/scripts/validate_template_name.py`. It uses
only the Python standard library and accepts one or more positional names:

```text
python3 validate_template_name.py NAME [NAME ...]
```

Each argument may be either a canonical basename or a built template name. A
built name must contain exactly one terminal `-template` suffix; validation
then applies to the remaining basename.

For each valid argument, the command prints a concise success line to standard
output. For each invalid argument, it prints the rejected name and an
actionable reason to standard error. It exits zero only when every argument is
valid; otherwise it exits nonzero after reporting all supplied names.

Validation covers:

- recognized family shape;
- required and ordered fields;
- lowercase ASCII and permitted separators;
- release separator rules;
- supported architecture and Linux role tokens;
- qualifier syntax;
- required two-letter final locale;
- exact built-template suffix behavior.

The validator does not inspect HCL, infer semantics, rename files, or guarantee
that a syntactically valid locale is correct for the installer. Those checks
remain part of the skill workflow.

## Existing Skill Integration

`change-template-input-language` will no longer derive a target by replacing a
locale token in place. It will preserve semantic values but reconstruct the
entire canonical basename, placing role before qualifiers and locale last. Its
Ubuntu example becomes `ubuntu-24.04.2-x64-desktop-no`.

`update-os-template` will no longer preserve a source's naming style and suffix
order. It will normalize the copied template's semantic fields while replacing
the release. It will keep numeric release punctuation canonical and use
underscores only for semantic release combinations or multiword fields.

Both skills remain useful when installed alone: each includes a concise summary
of the grammar and manual verification requirements. The dedicated naming skill
provides the full rationale and executable validator when installed directly or
as part of `ludus-toolkit`; neither existing micro-entry will assume access to a
sibling plugin root.

## Packaging And Release

Implementation changes include:

1. `skills/ludus-template-naming/SKILL.md` - new naming workflow and grammar.
2. `skills/ludus-template-naming/scripts/validate_template_name.py` - new
   dependency-free validator.
3. `skills/change-template-input-language/SKILL.md` - canonical reconstruction
   and updated examples/checks.
4. `skills/update-os-template/SKILL.md` - canonical reconstruction and updated
   source-selection/check rules.
5. `plugins/ludus-toolkit/skills/ludus-template-naming` - bundle symlink to the
   pooled skill.
6. `plugins/ludus-toolkit/opencode/install.py` - add the seventh skill.
7. `.github/scripts/test-ludus-opencode-install.py` - expect and verify seven
   installed skills.
8. `.github/scripts/test-ludus-template-naming.py` - validator behavior tests.
9. `.github/workflows/validate.yml` - run the validator tests in CI.
10. `plugins/ludus-toolkit/README.md` - list the naming skill.
11. `plugins/ludus-toolkit/.claude-plugin/plugin.json` - bump `0.3.0` to
    `0.4.0` because this adds a user-facing toolkit capability.
12. `plugins/ludus-toolkit/RELEASE-NOTES.md` - add a `v0.4.0 (2026-09-10)` entry
    explaining that ambiguous legacy ordering required a canonical grammar and
    deterministic validation.
13. `.claude-plugin/marketplace.json` - regenerate so the new skill receives a
    standalone micro-entry and bundle metadata remains current.

The OpenCode installer copies skill trees with symlinks dereferenced, so the
new validator script must be present and byte-identical in the installed skill.
The existing installer test's manifest comparison verifies this behavior.

## Error Handling

- Reject unknown OS families instead of guessing their field layout.
- Reject locale-before-role legacy names and explain the expected family shape.
- Reject missing locales, including templates that previously relied on a
  default-US convention.
- Reject multiword qualifiers written with hyphens when they make field meaning
  ambiguous; direct the user to underscore form such as `no_security_updates`.
- Reject numeric release components joined with underscores and direct the user
  to dots. Permit an underscore when it separates a semantic alphanumeric part,
  as in `11_22h2`.
- Stop the editing workflow on target-path collisions or unresolved semantic
  ambiguity. Validation failure must not trigger an automatic rename.

## Testing

The validator test will exercise the command as a subprocess and assert output
and exit status. Valid cases cover every canonical example in this design, both
basename and `-template` forms, optional qualifiers, and multiple-name input.

Invalid cases cover:

- `ubuntu-24.04.2-x64-no-desktop` (locale before role);
- `debian-13-2-x64-server-no` (hyphens inside release);
- `windows-server-2019-x64-no-security-updates` (ambiguous qualifier and missing
  explicit locale);
- `windows-server-2019-x64-no_security_updates` (missing locale);
- uppercase characters;
- unknown family, architecture, or Linux role;
- malformed or repeated separators;
- missing, misplaced, or repeated `template` suffixes;
- mixed batches in which one invalid name makes the command fail after all
  inputs are reported.

Repository verification will run:

```text
python3 .github/scripts/test-ludus-template-naming.py
python3 .github/scripts/test-ludus-opencode-install.py <opencode-schema.json>
bash hooks/hooks-toolkit/scripts/validate-skill-frontmatter.sh skills/ludus-template-naming/SKILL.md
python3 .github/scripts/generate-marketplace.py --check
python3 .github/scripts/check-plugin-root-refs.py
python3 .github/scripts/check-host-compat.py
python3 hooks/steward/scripts/release-notes-audit.py --all
git diff --check
```

## Out Of Scope

- Renaming directories, Packer files, `vm_name` values, archives, or range
  references in `dotknewt/awesome-ludus-sauce`.
- Backward-compatible aliases for legacy built template names.
- Automatic inference or rewriting of ambiguous legacy names.
- Changes to the Ludus MCP server or OpenAPI schema; those surfaces pass
  template names through as opaque strings.
- A universal grammar for future OS families not represented in the current
  template corpus. New family shapes must be added deliberately.
