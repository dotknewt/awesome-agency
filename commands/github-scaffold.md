---
description: Scaffold GitHub repo metadata — pick what to create (issue template, CI workflow, …)
allowed-tools: Read, Bash, Glob, AskUserQuestion
---

Use `AskUserQuestion` to ask the user which GitHub scaffolding task to run, then dispatch to the right sub-command. Do not duplicate sub-command logic here.

## Step 1: Ask

Single-question `AskUserQuestion` with one option per catalogue row plus Cancel:

| Option label | Description |
|---|---|
| Create issue template | Scaffold a YAML issue form in `.github/ISSUE_TEMPLATE/` |
| Scaffold CI workflow | Create a `.github/workflows/*.yml` with canonical CI defaults (push-to-main, concurrency, path filters) |
| Cancel | Stop without doing anything |

## Step 2: Dispatch

- **Create issue template** → follow the workflow in `plugins/github-toolkit/commands/create-issue-template.md`.
- **Scaffold CI workflow** → follow the workflow in `plugins/github-toolkit/commands/scaffold-ci-workflow.md`.
- **Cancel** → acknowledge and stop.

_(Add a row to the table and a dispatch line here each time a new scaffolding command is added to this plugin.)_
