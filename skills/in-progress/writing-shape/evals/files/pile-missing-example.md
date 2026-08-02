# notes - one-paragraph PR descriptions

core claim: if you can't describe what a PR does in one paragraph, the PR
is doing too many things. this isn't a writing-quality complaint, it's a
scope complaint wearing a writing-quality costume.

- reviewers skim. a five-paragraph PR description gets skimmed, which
  means the reviewer approves based on the diff alone, which defeats the
  point of having a description
- when I catch myself writing paragraph two, that's the signal to split
  the PR, not to write a better paragraph two

pushback I get: "but this PR genuinely touches five files for one
reason, it needs the context." response: the context can live in a
linked doc or the commit body — the PR description is a pointer, not
a container.

things to check before publishing this:
- need a real before/after: an actual bloated PR description next to
  the one-paragraph version of the same change, so the reader can see
  the difference instead of just being told it exists
- I don't have one saved anywhere, would have to go dig one up or make
  one up (don't want to make one up, wouldn't be honest)

- worth mentioning: this is a norm, not a linter rule. we don't block
  merges on paragraph count, tech leads just push back in review
