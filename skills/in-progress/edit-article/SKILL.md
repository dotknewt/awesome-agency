---
name: edit-article
description: Edit an article draft by first proposing a section plan (respecting which ideas depend on which) and confirming it with the user, then rewriting section by section with a 240-character-per-paragraph cap for scannability. Use whenever someone wants an article, blog post, or draft restructured, tightened, or made to read better — including indirect requests like "make this flow better", "this reads clunky", "tighten this up", "smooth this out", or "this needs a pass" before it ships — not only literal asks to edit, revise, or improve.
# disable-model-invocation is intentional while this skill is still maturing in
# skills/in-progress/: the workflow hasn't been validated for reliable auto-triggering yet
# (see evals/eval_queries.json). Revisit removing this once trigger rates look good and the
# skill graduates out of in-progress/.
disable-model-invocation: true
---

# Edit Article

Revise an article draft section by section, confirming the plan with the user up front and checking back in after each rewrite, so the final piece is never a surprise.

1. First, divide the article into sections based on its headings. Think about the main points you want to make during those sections.

   Order sections so dependent ideas come after the ideas they depend on — don't lean on a term or example before it's been introduced.

   Confirm the sections with the user before rewriting anything.

2. For each confirmed section, in order:

   2a. Rewrite the section to improve clarity, coherence, and flow. Use a maximum of 240 characters per paragraph (see Gotchas below for content that can't be shortened).

   2b. Present the rewritten section to the user and incorporate their feedback before moving on. Resolve any open feedback on the current section before starting the next one — don't let it carry forward unaddressed.

3. Once every section is rewritten and approved, assemble the full article and deliver it:

   - **Default:** if the article came from a file, edit that file in place with the final assembled text.
   - **No source file (e.g. pasted inline):** ask the user whether they want a new file or the full text returned directly in the conversation; for long pieces, offer an Artifact.
   - Either way, summarize what changed structurally (reordered or merged sections, sections split apart) so the user can review the shape of the edit without having to diff every line of prose.

## Gotchas

- **Why 240 characters per paragraph?** It's a scannability target, not a technical constraint: short paragraphs force one idea per paragraph, which keeps the dependency ordering from step 1 legible to a reader moving quickly. Apply it to prose you're actively rewriting, not as a rule to enforce everywhere.
- **Code blocks, quotes, and other content you can't shorten.** The cap applies to your own rewritten prose paragraphs — leave fenced code blocks, block quotes, and verbatim quoted material alone even when they run long. `scripts/validate_paragraphs.py` skips these by default.
- **Circular section dependencies.** If section A needs a term defined in B, and B needs an example from A, break the cycle instead of guessing: add a short forward reference ("more on this in the next section") or pull the shared concept into its own earlier section. Raise the tradeoff with the user during the confirm-sections step in 1, before you've rewritten anything.

### Example

Before (one 367-character paragraph):

> Our new caching layer, which we rolled out last quarter after the incident where the database fell over under load during the product launch, uses a write-through strategy so that reads are always consistent, and it's backed by Redis with a fallback to the origin database if a key is missing, which took a while to get right because of some edge cases around expiry.

After (three paragraphs, each under 240 characters):

> We rolled out a new caching layer last quarter, after the database fell over under load during a product launch.
>
> It uses a write-through strategy, so reads are always consistent. Redis backs the cache, with a fallback to the origin database if a key is missing.
>
> Getting the expiry edge cases right took the longest.

## Available scripts

- **`scripts/validate_paragraphs.py`** — Checks a markdown file's paragraphs against the 240-character limit and reports any that are too long, with their location. Run it after rewriting a section (step 2a) to confirm the limit is respected:

  ```bash
  python3 scripts/validate_paragraphs.py path/to/article.md
  ```

  Run `python3 scripts/validate_paragraphs.py --help` for all options.
