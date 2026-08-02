---
name: github-scaffold
description: >
  Use when the user asks to scaffold GitHub repo metadata under `.github/` —
  issue templates, issue forms (YAML), PR templates, CODEOWNERS, or workflows.
  Triggers on phrases like "add an issue template", "set up issue forms",
  "scaffold .github", "create a PR template", "add a bug report template",
  "set up GitHub templates". Routes to the `/github-scaffold` command, which
  lists available subtasks and dispatches to the right one.
---

Run `/github-scaffold` to pick a subtask. The umbrella command lists what is currently available; today that is `/create-issue-template` (supports creating multiple templates in one run).
