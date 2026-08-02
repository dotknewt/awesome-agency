---
name: context-engineering
description: >
  Concepts and techniques for memory and context engineering with LLMs — covering three
  angles: supporting development (prompting patterns, RAG, context window management),
  exploiting LLMs (red-team and adversarial-testing techniques for educational use,
  including role-play framing, encoding obfuscation, many-shot persuasion, extraction
  attacks, and context poisoning), and defending LLMs (guardrails, context isolation,
  prompt injection mitigations). Use this skill when asked about context windows, prompt
  design, memory systems, RAG, prompt injection, jailbreaking (offensive red-team
  techniques or defensive mitigations), red-team techniques, adversarial prompt testing,
  context poisoning, or hardening LLM-backed applications.
---

# Context Engineering

A unified reference for the three-angle view of LLM context and memory: **supporting** development, **exploiting** weaknesses (red-team/educational use), and **defending** against attacks.

This file covers the supporting-development angle directly. The exploiting and defending angles each have their own reference file — load only the one the current task needs:

- **`references/exploiting.md`** — read when red-teaming a model or application, testing jailbreak/injection resistance, or otherwise working through attack techniques (prompt injection, context poisoning, jailbreak patterns, extraction attacks) for educational or adversarial-testing purposes.
- **`references/defending.md`** — read when hardening an LLM-backed application: input sanitization, context isolation, output validation, minimal-privilege context, or building defense-in-depth against prompt injection and jailbreaks.

A task that spans both angles (e.g. "give me jailbreak techniques to try, then the mitigations we need before launch") should load both files.

---

## Supporting Development

### Context Window Management

| Technique | When to use |
|---|---|
| **System prompt** | Stable instructions, persona, constraints — put here so caching amortizes cost |
| **Few-shot examples** | Task-specific patterns the model must mimic; 2–5 examples usually sufficient |
| **Turn compression** | Summarize earlier turns when nearing limit; keep the last N turns verbatim |
| **Context pruning** | Drop tool output beyond a size threshold; keep only parsed results |
| **Prefill** | For some providers, prefill the assistant turn to steer format (e.g., `{`) — see Gotchas below, support varies by model version |

### Memory Architectures

```
In-context memory    → everything in the prompt; cheapest for short sessions
External memory      → vector store / key-value; retrieved at query time (RAG)
Working memory       → structured scratchpad updated each step (tool calls, agent state)
Episodic memory      → log of past sessions; summarized and injected as context
Semantic memory      → distilled facts (user preferences, project facts) persisted in files
```

**RAG pattern:**
```
user query → embed → similarity search → top-K chunks → inject before query → generate
```

Key tradeoffs:
- **Recall vs. noise**: more chunks = higher recall but more irrelevant context
- **Chunk size**: small chunks = precise retrieval; large chunks = more coherent context
- **Reranking**: a cross-encoder pass after vector search cuts noise substantially

### Prompting for Code Generation

- **Specify language, framework, version** in the system prompt — models hallucinate APIs when left implicit.
- **Provide failing tests or expected output** rather than prose specs; the model can check its own work.
- **Chain of thought for complex logic**: ask the model to reason before writing code.
- **Constrain scope explicitly**: "only change X, leave Y unchanged" prevents scope creep.
- **Self-critique loop**: ask the model to review its own output before returning it — see `skills/agentic-eval` for the full self-critique/evaluator-optimizer pattern and rubric-based grading.

---

## Gotchas

Concrete, falsifiable facts that override the generic technique tables above and in the reference files:

- **OWASP's own two LLM Top-10 pages disagree.** `owasp.org/www-project-top-10-for-large-language-model-applications/` still serves the legacy 2023 list (LLM01: Prompt Injection, LLM02: Insecure Output Handling, LLM03: Training Data Poisoning, LLM04: Model Denial of Service, LLM05: Supply Chain Vulnerabilities, LLM06: Sensitive Information Disclosure, LLM07: Insecure Plugin Design, LLM08: Excessive Agency, LLM09: Overreliance, LLM10: Model Theft). The current list lives at `genai.owasp.org/llm-top-10/` and uses different identifiers and order: LLM01:2025 Prompt Injection, LLM02:2025 Sensitive Information Disclosure, LLM03:2025 Supply Chain, LLM04:2025 Data and Model Poisoning, LLM05:2025 Improper Output Handling, LLM06:2025 Excessive Agency, LLM07:2025 System Prompt Leakage, LLM08:2025 Vector and Embedding Weaknesses, LLM09:2025 Misinformation, LLM10:2025 Unbounded Consumption. Cite the `:2025` identifiers, not the legacy numbering.
- **Assistant-turn prefill is not universally supported, even within one provider's own model lineup.** Anthropic's post-4.6 Claude models (Sonnet 4.6 and later, including current Sonnet/Opus releases) reject a prefilled assistant message outright with a 400 error; only pre-4.6 models (Claude 3.5 Sonnet, Claude 3 Opus, etc.) still accept it. Don't assume the "prefill the assistant turn" technique works across all Claude versions — check the target model first, and prefer structured outputs (`output_config`) or system-prompt format instructions on newer models.
- **Base64/ROT13 obfuscation reliably defeats keyword- and semantic-guardrail models trained on plaintext English.** Research on Meta's Llama Guard found Base64-encoded harmful prompts collapsed its detection rate to roughly 12% — encoding obfuscation isn't a theoretical bypass, it's a measured one against a widely-used guardrail product.
- **Many-shot jailbreaking follows a power law, not a threshold.** Anthropic's research found the technique doesn't work with as few as 5 shots (example dialogues) in the prompt, but becomes consistently effective by around 256 shots, and is effective against most large language models, not just one vendor's.
- **Low-resource-language translation is its own bypass category, separate from encoding.** Published research on GPT-4 found translating a harmful prompt into Zulu or Scots Gaelic succeeded roughly 53% and 43% of the time respectively (combined ~79%), versus under 1% for the same prompts in English. Guardrails trained mostly on English and other high-resource languages don't generalize to this attack surface by default.

---

## References

- OWASP Top 10 for LLM Applications: https://owasp.org/www-project-top-10-for-large-language-model-applications/
- Simon Willison on prompt injection: https://simonwillison.net/series/prompt-injection/
- Anthropic prompt injection mitigations: https://platform.claude.com/docs/en/docs/test-and-evaluate/strengthen-guardrails/mitigate-jailbreaks
