# Extension Audit Release Notes

## v0.2.0 (2026-08-06)

- **`extension-reviewer` now pins `model: opus` instead of inheriting the caller's
  model.** Inheriting meant the depth of a security and supply-chain audit depended on
  whatever tier the user happened to be running — so the same untrusted plugin could
  be cleared by a Haiku session and flagged by an Opus one, with nothing in the report
  indicating which had happened. An adversarial reviewer is exactly the agent that
  must not inherit: it exists to catch subtle risks that weaker reasoning misses, and
  running it on a cheap model reproduces the blind spot it was built to cover. Opus
  rather than Fable deliberately — Fable's classifier silently routes
  security-adjacent prompts to an older Opus, so it would cost twice as much for less
  capability, with no signal that the downgrade occurred.

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
