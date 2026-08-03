---
name: extension-audit
description: This skill should be used when the user asks to "audit a plugin", "scan a Claude skill or agent", "check extension security", "verify extension integrity", "validate marketplace metadata", or "score extension quality". It performs a static, report-only audit of local plugin, skill, agent, instruction, command, and hook artifacts.
---

# Extension Audit

Run a deterministic, local audit of extension artifacts without importing, executing,
cloning, or fetching the target. Treat every result as a review lead rather than proof
of safety. Keep the default workflow report-only and preserve the target unchanged.

## Run the orchestrator

Use the bundled standard-library CLI:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/extension-audit/scripts/audit.py" scan PATH
python3 "${CLAUDE_PLUGIN_ROOT}/skills/extension-audit/scripts/audit.py" scan PATH --json
```

Run `scan` first for a one-shot report. It discovers common Claude/Copilot structures,
checks security heuristics, scores semantic quality, validates marketplace metadata, and
verifies `INTEGRITY.json` when one is present. Pass `--policy public-submission` when
reviewing a package intended for public marketplace submission. Use `--output report.json`
to save the rendered report.

## Run focused dimensions

Use the focused subcommands when a workflow needs a single artifact or a stable CI
stage:

```bash
python3 ".../audit.py" quality PATH --json
python3 ".../audit.py" marketplace PATH --policy public-submission
python3 ".../audit.py" integrity PATH
python3 ".../audit.py" verify PATH
```

`integrity` writes deterministic `INTEGRITY.json` (or the path supplied with
`--manifest`). It excludes itself, VCS metadata, dependency caches, and common build
directories. `verify` reports modified, missing, and untracked files. Both commands
also flag dependency declarations that are not pinned to exact versions or immutable
SHAs.

## Interpret the report

Review findings by severity:

- **Critical** — possible secret-bearing outbound behavior or dangerous hook command.
- **High** — prompt-injection language, sensitive path access, dangerous execution,
  broad hooks, invalid public metadata, or integrity mismatch.
- **Medium** — unpinned dependencies, auto-triggered hooks, missing metadata, or
  quality gaps.
- **Low** — organization and documentation improvements.

The inventory records artifact type, relative path, file permissions, frontmatter,
tool/trigger metadata, and hook events. Discovery includes `.claude-plugin/plugin.json`,
`.github/plugin/plugin.json`, `SKILL.md`, Claude agent files and `*.agent.md`,
`AGENTS.md`, `CLAUDE.md`, `*.instructions.md`, `hooks.json`, and command directories.

The security pass is static and intentionally conservative. It looks for instruction
override/concealment phrases, network and exfiltration patterns, environment/token and
credential paths, dangerous shell/code execution, broad permissions, and broad or
auto-triggered hooks. It does not understand runtime control flow, shell quoting,
obfuscation, or whether an example is inert. Never treat a clean scan as a security
guarantee.

The semantic-quality pass gives each skill, agent, instruction, and command a
deterministic 0–100 score. The explainable rubric covers description, structure,
trigger specificity, imperative/actionable guidance, progressive disclosure/file
references, output contract, safety boundaries, and cross-reference validity. Findings
include paths and line numbers where available. A low score is a reason to revise
documentation, not a security verdict.

## Agent handoff

For an autonomous read-only review, dispatch the bundled `extension-reviewer` agent.
It runs this CLI, preserves report-only behavior, and returns the structured report
with a concise risk summary. The standalone agent package includes a symlink to this
skill so `${CLAUDE_PLUGIN_ROOT}/skills/extension-audit/scripts/audit.py` resolves
after a micro-install.

## Additional resources

- **`scripts/audit.py`** — the complete static CLI and JSON report implementation.

