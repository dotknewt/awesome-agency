# Guest Access Skill and Libvirt Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development to implement this accepted plan task-by-task. Use openai/gpt-5.6-sol for workers, task reviewers, and final review. Leave changes uncommitted. Steps use checkbox syntax.

**Goal:** Make project-in-VM requests reliably continue from VM lifecycle through verified access, transfer, and guest execution.

**Architecture:** Add a provider-neutral, independently installable `guest-access` skill and bundle it with libvirt-toolkit. Keep libvirt networking and QGA diagnostics in the provider skill, with an explicit evidence-bearing handoff. Use existing CLI tools; defer an SSH MCP.

**Tech Stack:** Markdown skills/references, JSON evaluation fixtures/catalog, Python unittest installation tests, existing OpenCode installer and libvirt MCP.

**Spec:** `docs/superpowers/specs/2026-09-16-guest-access-design.md`

**Execution status (2026-09-16):** Tasks 1–4 implemented and independently reviewed using
`openai/gpt-5.6-sol`. Work remains uncommitted. Final review and scoped corrections passed;
no open Critical/Important findings remain.
Validation: 100 OpenCode Python tests, 22 Node runtime tests, and 93 libvirt tests passed;
after the final documentation clarification, all 5 covering packaging tests and required
structural/catalog checks passed. Final synthetic response grading: 14/14 assertions
versus 12/14 for the complete baseline; metadata relevance choices 5/5. These are not live
guest-access or runtime auto-trigger measurements. Host compatibility retains 27 existing
warnings and 6 notes. Full reports live in the plan's ignored SDD workspace in the isolated
worktree `/tmp/opencode/awesome-agency-guest-access`.

Final review additionally corrected effective SSH trust-store handling, authentication order,
alternate key sources and multiplex reuse, and passt capability discovery. A reproducible
connection-free trust harness passed against deliberately permissive SSH configuration and
mocked SSH/SCP/rsync, including aliases, direct ports, and a trust path containing spaces.
Covering source-removal packaging tests passed after these corrections. The final independent
Scenario C response passed all six assertions on the corrected guidance. One nonblocking
scratch-harness assertion-strengthening suggestion is retained in the SDD ledger.

Delivered 23 incremental paths to the original checkout after baseline conflict checks.
All full suites were rerun on the delivered final tree: OpenCode Python100/100,
Node runtime22/22, and libvirt93/93 passed. Projection, generator, release-note,
plugin-root reference, and whitespace checks passed. Changes remain uncommitted.

## Global Constraints

- Preserve existing modified and untracked source; review incremental changes against a captured dirty-checkout baseline.
- Use `openai/gpt-5.6-sol` for every delegated role; controller owns all dispatches and records actual model/task identity.
- Do not stage, commit, push, or refresh another project's installation.
- Do not perform live VM mutations, real SSH connections, repository transfers, or guest setup; use synthetic evidence and temporary installation projects.
- Keep libvirt MCP lifecycle-only and preserve rejection, recovery, ownership, and power-state rules.
- Keep standalone skill installations self-contained and regenerate marketplace output rather than hand-editing it.
- Report lifecycle, prerequisites, SSH authentication, clone identity, transfer, and execution separately using verified / failed / untested / not applicable.
- Preserve distinctions between QGA diagnostics, SSH authentication, and normal-user project execution, and between prior Ubuntu and CachyOS evidence.

## Execution setup

- [ ] Create an isolated workspace containing the complete uncommitted libvirt baseline, not HEAD alone.
- [ ] Capture baseline hashes/content including untracked files and symlinks for incremental review and conflict-checked delivery.
- [ ] Create a plan-specific SDD ledger with model policy, task status, and preflight interface checks.
- [ ] Keep the baseline and ledger until uncommitted changes have been delivered and reviewed; no commit-based cleanup assumptions.

### Task 1: Standalone guest-access workflow

**Files:** Create `skills/guest-access/SKILL.md`, `skills/guest-access/references/ssh-workflow.md`, `skills/guest-access/evals/evals.json`, `skills/guest-access/evals/eval_queries.json`, `skills/guest-access/evals/files/access-scenarios.md`, and `opencode/tests/test_guest_access.py`. Regenerate `.claude-plugin/marketplace.json`.

**Interfaces:** Produce skill name `guest-access` and own relative `references/ssh-workflow.md`. Task 2 invokes it by name and bundles its entire directory. Consume a Markdown handoff with requested outcome; provider/host/owner/session/domain; connection origin; candidate endpoint/provenance; intended account/home; identity evidence; available tooling; per-stage progress. Unknown values stay unknown until investigated, not fabricated.

