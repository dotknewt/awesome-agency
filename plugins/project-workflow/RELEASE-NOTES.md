# project-workflow Release Notes

## v0.1.0 (2026-08-18)

Initial release.

### Skills

- **`project-manager`, `project-spec`, `project-verify`, and
  `project-environment` ship as one bundle.** The three layers are sequential —
  verify's criteria are only meaningful against a signed-off goal, and
  environment's gap scan is scoped by both — so installing the orchestrator
  without the layers it dispatches to leaves it unable to do its job. Bundling
  them makes the whole chain a single install; each skill also stays available
  as a standalone micro-entry for anyone who wants just one layer.
- **The checkpoint protocol is duplicated into each layer's `references/`
  rather than shared.** Each layer must work when installed alone, so
  `checkpoint-protocol.md` (itemized claim test, load-bearing test, checkpoint
  timing, critic mechanism, logging format) is carried by every skill that
  reads it instead of living in one place the others would have to reach into.
