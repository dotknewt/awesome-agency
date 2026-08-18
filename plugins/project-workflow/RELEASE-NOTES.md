# project-workflow Release Notes

## v0.1.1 (2026-08-18)

### Fixed

- **Every claim in the interview now carries a source tag, because the agent was
  laundering its own words into the user's mouth.** The observed failure: the
  agent wrote an option label asserting a fact, the user picked that option, and
  the agent then cited the fact back as something the user had reported — so a
  guess acquired a human's name on it and never got checked. A new attribution
  section in the shared `checkpoint-protocol.md` tags each line item `@user`,
  `@approved`, `@inferred`, or `@observed`, forbids "you said"-style attribution
  for anything but `@user`, bars unconfirmed facts from riding inside option
  labels, and blocks an unconfirmed inference from grounding a downstream claim.
  The self-check and critic pass now look for misattribution explicitly, and the
  `.decisions.log` records `source`/`source_detail` per claim plus whether the
  human's answer was free text or a click on a menu the agent authored — without
  that field, a later reader cannot tell the two apart, which is what made the
  failure invisible in the first place.
- **Each layer applies the rule where it is most likely to slip.** project-spec
  flags that an early Goal draft is mostly the agent's wording; project-verify
  calls out proposed thresholds landing in `verify.md` as "the number the user
  gave"; project-environment sources every gap to what was actually read and
  notes that accepting a risk is not reporting a problem; project-manager's
  wrap-up summarizes what the files say rather than who said it.

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
