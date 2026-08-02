# work-objects-toolkit

Evidence-linked work objects for code-change tasks: one `work/<id>-<slug>/`
directory per task keeps the spec, the captured diff, the captured test
output, a run manifest, and the review decision together as a single
inspectable object — so a reviewer checks evidence instead of trusting a
summary. Status transitions are gated by a checker script and enforced by
a PreToolUse hook, not narrated.

## Anatomy of a work object

```
work/CHG-20260801-fix-login/
├── spec.md                   # written BEFORE code; status: draft|in-review|approved|rejected
├── evidence/
│   ├── diff.patch            # literal `git diff <before>..<after>` output
│   ├── test-output.txt       # literal stdout+stderr of the test command
│   └── run-manifest.json     # real SHAs, branch, timestamp, exact commands
└── review.md                 # decision citing each evidence file by name
```

## What ships

| Component | Path | What it does |
|---|---|---|
| `work-object-guard` skill | `skills/work-object-guard/` | Scaffold → capture evidence → gate `in-review` → review → gate `approved` |
| Checker | `scripts/check_preconditions.py` | Mechanical gate: files exist and are non-empty, manifest valid, `commit_after` == actual HEAD, SHAs exist in history, diff.patch is real git output touching only actually-changed files, review cites every evidence file and decides `approved` |
| Status gate hook | `scripts/work-object-status-gate.sh` | PreToolUse(Write\|Edit): blocks flipping `status:` to `in-review`/`approved` in `work/*/spec.md` or `work/*/review.md` unless the checker passes |

## Hook behavior

| Write/Edit target | New status | Gate applied |
|---|---|---|
| anything outside `work/*/spec.md`, `work/*/review.md` | — | allowed (hook exits immediately) |
| `work/*/spec.md` | `draft` / other | allowed |
| `work/*/spec.md` | `in-review` | checker `--transition in-review` |
| `work/*/spec.md` | `approved` | checker `--transition approved` |
| `work/*/review.md` | `in-review`/`approved` | checker `--transition in-review` (the `approved` check needs review.md on disk, which this write is creating; the full gate fires on the spec.md flip) |

Exit 0 = allowed, exit 2 = blocked with the checker's `BLOCKED:` reason fed
back to Claude.

**Known limitation:** the hook intercepts the Write/Edit tools only — a
`bash -c 'echo ... > work/x/spec.md'` write bypasses it. The skill's hard
rule and the AGENTS.md drop-in (`skills/work-object-guard/references/agents-md-snippet.md`)
remain the guard for that path.

## Quick start

```bash
# 1. Scaffold
id="CHG-$(date +%Y%m%d)-my-change"
mkdir -p "work/$id/evidence"
cp "<plugin-root>/skills/work-object-guard/references/spec_template.md" "work/$id/spec.md"

# 2. After making the change, capture evidence (never hand-write it)
git diff <before>..<after> > "work/$id/evidence/diff.patch"
pytest -q > "work/$id/evidence/test-output.txt" 2>&1
# ...write evidence/run-manifest.json with the real SHAs

# 3. Gate transitions
python3 "<plugin-root>/scripts/check_preconditions.py" "work/$id" --transition in-review
python3 "<plugin-root>/scripts/check_preconditions.py" "work/$id" --transition approved
```

## Testing the hook manually

```bash
export CLAUDE_PLUGIN_ROOT=$(pwd)
printf '%s' '{"tool_name":"Edit","tool_input":{"file_path":"work/CHG-1-x/spec.md","old_string":"status: draft","new_string":"status: in-review"}}' \
  | bash scripts/work-object-status-gate.sh
echo "exit: $?"
```

## Relationship to superpowers

`subagent-driven-development` produces ephemeral evidence (gitignored
`.superpowers/sdd/` review packages); `verification-before-completion`
states evidence-before-claims as prose. Work objects are the durable,
git-tracked, mechanically enforced version of the same discipline — use
them when the evidence should outlive the session. See
`specs/work-objects/Work-Object-Specification.md` in the agency repo for
the full format specification.
