# Extension Audit Release Notes

## v0.1.0 (2026-08-06)

Initial release. Notes reconstructed from git history.

### Agents

- **`extension-reviewer` audits extension artifacts before you install them.**
  Marketplace plugins, skills, and agents execute with your tools and credentials,
  but nothing in the install path inspects what they actually do. The agent runs a
  static, report-only pass over security, capability, integrity, marketplace
  metadata, and semantic quality — it never modifies the artifact under review.

### Skills

- **`extension-audit` ships the scanner the agent drives.** The scan logic lives in
  `scripts/audit.py` rather than in prose so its findings are reproducible and can
  be re-run outside an agent session.
