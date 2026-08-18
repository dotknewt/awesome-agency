# project-workflow Release Notes

## v0.1.2 (2026-08-18)

Review pass over v0.1.1's attribution change. Two of these are the attribution
feature failing to actually work; the rest are seams the review found around it.

### Fixed

- **The critic pass could not check attribution, which was the whole point of
  asking it to.** The protocol told the critic to hunt claims presented as the
  human's that trace back to agent-written option labels, while the sanctioned
  fallback is a fresh agent with no memory of the conversation — it cannot see
  a difference that exists only in the source tags, not in the prose. The
  critic step now requires handing over the tagged claim list and the relevant
  log entries, and says that when those can't be supplied, the critic's remit
  is measurability only and must be reported as such rather than as an
  attribution review that never happened. `critic.inputs` records what it
  actually received.
- **The canonical hook example was inert and would have been copied.**
  project-environment drafts hooks for users to apply, so a broken example is
  worse than none. It used `$TOOL_INPUT` (which exists only in `type: prompt`
  hooks, not `type: command`), echoed to stdout, and exited 1 — a non-blocking
  error that lets the tool call through. Replaced with a working
  entry-plus-script pair using the real mechanics (JSON on stdin via `jq`,
  `ask` via `hookSpecificOutput` on stdout with exit 0, deny via stderr plus
  exit 2), a `$CLAUDE_PROJECT_DIR` path since drafted hooks land in the user's
  project rather than a plugin, and an explicit note that a pattern list is a
  speed bump rather than a control.

### Changed

- **Frontmatter no longer asserts dependencies that weren't satisfied.**
  verify and environment explicitly permit proceeding without a completed
  upstream layer, but their templates hardcoded `depends_on`/`layers_complete`
  as if it had been — an unbacked claim in YAML, which is exactly what this
  bundle exists to prevent. Replaced with `grounded_in`, which records the
  state actually observed per dependency (`complete | incomplete | missing`).
- **Dropped `layers_complete`.** Three files each carried a roll-up of what
  the other files' `status` fields already said, with nothing reconciling
  drift. Each file's own `status` is now the single source of truth.
- **Source tags now appear in the spec files, not only the decisions log.**
  v0.1.1 kept provenance in the log and mandated flat prose in the files —
  but the file is what people read, and recovering "was this criterion the
  user's requirement or my guess?" by diffing against a log is not something
  anyone does. Claims now carry their tag inline; the ban on narrated
  attribution ("the user reports…") stands.
- **The critic threshold was firing at nearly every checkpoint.** "3+ sections
  OR 300+ words" is crossed mid-interview by a spec targeted at 200-500 words
  across four mandatory sections, so an adversarial pass meant to be selective
  ran constantly — which trains everyone to skim it. Now it runs on
  `⚠ load-bearing` checkpoints and each layer's final checkpoint.
- **The codex-plugin-cc fallback choice is made once per slug**, recorded as
  `critic.fallback_choice`, instead of re-interrogating a user who doesn't have
  it installed at every critic-triggering checkpoint.
- **Re-presenting an approved section now collapses unchanged claims** to a
  count plus their checkpoint id. Showing the full list is the trust mechanism
  for claims under review; replaying approved ones verbatim is noise, and
  noise is how a real gap gets skimmed past.
- **Attribution edge cases closed.** A fact confirmed by agreeing to the
  agent's paraphrase is `@approved`, not `@user` (the wording, and anything
  added while paraphrasing, is still the agent's); a confirmed `@inferred`
  claim becomes `@approved`, never `@user`, since confirmation doesn't change
  who authored it; `options_authored_by` is logged only for `chose-option`
  answers, instead of forcing an invented value onto every free-text entry.
- **The critic was still being handed the classification it was supposed to
  audit.** Passing it the tagged list alone lets it do nothing but agree: the
  tag is the claim under review, and a claim first raised at the current
  checkpoint has no earlier log entry to check it against. The critic now
  receives `source_detail` for every current claim — exact wording, exact
  option label, what an inference came from, or the path read — as a pending
  log block written before the human responds.
- **Two log-schema placeholders that would have produced false entries.**
  `source_detail` offered no form for an `@inferred` claim, so the one source
  type whose evidence exists only in the agent's head had nowhere to record it;
  and `critic.inputs` was written as a fixed non-empty list, which would have
  logged inputs to a critic that never ran. `[]` when `invoked: false` is now
  explicit — an audit field that lies by default is worse than no field.
- **project-manager stopped pointing at a file it doesn't ship** (its dir has
  no `references/`, so a solo install dangled) and dropped an
  accepted-with-risk carve-out for a layer transition that doesn't exist —
  environment is the last layer, and accepted risks still reach `complete`.

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
