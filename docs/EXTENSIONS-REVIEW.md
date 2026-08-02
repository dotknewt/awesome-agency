# Extensions Functionality Review

Advisory review of the extensions cataloged in `docs/EXTENSIONS.md` — looking for merge/combine/remove/extend opportunities. Findings are evidence-based (read the actual skill/agent bodies, not just descriptions), ordered by confidence/impact. This is recommendations only; no code changes were made as part of this review.

## Findings

### 1. `grilling` / `grill-me` / `grill-with-docs` — not duplicates, keep as-is (no action)

**Finding:** These read as three overlapping skills from their descriptions alone, but they aren't. `grilling` (engineering-toolkit) is the actual implementation (7 lines of interview instructions). `grill-me` and `grill-with-docs` are both `disable-model-invocation: true` one-liners that just say "Run a `/grilling` session" — they exist purely as explicit slash-command aliases so a user can type `/grill-me` without the model auto-triggering on the word "grill" elsewhere. `grill-with-docs` additionally chains in `/domain-modeling` to produce ADRs/glossary alongside the interview.

**Evidence:** `skills/grill-me/SKILL.md` and `skills/grill-with-docs/SKILL.md` are 7-8 lines each, entirely delegation.

**Recommendation:** Keep as-is. This is a legitimate alias pattern (thin explicit-invocation entry points over one implementation), not duplication.

### 2. `doublecheck` skill vs `doublecheck` (Doublecheck) agent — intentional pair, minor doc gap

**Finding:** Both exist in `agent-doublecheck` and do the same three-layer verification pipeline. The plugin's own `README.md` documents the split clearly — skill = core pipeline (one-shot or persistent inline mode), agent = interactive mode for follow-up questions and deeper investigation. So this is intentional, not redundant.

**Evidence:** `plugins/agent-doublecheck/README.md` has an explicit table distinguishing the two; `skills/doublecheck/SKILL.md` itself never mentions the agent.

**Recommendation:** Extend, low priority — add a one-line pointer in `SKILL.md`'s Activation section ("for interactive follow-up investigation, see the `Doublecheck` agent") so the distinction is visible to anyone who only reads the skill, not just the plugin README.

### 3. `dockerize-mcp-server` skill vs agent — well-composed, no action

**Finding:** Same name, same domain, but a real layering: the skill is inline how-to guidance including a `multi-stage-dockerfile` cross-reference; the agent explicitly reads the skill's own files (`SKILL.md`, its `references/dockerfile-templates.md` and `references/docker-mcp-gateway.md`) as its knowledge source, then runs in an isolated context window for large source repos. The docker-toolkit README also documents both.

**Evidence:** `agents/dockerize-mcp-server/dockerize-mcp-server.md:50-52` reads the skill's own files by path.

**Recommendation:** No action. This is a good example of an agent built as a thin isolated-context wrapper over a skill, not a maintenance burden.

### 4. `eyeball` vs `doublecheck` — different verification target, keep both

**Finding:** Both are "verify claims" skills and could plausibly collide on trigger phrases like "fact-check" or "verify this," but they solve different problems. `doublecheck` verifies AI-generated *output* against external web sources (citations, statistics, hallucination patterns) and produces a text/inline report with source links. `eyeball` verifies an existing *document's* claims against its own source material (a contract, PDF, webpage) and produces a Word doc with highlighted screenshot proof — visual citation, not web search.

**Evidence:** Full SKILL.md read of both; `doublecheck` never touches documents-as-source, `eyeball` never does web search for external corroboration.

**Recommendation:** Keep both. If trigger collisions turn out to be a real problem in practice (e.g. "fact-check this contract" firing the wrong one), tighten the description disambiguation rather than merging — the underlying workflows and output formats are too different to combine.

### 5. `agent-ember`'s four `from-the-other-side-*` skills — keep separate

**Finding:** These are substantive, distinct persona profiles (85-123 lines each) for different named collaborators (Anitta, Quinn, Vega, Wiggins), each with its own identity, default mode, and optimization criteria that Ember draws on contextually. They aren't near-duplicate content wearing different names — each is written from a different collaborator's specific working relationship.

**Evidence:** Read all four in full; content divergence is substantial (e.g. Anitta emphasizes query-authoring standards and rigorous challenge, Vega is a first-person partnership narrative, Wiggins is about narrative/communication framing).

**Recommendation:** Keep separate. Collapsing into one parameterized skill would blur the point of having distinct persona lenses, and at this size (four ~100-line files) there's no real maintenance cost to keeping them apart.

### 6. Four `ludus-*` skills — keep split, low-priority merge candidate only if triggering misfires

**Finding:** `ludus-cli`, `ludus-environment-guide`, `ludus-range-config`, `ludus-troubleshoot` are each small (30-63 lines) and scoped to one clearly distinct user intent — running CLI commands, choosing a pre-built lab, authoring range config YAML, and diagnosing failures, respectively.

**Evidence:** Descriptions and bodies map cleanly to non-overlapping trigger conditions with no shared content between them.

**Recommendation:** Keep split. Combined they're only ~183 lines, so a merge wouldn't meaningfully reduce content, and splitting lets the model load only the relevant slice for a given question (progressive disclosure). Revisit only if trigger selection between them proves unreliable in practice.

### 7. `codebase-design` / `domain-modeling` / `improve-codebase-architecture` — well-composed, no action

**Finding:** This looks like a cluster from the names, but it's a deliberate three-layer composition: `codebase-design` supplies shared architecture vocabulary (module, interface, depth, seam), `domain-modeling` maintains the project's domain glossary/ADRs, and `improve-codebase-architecture` is the end-to-end scan-and-report workflow that explicitly runs both of the others and requires using their vocabulary "exactly" in its output.

**Evidence:** `skills/improve-codebase-architecture/SKILL.md` lines 10-13 explicitly instruct running `/codebase-design` and reference `domain-modeling`'s `CONTEXT.md`/ADR outputs.

**Recommendation:** No action — a positive example of extension via composition rather than duplication.

### 8. `instruction-management` / `restructure-instructions` / `revise-instructions` — intentional pairing, no action

**Finding:** Same plugin, adjacent names, but distinct lifecycle stages: `instruction-management` audits AGENTS.md/CLAUDE.md against a quality rubric, `restructure-instructions` moves content closer to where it's used (reduce root bloat), and `revise-instructions` captures new session learnings into the file. Not overlapping — three phases of the same maintenance job.

**Recommendation:** No action.

### 9. `to-issues` vs `to-prd` — intentional inverse pair, no action

**Finding:** `to-issues` breaks a plan/spec/PRD into tracker issues; `to-prd` synthesizes a conversation into a PRD and publishes it. Opposite directions of the same PRD↔issues pipeline, not overlapping — flagged in the initial inventory only because the names are easy to confuse at a glance.

**Recommendation:** No action.

## Summary of recommended changes

Only one concrete action came out of this review, and it's small:

- **`skills/doublecheck/SKILL.md`**: add a one-line cross-reference to the `Doublecheck` agent in the Activation section, so the skill/agent split is visible without needing to open the plugin README.

Everything else reviewed here is either a legitimate alias pattern, a well-composed layering, or an intentional pairing — the marketplace's apparent "near-duplicates" mostly turn out to be deliberate design once read in full. No merges, removals, or consolidations are recommended at this time.
