---
name: writing-fragments
description: Use when the user wants to freewrite, brainstorm, or capture raw notes and half-formed ideas for a piece of writing before any outline or structure exists — interviews them and appends fragments (sentences, vignettes, quotes, leading words) to a markdown file. Trigger even when they don't say "brainstorm" or "fragments" explicitly, e.g. "I have a vague idea for an essay about X", "let's talk through what I want to say about Y", "help me think out loud about Z", or "I keep noticing this pattern and want to write about it". Do NOT trigger once the user is ready to outline, sequence, or structure the piece into beats, paragraphs, or sections — that's a separate, later-stage skill (writing-beats, writing-shape).
disable-model-invocation: true
# `disable-model-invocation` stays top-level rather than moving under `metadata:`
# (the skill-spec's documented extension point for undocumented keys): Claude Code
# reads this key at the top level to gate auto-invocation of the skill, and treats
# `metadata` as inert key-value storage per spec, not consulted for behavior.
# Moving it would silently re-enable auto-triggering. Same convention followed by
# every other SKILL.md in this repo (writing-beats, writing-shape, edit-article,
# wizard, loop-me, claude-handoff) and documented explicitly in the agency repo at
# .claude/skills/manifest-lint/SKILL.md and
# .claude/skills/command-development/references/frontmatter-reference.md.
---

<what-to-do>

This is pure **explore**: widen the space of what could be written without committing to structure — committing is _exploit_, a separate skill's job. Run a grilling session that produces fragments, interviewing the user relentlessly about whatever they want to write about. Imposing phases, outlines, or article structure is out of scope here.

As fragments emerge from either side of the conversation, append them to a single markdown file.

If the user did not pass a path, ask once where to save the document, then remember it for the rest of the session.

Capture fragments from the very first thing the user says, including the initial prompt.

On first write, put a single H1 at the top with a working title (it can change later) and nothing else — no metadata, no TOC, no date.

</what-to-do>

<supporting-info>

## What is a fragment

A fragment is any piece of text that might survive into the final article. It must be _readable by the author_ — the author can tell what it means — but it does not need to define its terms or be comprehensible to a cold reader. The bar is "is this a piece of good writing?", not "is this a self-contained argument?"

Fragments are deliberately heterogeneous. Examples of what could be a fragment:

- A sharp sentence you'd want to deploy somewhere but don't yet know where.
- A claim with a one-line justification.
- A vignette: a thing that happened, a code snippet, a scenario, an analogy.
- A half-thought: "something about how X feels like Y, work this out later."
- A quote, a piece of dialogue, an overheard line.
- A list of related observations that hang together by feel.
- A complaint, a confession, a punchline.
- A **leading word** — a compact metaphor or coinage the whole piece can hang on (one term that names the idea, the way _tracer bullets_ or _fog of war_ names a whole pattern).

Of these, the leading word is the most valuable fragment to land. It is load-bearing: name the right one in explore and it shapes the structure, the transitions, and the title later — paying dividends through the entire exploit phase. When the conversation circles a recurring idea, push to coin a word for it.

The novelist's diary is the model: years of unstructured noticings that later get mined for raw material. Fragments are noticings.

## File format

```markdown
# Working title

A first fragment lives here.

It can be multiple paragraphs. It can include lists, code, quotes — whatever
shape the fragment naturally takes.

---

A second fragment.

---

> A quoted line that the user wants to keep around.

A reaction to it.

---

- A cluster of related observations
- That hang together by feel
- And want to be near each other
```

Fragments are separated by a horizontal rule (`\n---\n`). No headings inside the body. No tags. No order beyond the order they were added.

## Writing rhythm

Append silently. Don't ask permission for each fragment. Mention what you added in passing ("adding that"), but don't interrupt the conversation with save dialogs.

Before every write: re-read the file from disk. The user may have edited, reordered, or deleted fragments between turns — preserve their changes. Never overwrite the file; only append (or, if the user asks, edit a specific fragment in place).

The user can say "cut the last one", "rewrite that one sharper", "merge those two" at any time. Treat those as first-class instructions.

</supporting-info>
