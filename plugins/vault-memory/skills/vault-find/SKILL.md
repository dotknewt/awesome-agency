---
name: vault-find
description: Find what the project vault already knows about a topic and return a compact briefing (paths + one-line takeaways + gaps), not raw notes. Use before non-trivial work, when asked "what do we know / did we decide about X", or when a gotcha, convention or decision might already exist. Runs in the read-only vault-librarian subagent.
argument-hint: "<one-sentence task goal + 3-6 key terms (identifiers, file paths, error strings, domain nouns)> [--history] [--sources] [--budget N]"
context: fork
agent: vault-librarian
background: false
user-invocable: true
---
Retrieval request from the main conversation.

Topic / question: $ARGUMENTS

Instructions:
- You have no conversation history: everything you need is in the topic above and in the vault. Start with `read_note {path:"INDEX.md"}`.
- Follow your retrieval procedure exactly (frame → INDEX/MOC → 2–3 search variants per scope + frontmatter pass + Grep precision
  pass → triage with `get_frontmatter` → score → partial reads → one-hop expansion → verify evidence).
- Flags: `--history` = include `archive/` and superseded notes (temporal questions); `--sources` = also search `sources`;
  `--budget N` = max notes to read (default 8).
- Return ONLY the briefing in the standard format (≤40 lines, ≤1,500 tokens). No preamble, no raw note bodies.
- If the vault has nothing relevant, say so in one line and list the 2–3 closest notes with why they are not a match.
