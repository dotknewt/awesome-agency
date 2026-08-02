# Docs Layout Convention

## `docs/TODO.md` — backlog

Backlog notes, grouped by topic heading, bullet list per topic:

```markdown
# some-topic
- idea or task worth keeping
- another one

# another-topic
- ...
```

## `docs/STATE.md` — session bookmarks

Session bookmarks (What / How / WIP / ToDo / Completed / Decisions).
The schema is owned by the `state-keeper` agent — do not duplicate it
here. Create and maintain the file by invoking `state-keeper` with
path `docs/STATE.md`.

## `docs/user/*.md` — user-facing docs

User-facing docs: install, usage, tutorials, FAQ. Open-ended file set —
the convention establishes the location, not a fixed list of filenames.

Distinguish from:

- `docs/specs/` — architecture and contributor docs (owned by
  `docs-spec-maintainer`).
- Root `README.md` — short overview plus a pointer into `docs/user/`.
