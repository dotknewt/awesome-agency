# Work Objects Toolkit Release Notes

## v0.1.0 (2026-08-06)

Initial release notes, reconstructed from git history. Earlier versions shipped
without notes.

### Hooks

- **Status transitions are gated by a script, not by convention.** A work object
  claiming `in-review` or `approved` without the evidence to back it is worse than
  no work object at all, and asking a model to self-certify does not hold under
  pressure. A `PreToolUse` hook runs `check_preconditions.py` and blocks the
  transition when the captured diff, test output, run manifest, or review is
  missing.
- **The gate no-ops when `${CLAUDE_PLUGIN_ROOT}` is unset** rather than failing
  closed, so the hook cannot wedge a session where the plugin is only partly
  installed.

### Skills

- **`work-object-guard` is bundle-bound and gets no standalone entry.** The skill
  documents transitions that only the bundled hook can enforce; installing it alone
  would describe a gate that is not there.
