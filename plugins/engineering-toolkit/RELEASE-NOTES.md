# Engineering Toolkit Release Notes

## v0.1.0 (2026-08-06)

Initial release notes, reconstructed from git history. Earlier versions shipped
without notes.

### Skills

- **Idea-to-ship flow assembled as one bundle.** The constituent skills — grilling,
  PRD and issue breakdown, TDD implementation, code review — were installable
  individually, which left users to discover the ordering themselves. `ask-matt`
  routes between them so the bundle carries the workflow, not just the parts.
- **Matt Pocock's skills vendored rather than fetched.** `grill-with-docs`,
  `improve-codebase-architecture`, and their siblings are cloned from
  `mattpocock/skills` so the bundle installs without a network dependency on a
  third-party repo that can move or disappear.
