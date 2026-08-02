---
name: agentic-eval
description: |
  Patterns and techniques for evaluating and improving AI agent outputs. Use this skill when:
  - The user makes an ad-hoc, in-session request to double-check, critique, or review your own output before finishing — e.g. "double check this," "critique your own answer before finishing," "review this before you're done" — even with no mention of building a pipeline or eval system
  - Implementing self-critique and reflection loops
  - Building evaluator-optimizer pipelines for quality-critical generation
  - Creating test-driven code refinement workflows
  - Designing rubric-based or LLM-as-judge evaluation systems
  - Adding iterative improvement to agent outputs (code, reports, analysis)
  - Measuring and improving agent response quality
---

# Agentic Evaluation Patterns

Patterns for self-improvement through iterative evaluation and refinement.

See also: `skills/context-engineering` for the retrieval/RAG side of context management, and the broader context-window/memory concepts these evaluation patterns operate within.

## Overview

Evaluation patterns enable agents to assess and improve their own outputs, moving beyond single-shot generation to iterative refinement loops.

```
Generate → Evaluate → Critique → Refine → Output
    ↑                              │
    └──────────────────────────────┘
```

## When to Use

- **Ad-hoc self-review**: The user asks you to double-check, critique, or review your own answer before finishing — e.g. "double check this," "critique your own answer before finishing," "review this before you're done" — no code or pipeline required, just apply the pattern in-session
- **Quality-critical generation**: Code, reports, analysis requiring high accuracy
- **Tasks with clear evaluation criteria**: Defined success metrics exist
- **Content requiring specific standards**: Style guides, compliance, formatting

---

> **Note on code snippets:** The Python in the patterns below (`llm(...)`, `run_tests(...)`, etc.) is illustrative pseudocode, not working code. `llm(...)` is a stand-in for whatever LLM call is actually available in context (an API client, a subagent invocation, a tool call), and `run_tests(...)` stands in for a real test runner. Adapt the structure and names to your environment — don't copy-paste expecting it to execute as-is.

## Pattern 1: Basic Reflection

Agent evaluates and improves its own output through self-critique.

```python
def reflect_and_refine(task: str, criteria: list[str], max_iterations: int = 3) -> str:
    """Generate with reflection loop."""
    output = llm(f"Complete this task:\n{task}")
    
    for i in range(max_iterations):
        # Self-critique
        critique = llm(f"""
        Evaluate this output against criteria: {criteria}
        Output: {output}
        Rate each: PASS/FAIL with feedback as JSON.
        """)
        
        critique_data = json.loads(critique)
        all_pass = all(c["status"] == "PASS" for c in critique_data.values())
        if all_pass:
            return output
        
        # Refine based on critique
        failed = {k: v["feedback"] for k, v in critique_data.items() if v["status"] == "FAIL"}
        output = llm(f"Improve to address: {failed}\nOriginal: {output}")
    
    return output
```

**Key insight**: Use structured JSON output for reliable parsing of critique results.

---

## Pattern 2: Evaluator-Optimizer

Separate generation and evaluation into distinct components for clearer responsibilities.

```python
class EvaluatorOptimizer:
    def __init__(self, score_threshold: float = 0.8):
        self.score_threshold = score_threshold
    
    def generate(self, task: str) -> str:
        return llm(f"Complete: {task}")
    
    def evaluate(self, output: str, task: str) -> dict:
        return json.loads(llm(f"""
        Evaluate output for task: {task}
        Output: {output}
        Return JSON: {{"overall_score": 0-1, "dimensions": {{"accuracy": ..., "clarity": ...}}}}
        """))
    
    def optimize(self, output: str, feedback: dict) -> str:
        return llm(f"Improve based on feedback: {feedback}\nOutput: {output}")
    
    def run(self, task: str, max_iterations: int = 3) -> str:
        output = self.generate(task)
        for _ in range(max_iterations):
            evaluation = self.evaluate(output, task)
            if evaluation["overall_score"] >= self.score_threshold:
                break
            output = self.optimize(output, evaluation)
        return output
```

---

## Pattern 3: Code-Specific Reflection

Test-driven refinement loop for code generation.