- [ ] Read AGENTS.md, skill-development/writing-skills guidance, `docs/specs/skills/eval.md`, existing installer tests, and the spec. Do not delegate.
- [ ] Add a meaningful standalone source-removal packaging test using a temporary marketplace/source/project and isolated HOME/XDG. Prove the new skill is discoverable and its own reference remains readable after removing only the copied source. Run the test before adding the skill and record the intended failure. Follow existing installer APIs; no production installer change is expected.
- [ ] Author lean skill metadata triggering existing-VM SSH, access diagnosis, project transfer, and guest tests. Lifecycle-only requests must not cause access setup. Body explains tool inventory before capability conclusions, endpoint/host-key verification, authentication, clone identity where relevant, guest account/home/cwd, transfer verification, requested command/exit/result, and separate status reporting.
- [ ] Author SSH reference with concrete parameterized examples for bounded noninteractive probes, trusted host-key verification (keyscan alone is not authentication), existing SSH config/agent compatibility, SCP/rsync transfer and destination verification, regular-user command execution with explicit cwd, and client/host/guest path distinctions. Avoid shell quoting bugs for user paths. Do not use root QGA as normal-user setup evidence.
- [ ] Author synthetic eval fixtures and three cases: (1) lifecycle-only MCP plus working QGA but missing passt forward, (2) guest-reported IP is host-local and refused, (3) remote libvirt host with project tests. Store task prompts, files, expected outputs, and behavior assertions in `evals/evals.json` following repository schema. These are scenarios for later controller-owned evaluation, not live commands.
- [ ] Add positive discovery queries for VM tests, refused SSH, copy-and-dry-run; negative queries for VM listing and powered-off snapshot, using `query` and `should_trigger` fields. Avoid requiring exact prose in tests.
- [ ] Run marketplace generator, standalone focused tests, and the skill validator. Record commands, exit statuses, red/green evidence, changed paths, and concerns in the task report.
- [ ] Obtain independent spec compliance and quality review through the controller. Behavioral baseline/with-skill runs are centralized in Task 3 to avoid duplicate evaluation dispatches.

### Task 2: Libvirt provider handoff and release

**Files:** Create `skills/libvirt-vms/references/guest-access.md` and directory symlink `plugins/libvirt-toolkit/skills/guest-access` targeting `../../../skills/guest-access`. Modify `skills/libvirt-vms/SKILL.md`, the three `references/{ubuntu,debian,cachyos}-template.md` files, `plugins/libvirt-toolkit/README.md`, `plugins/libvirt-toolkit/.claude-plugin/plugin.json`, `plugins/libvirt-toolkit/RELEASE-NOTES.md`, `plugins/libvirt-toolkit/mcp/libvirt/libvirt_mcp/server.py` (version only), `opencode/tests/test_libvirt_bundle.py`, and root `README.md`. Regenerate marketplace.

**Interfaces:** Consume Task 1's skill name and handoff fields. Produce provider-relative `references/guest-access.md` and a bundle that carries both skills. No new MCP tools or production renderer behavior.

- [ ] Read spec, current provider guidance, domain parser forwarding restrictions and clone sanitizer, existing packaging test, and relevant skill-development guidance. Do not delegate.
- [ ] Extend source-removal tests before bundling: both new references and skills must survive temporary source removal and generated discovery must include guest-access. Exercise bundle-plus-micro selection using the installer's existing collision policy, not a new policy. Record the intended red test.
- [ ] Update libvirt-vms description for project-in-VM requests. Add direct main-workflow handoff for new and existing clones requiring guest access; populate handoff fields and invoke guest-access by name. Keep lifecycle-only requests bounded.
- [ ] Write provider recipe: confirm host/user/session/domain; inspect networking and route from connection origin; for passt select an unused unprivileged virtualization-host port and configure persistent 127.0.0.1 TCP-to-22 forwarding while shut off; preserve graceful shutdown/ownership/recovery gates; start via MCP and verify actual endpoint. Check both active listeners and configured sibling forwards to reduce collisions; availability before start is not a reservation. Explain remote-host loopback access via a client tunnel and distinguish all path origins.
- [ ] Write optional read-only QGA diagnosis: inspect capabilities and domain identity, issue a read-only guest-exec probe, bounded polling of guest-exec-status, decode captured base64 stdout/stderr, require exited status and exitcode. Parameterize domain/session explicitly. Explain unavailable agent or disabled commands do not prove all guest transports are unavailable; QGA success is neither SSH authentication nor intended-user setup.
- [ ] Link OS references to the shared provider recipe while preserving OS-specific preparation facts. Document SSH trust/authentication and clone identity checks before project execution; report unavailable source/sibling comparisons. Do not change Ubuntu smoke-test claims into CachyOS claims.
- [ ] Add directory symlink with shell tooling (apply_patch cannot create symlinks). Update bundle README and root catalog description, standalone/bundled installation and refresh/restart guidance. No installed project is refreshed as part of implementation.
- [ ] In the same edit, bump inspected 1.0.6 to 1.0.7, add matching dated release notes explaining the skipped-access failure, and align existing MCP version metadata. If version changed concurrently, report the conflict rather than overwrite.
- [ ] Regenerate marketplace; run focused packaging and libvirt protocol/domain tests plus both skill validators. Record evidence in report. Obtain independent spec and quality review.

