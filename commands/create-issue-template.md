---
description: Scaffold one or more GitHub issue forms (YAML schema) in .github/ISSUE_TEMPLATE/
allowed-tools: Read, Write, Bash, Glob, AskUserQuestion
---

Walk the user through creating one or more GitHub issue forms using the YAML issue-forms schema (`name`, `description`, `title`, `labels`, `body`). Collect all templates before writing anything; write them all in a single approval step at the end. Model output on `.github/ISSUE_TEMPLATE/new.yml` in the current repo if it exists, otherwise use the canonical structure described here.

## Step 1: Locate `.github/ISSUE_TEMPLATE/`

```bash
ls .github/ISSUE_TEMPLATE/ 2>/dev/null || echo "(directory absent)"
```

Note whether the directory exists; if not, plan to create it during the write step.

## Step 2: Check for `config.yml`

If `.github/ISSUE_TEMPLATE/config.yml` is missing, offer to scaffold one:

```bash
git remote get-url origin 2>/dev/null || echo "(no remote)"
```

Derive the README URL from the remote (e.g. `https://github.com/owner/repo/blob/main/README.md`). Propose:

```yaml
blank_issues_enabled: false
contact_links:
  - name: Repository README
    url: <derived-url>
    about: Overview of this repository.
```

Show the proposed file in a fenced block and ask the user to approve or skip. Do not write yet.

## Step 3: Reconcile issue-tracking labels

Read the canonical label set from `plugins/github-toolkit/skills/github-scaffold/references/label-defaults.yml` (`category` + `triage` entries = the 9 labels this tool guarantees exist; `remove_if_present` = the fixed set of GitHub stock defaults to clean up). Create-if-missing only — never edit or delete a label that already exists under one of the 9 names, even if its color/description differs from the file.

### 3a — Detect the target repo's label mechanism

```bash
ls .github/labels.yml .github/labels.yaml 2>/dev/null
grep -rl 'labels\.ya\?ml' .github/workflows/ 2>/dev/null
```

### 3b — Branch A: declarative `labels.yml` + a referencing workflow exists

Read the existing file. Compute which of the 9 required labels (by `name:`) are missing and append only those entries — do not touch or remove any existing entries (e.g. `type:*` / `action:*`); the file's own completeness plus the workflow's delete behavior is what removes unused stock defaults, not this step.

Show the diff in a fenced block and ask the user to approve before writing.

Check whether the referencing workflow sets `skip-delete: false` explicitly. If it does not, tell the user their existing pipeline won't auto-remove unused GitHub stock defaults, and offer to run Branch B's deletion logic (below) for just the `remove_if_present` names.

### 3c — Branch B: no declarative file found

```bash
gh label list --json name,description,color --limit 100
```

Compute two lists against the live label set:
- **Create**: any of the 9 required labels (`category` + `triage`) not present, via `gh label create "<name>" --color <hex> --description "<description>"`.
- **Delete**: any name from `remove_if_present` that is present, via `gh label delete "<name>" --yes`. Never delete a label outside this fixed 7-name list, regardless of what else exists in the repo.

Show the full create/delete plan and get one approval before running anything. If both lists are empty, skip the prompt and note that labels are already in sync.

## Step 4: Select templates (multi-select)

Use `AskUserQuestion` with `multiSelect: true` to present the template catalogue. Show up to 5 items per question; if you have more than 5 candidates, split into sequential questions (page 1 of N, page 2 of N, …) before proceeding.

Standard catalogue (use these 4 options; "Other" is added automatically as the 5th slot):

| Option label | Description |
|---|---|
| Bug report | Reproducible defect with steps to reproduce, expected vs actual behaviour |
| Feature request | New capability or enhancement proposal |
| Question / Support | Usage question or request for help |
| Documentation | Doc errors, missing content, or typos |

If the user selects "Other", ask them to name the custom template type before continuing.

Record every selected type; proceed to Step 5 for each in turn.

## Step 5: Gather fields for each selected template

For each template type selected in Step 4, work through it in sequence:

### 5a — Pre-populate defaults

Propose sensible default metadata and body fields based on the template type:

- **Bug report**: title prefix `"[bug] "`, label `bug`, fields: Description (textarea, required), Steps to reproduce (textarea, required), Expected behaviour (textarea), Actual behaviour (textarea), Environment (input).
- **Feature request**: title prefix `"[feat] "`, label `feat`, fields: Problem statement (textarea, required), Proposed solution (textarea, required), Alternatives considered (textarea).
- **Question / Support**: title prefix `"[question] "`, label `support`, fields: What are you trying to do? (textarea, required), What have you tried? (textarea).
- **Documentation**: title prefix `"[docs] "`, label `docs`, fields: Page or section (input, required), Issue description (textarea, required), Suggested correction (textarea).
- **Custom type**: no defaults; ask the user for all metadata and fields.

Show the proposed metadata and field list in plain text and ask the user to confirm, remove, or add fields before generating YAML.

### 5b — Field schema

For each field that will appear in `body`, ensure:

| Key | Values |
|-----|--------|
| `type` | `dropdown`, `input`, `textarea`, or `markdown` |
| `id` | lowercase, hyphens/underscores only (omit for `markdown`) |
| `label` | display label |
| `description` | optional helper text |
| `placeholder` | optional (input/textarea) |
| `options` | required for `dropdown` — comma-separated list |
| `required` | `true` or `false` |

Suggest a `markdown` field for section separators or headers when appropriate.

After fields are confirmed for this template, move on to the next selected type (back to 5a) until all are done, then proceed to Step 6.

## Step 6: Render and validate all templates

For each template, print its full YAML in a labeled fenced block (`## <filename>`). Before showing each one, verify:

- Top-level keys present: `name`, `description`, `body`
- Each `body` entry has `type`, `id` (or omit `id` only for `markdown`), `attributes.label`
- `dropdown` entries have at least one option
- All `id` values match `^[a-z][a-z0-9_-]*$` and are unique within the template

Surface any violations as a list before the relevant YAML preview.

Example shape:

```yaml
name: "Bug report"
description: Report a reproducible bug.
title: "[bug] "
labels:
  - "bug"
body:
  - type: textarea
    id: description
    attributes:
      label: Description
      description: What happened?
    validations:
      required: true

  - type: dropdown
    id: severity
    attributes:
      label: Severity
      options:
        - low
        - medium
        - high
    validations:
      required: true
```

## Step 7: Approval gate, then write all

Show a summary list of all files that will be written (template files + `config.yml` if approved in Step 2). Ask the user to confirm once before writing anything.

On approval, write all files in one pass:

1. Create `.github/ISSUE_TEMPLATE/` if absent:
   ```bash
   mkdir -p .github/ISSUE_TEMPLATE
   ```
2. Write each template file.
3. Write `config.yml` if approved in Step 2.

Confirm each path written.