```python
class CodeReflector:
    def reflect_and_fix(self, spec: str, max_iterations: int = 3) -> str:
        code = llm(f"Write Python code for: {spec}")
        tests = llm(f"Generate pytest tests for: {spec}\nCode: {code}")
        
        for _ in range(max_iterations):
            result = run_tests(code, tests)
            if result["success"]:
                return code
            code = llm(f"Fix error: {result['error']}\nCode: {code}")
        return code
```

---

## Evaluation Strategies

### Outcome-Based
Evaluate whether output achieves the expected result.

```python
def evaluate_outcome(task: str, output: str, expected: str) -> str:
    return llm(f"Does output achieve expected outcome? Task: {task}, Expected: {expected}, Output: {output}")
```

### LLM-as-Judge
Use LLM to compare and rank outputs.

```python
def llm_judge(output_a: str, output_b: str, criteria: str) -> str:
    return llm(f"Compare outputs A and B for {criteria}. Which is better and why?")
```

### Rubric-Based
Score outputs against weighted dimensions.

```python
RUBRIC = {
    "accuracy": {"weight": 0.4},
    "clarity": {"weight": 0.3},
    "completeness": {"weight": 0.3}
}

def evaluate_with_rubric(output: str, rubric: dict) -> float:
    scores = json.loads(llm(f"Rate 1-5 for each dimension: {list(rubric.keys())}\nOutput: {output}"))
    return sum(scores[d] * rubric[d]["weight"] for d in rubric) / 5
```

---

## Best Practices

| Practice | Rationale |
|----------|-----------|
| **Clear criteria** | Define specific, measurable evaluation criteria upfront |
| **Iteration limits** | Set max iterations (3-5) to prevent infinite loops |
| **Convergence check** | Stop if output score isn't improving between iterations |
| **Log history** | Keep full trajectory for debugging and analysis |
| **Structured output** | Use JSON for reliable parsing of evaluation results |

---

## Gotchas

- **Self-critique rubber-stamps itself.** LLM self-critique frequently returns all-PASS on the first pass unless explicitly prompted to be adversarial. Ask the critique step to find at least one FAIL if any genuinely exists, or phrase the prompt as "find problems with this output" rather than "is this output good."
- **Critique JSON often fails to parse.** `json.loads(critique)` (Pattern 1) and similar calls frequently throw on malformed output — trailing commentary, markdown code fences, truncated JSON. Wrap the parse in try/except and, on failure, re-prompt the model with the exact parse error rather than silently retrying or giving up.
- **Score thresholds are arbitrary until calibrated.** A `score_threshold` like `0.8` (Pattern 2) or a rubric cutoff has no inherent meaning — it's a guess. Calibrate it against a handful of human-graded examples (does a 0.8 actually correspond to output a human would accept?) before trusting it to gate output.

---

## Quick Start Checklist

```markdown
## Evaluation Implementation Checklist

### Setup
- [ ] Define evaluation criteria/rubric
- [ ] Set score threshold for "good enough"
- [ ] Configure max iterations (default: 3)

### Implementation
- [ ] Implement generate() function
- [ ] Implement evaluate() function with structured output
- [ ] Implement optimize() function
- [ ] Wire up the refinement loop

### Safety
- [ ] Add convergence detection
- [ ] Log all iterations for debugging
- [ ] Handle evaluation parse failures gracefully
```

---

## Available Scripts

- **`scripts/rubric_grader.py`** — Standalone, stdlib-only implementation of the rubric-based scoring pattern (see Pattern 2 / Rubric-Based above). Takes a JSON payload of weighted dimension scores on stdin or via `--input`, validates it, computes the weighted overall score, and checks it against a threshold. Run `python3 scripts/rubric_grader.py --help` for usage; use it directly, or as a model for a project-specific grading script.

---

## See Also

This skill is a pure pattern reference — code sketches meant to be adapted, not an executable system. A related but different-altitude capability exists elsewhere in this marketplace: an agent-based verification pipeline (`agents/agent-doublecheck`) that actually extracts claims from AI output, finds external sources, and flags hallucination risk. Reach for that when you need AI output checked against the outside world; reach for the patterns here when you need an iterative generate/evaluate/refine loop, self-critique, or a rubric/judge scoring mechanism.