### Task 3: Independent behavioral evaluations

**Files:** Read skill eval JSON/fixtures and the preserved original libvirt skill; write baseline/with-skill responses and independent grading to this plan's ignored SDD workspace. Product fixes, if needed, belong to the original task worker followed by scoped re-review.

**Interfaces:** Consume `skills/guest-access/evals/evals.json`, `eval_queries.json`, provider reference, and original baseline. Produce a per-case verdict with evidence and honest limitations; no live proof claims.

- [ ] Controller dispatches fresh read-only child contexts for each baseline/with-skill scenario, all on openai/gpt-5.6-sol. Give only scenario evidence and allowed skill version, not expected answers. Tools may read explicitly supplied fixtures but may not connect to services or mutate hosts/guests.
- [ ] For baseline supply only the pre-change libvirt guidance; with-skill supply the skill pair and reachable references. Keep each scenario context isolated. User prompts request diagnosis/next actions and an evidence table, not execution against real hosts.
- [ ] Independently grade capability distinction, missing forward recognition, host-local routing interpretation, remote-host/client/guest separation, host-key/account/identity verification, and honest SSH/transfer/setup status. Grade negative discovery queries so listing/snapshot requests do not initiate guest access.
- [ ] Record failures and limitations. Route substantive fixes through workers, run covering checks and scoped reviews, then repeat only affected cases. Do not claim discovery execution or real guest access from model-response evaluation.

### Task 4: Distribution checks and final review

**Files:** Read completed product tree; write command results and final-review package/report to plan workspace. Add a short durable validation record to this plan after checks pass.

**Interfaces:** Consume completed task reports and incremental baseline-to-worktree diff including untracked files. Produce verified uncommitted changes and recorded remaining limitations.

- [ ] Run the following checks once on the final tree (repeat affected checks only after changes):

```sh
python3 .claude/skills/skill-development/scripts/validate_skill.py skills/guest-access/SKILL.md
python3 .claude/skills/skill-development/scripts/validate_skill.py skills/libvirt-vms/SKILL.md
python3 .github/scripts/generate-marketplace.py --check
python3 .github/scripts/check-plugin-root-refs.py
python3 .github/scripts/check-host-compat.py
python3 hooks/steward/scripts/release-notes-audit.py --all
python3 .github/scripts/check-opencode.py
python3 -m unittest discover -s opencode/tests -p 'test_*.py' -v
node --test opencode/tests/runtime.test.mjs
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s plugins/libvirt-toolkit/mcp/libvirt/tests -p 'test_*.py' -v
git diff --check
```

- [ ] Use pinned `mcp==2.2.0` and existing test prerequisites. If isolated Python lacks dependencies, run the exact commands through an isolated uv environment with the same requirements and record that adaptation. No global package installs.
- [ ] Obtain final independent review against the captured original tree, including untracked content, evaluation outcomes, and deferred findings. Reviewer need not rerun tests.
- [ ] Dispatch one consolidated fix wave if required, run covering checks, obtain scoped re-review, and record adjudications.
- [ ] Deliver only new incremental changes to the original checkout after verifying every affected original path still matches its baseline. Preserve worktree/baseline/ledger because there are no commits as a recovery record. Report files, tests, limitations, and consuming-project refresh instructions.

## Acceptance criteria

- Independently installable guest-access ships with libvirt-toolkit and retains all references after source removal.
- Project-in-VM requests explicitly continue into access; lifecycle-only requests do not.
- Missing MCP APIs are not mistaken for missing host tooling.
- Passt forwarding, host-local IP, and remote-host scenarios meet behavior assertions.
- QGA, SSH, identity, transfer, and execution claims remain separate and evidence-based.
- Required checks and independent reviews pass without live VM or SSH operations.
