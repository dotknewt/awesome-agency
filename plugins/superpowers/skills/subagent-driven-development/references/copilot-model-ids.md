# Copilot CLI model ids

Maintained snapshot of GitHub Copilot CLI's `--model` short-id catalog, dated
2026-08-13. This is a hand-maintained list, not a live query — verify with
`copilot help` before trusting it for a real dispatch, since model catalogs change and
a stale id fails exactly like a guessed one.

```
anthropic: claude-sonnet-5, claude-opus-5, claude-opus-4.8, claude-opus-4.7,
           claude-sonnet-4.6, claude-opus-4.6, claude-sonnet-4.5,
           claude-opus-4.5, claude-haiku-4.5
openai:    gpt-5.6-sol, gpt-5.6-terra, gpt-5.6-luna, gpt-5.5, gpt-5.4,
           gpt-5.4-mini, gpt-5.3-codex, gpt-5-mini
```

This list is for Copilot CLI's `--model`/dispatch short-id format only. It does not
apply to Copilot Chat in VS Code's `runSubagent`, which needs a separate
`"Model Name (Vendor)"` display string (e.g. `Claude Sonnet 5 (copilot)`) that this
list does not provide.
