---
description: Scaffold a GitHub Actions CI workflow file with canonical defaults (push-to-main, concurrency, path filters, workflow_dispatch).
allowed-tools: Read, Write, Bash, AskUserQuestion
---

Walk the user through creating a `.github/workflows/<name>.yml` file that follows the CI defaults in `plugins/github-toolkit/skills/github-workflow/SKILL.md`.

## Step 1: Gather inputs

Use `AskUserQuestion` to ask two things in a single call:

- **Workflow name**: What should the workflow be called? (e.g. `ci`, `test`, `deploy`, `lint`). This becomes the filename and the `name:` field.
- **Path scope**: Should the workflow skip docs-only changes?
  - Yes — add `paths-ignore` for `**.md`, `instructions/**`, `docs/**`, `.gitignore`, `LICENSE`
  - No — run on every push/PR regardless of file type
  - Custom — let me specify paths

If Custom, ask a follow-up: `paths:` (include list) or `paths-ignore:` (exclude list)? And what paths?

## Step 2: Preview the file

Show the user the full YAML that will be written before writing it. Derive it from the template at `plugins/github-toolkit/skills/github-workflow/references/ci-defaults.yml` with their inputs substituted:
- `name:` → their workflow name (title-cased, e.g. "ci" → "CI")
- Job id → `<workflow-name>` with hyphens
- Path filter block → per their choice (include, ignore, or omit)

If scope was Custom, substitute their path list.

## Step 3: Confirm and write

Ask: "Write this to `.github/workflows/<name>.yml`?" (Yes / Edit first / Cancel).

- **Yes** → ensure `.github/workflows/` exists (`Bash: mkdir -p .github/workflows`), then write the file.
- **Edit first** → show the YAML in an editable prompt context, let the user paste a corrected version, then write it.
- **Cancel** → stop.

## Step 4: Confirm

Print the relative path of the file written and remind the user to:
1. Replace the `# ... your steps here` placeholder with actual job steps.
2. Update `permissions:` if the job needs more than `contents: read`.
