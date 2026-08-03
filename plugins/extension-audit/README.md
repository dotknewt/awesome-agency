# extension-audit

`extension-audit` is a focused, local-only bundle for reviewing Claude Code and
Copilot extension artifacts before installation or publication. It is report-only:
the bundled Python CLI never executes target code, hooks, commands, or network
requests.

## Included

| Component | Purpose |
|---|---|
| `extension-audit` skill | One-shot and focused static audits with JSON or human output. |
| `extension-reviewer` agent | Read-only structured review that invokes the skill CLI. |

## Usage

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/extension-audit/scripts/audit.py" scan ./my-extension
python3 "${CLAUDE_PLUGIN_ROOT}/skills/extension-audit/scripts/audit.py" scan ./my-extension --json --output report.json
python3 "${CLAUDE_PLUGIN_ROOT}/skills/extension-audit/scripts/audit.py" quality ./my-extension
python3 "${CLAUDE_PLUGIN_ROOT}/skills/extension-audit/scripts/audit.py" marketplace ./my-extension --policy public-submission
python3 "${CLAUDE_PLUGIN_ROOT}/skills/extension-audit/scripts/audit.py" integrity ./my-extension
python3 "${CLAUDE_PLUGIN_ROOT}/skills/extension-audit/scripts/audit.py" verify ./my-extension
```

`scan` inventories plugin/skill/agent/instruction/command/hook capabilities, checks
heuristic security risks, scores semantic quality, validates metadata, and verifies an
existing `INTEGRITY.json`. `integrity` creates a deterministic SHA-256 manifest;
`verify` reports modified, missing, and untracked files. High/critical findings return
nonzero status for CI use.

## Mapping to external building blocks

1. **Cisco skill-scanner** — static prompt-injection, exfiltration, credential/path,
   dangerous-code, permission, and hook-scope heuristics.
2. **nestedcat / Forged-Cortex plugin audits** — capability inventory, hook metadata,
   risk categorization, and structured findings.
3. **awesome-copilot agent-supply-chain** — deterministic SHA-256 manifests, verify
   mode, and unpinned dependency warnings.
4. **Tessl-like semantic evaluation** — deterministic, explainable local rubric for
   descriptions, structure, triggers, actionability, progressive disclosure, output
   contracts, safety boundaries, and cross-references.
5. **awesome-copilot external-plugin-validation** — marketplace metadata, HTTPS,
   safe source paths, semver, duplicate names, and public-submission policy checks.

## Limitations

Pattern matching can miss obfuscated or runtime-only behavior and can flag benign
examples. A clean result is not proof of safety or provenance. Integrity verifies local
bytes against a local manifest; it does not authenticate the manifest or remote source.
Semantic scores are a deterministic documentation rubric, not an LLM judgment. Review
all high-risk findings and source provenance manually before installation.
