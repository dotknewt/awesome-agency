# /// script
# requires-python = ">=3.9"
# dependencies = []
# ///
"""rubric_grader.py — score a rubric-based evaluation payload and check it against a threshold.

Implements the JSON-based rubric-scoring pattern described in agentic-eval's
SKILL.md (Pattern 2 / "Rubric-Based" evaluation strategy): weighted
dimensions, each scored on a fixed scale, combined into a single overall
score and compared against a "good enough" threshold.

This script does NOT call an LLM. It grades a scoring payload that has
already been produced (e.g. by an LLM judge) — the kind of JSON you'd get
back from a prompt like:

    Rate 1-5 for each dimension: [accuracy, clarity, completeness]

Input schema (JSON object), read from --input FILE, --input -, or stdin:

    {
      "dimensions": {
        "accuracy":     {"weight": 0.4, "score": 4},
        "clarity":      {"weight": 0.3, "score": 5},
        "completeness": {"weight": 0.3, "score": 3}
      },
      "scale": 5
    }

- "dimensions": required. Map of dimension name -> {"weight": float, "score": number}.
  Weights must be non-negative and sum to 1.0 (+/- 0.01 tolerance).
  Scores must fall within [0, scale].
- "scale": optional. The max value a single dimension score can take
  (default 5, matching evaluate_with_rubric() in SKILL.md). Can be
  overridden with --scale, which takes precedence over the payload.

Output: a single JSON object on stdout with the overall score, per-dimension
contributions, and pass/fail against --threshold. All diagnostics, warnings,
and errors go to stderr so stdout stays machine-parseable.

Exit codes:
  0  PASS  — input parsed and validated, overall_score >= threshold
  1  ERROR — invalid JSON, missing/malformed fields, or weights that don't
             sum to 1.0 within tolerance ("parse failure" in the broad sense:
             the payload could not be trusted enough to grade)
  2  (reserved by argparse for CLI usage errors, e.g. unknown flags)
  3  FAIL  — input parsed and validated fine, but overall_score < threshold

Examples:
  echo '{"dimensions": {"accuracy": {"weight": 0.5, "score": 5},
                         "clarity":  {"weight": 0.5, "score": 3}}}' \\
    | python3 scripts/rubric_grader.py

  python3 scripts/rubric_grader.py --input scores.json --threshold 0.75

  python3 scripts/rubric_grader.py --input scores.json --scale 10 --threshold 0.9
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


DEFAULT_SCALE = 5
DEFAULT_THRESHOLD = 0.8
WEIGHT_TOLERANCE = 0.01

EXIT_PASS = 0
EXIT_INVALID_INPUT = 1
# EXIT code 2 is reserved by argparse for CLI usage errors.
EXIT_BELOW_THRESHOLD = 3


class RubricInputError(ValueError):
    """Raised when the rubric payload is malformed or fails validation."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rubric_grader.py",
        description=(
            "Score a rubric-based evaluation payload (weighted dimensions, "
            "each rated on a fixed scale) and check it against a threshold."
        ),
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input",
        metavar="FILE",
        default="-",
        help=(
            "Path to a JSON file with the rubric payload. Use '-' (default) "
            "to read from stdin."
        ),
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Minimum overall_score (0-1) required to PASS (default: {DEFAULT_THRESHOLD}).",
    )
    parser.add_argument(
        "--scale",
        type=float,
        default=None,
        help=(
            "Max value a single dimension score can take. Overrides any "
            f"'scale' field in the input payload. Defaults to {DEFAULT_SCALE} "
            "if neither is provided."
        ),
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="Indent level for the JSON printed to stdout (default: 2). Use 0 for compact output.",
    )
    return parser


def read_input_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError as exc:
        raise RubricInputError(f"could not read input file '{path}': {exc}") from exc


def parse_payload(raw_text: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RubricInputError(
            f"input is not valid JSON: {exc.msg} (line {exc.lineno}, column {exc.colno}). "
            "If this came from an LLM, the raw text may include markdown code fences or "
            "trailing commentary — strip everything outside the outermost {...} and retry."
        ) from exc

    if not isinstance(payload, dict):
        raise RubricInputError(f"expected a JSON object at the top level, got {type(payload).__name__}")

    return payload


def validate_and_score(payload: dict[str, Any], scale_override: float | None) -> dict[str, Any]:
    dimensions = payload.get("dimensions")
    if not isinstance(dimensions, dict) or not dimensions:
        raise RubricInputError(
            "payload must include a non-empty 'dimensions' object, e.g. "
            '{"dimensions": {"accuracy": {"weight": 0.5, "score": 4}, ...}}'
        )

    scale = scale_override if scale_override is not None else payload.get("scale", DEFAULT_SCALE)
    try:
        scale = float(scale)
    except (TypeError, ValueError) as exc:
        raise RubricInputError(f"'scale' must be a number, got {payload.get('scale')!r}") from exc
    if scale <= 0:
        raise RubricInputError(f"'scale' must be positive, got {scale}")

    weight_sum = 0.0
    contributions: dict[str, Any] = {}

    for name, spec in dimensions.items():
        if not isinstance(spec, dict):
            raise RubricInputError(f"dimension '{name}' must be an object with 'weight' and 'score'")

        if "weight" not in spec or "score" not in spec:
            raise RubricInputError(f"dimension '{name}' is missing 'weight' and/or 'score'")

        try:
            weight = float(spec["weight"])
        except (TypeError, ValueError) as exc:
            raise RubricInputError(f"dimension '{name}' has a non-numeric weight: {spec['weight']!r}") from exc

        try:
            score = float(spec["score"])
        except (TypeError, ValueError) as exc:
            raise RubricInputError(f"dimension '{name}' has a non-numeric score: {spec['score']!r}") from exc

        if weight < 0:
            raise RubricInputError(f"dimension '{name}' has a negative weight: {weight}")
        if not (0 <= score <= scale):
            raise RubricInputError(
                f"dimension '{name}' has score {score}, outside the valid range [0, {scale}]"
            )

        weight_sum += weight
        contributions[name] = {"weight": weight, "score": score, "weighted": (weight * score) / scale}

    if abs(weight_sum - 1.0) > WEIGHT_TOLERANCE:
        raise RubricInputError(
            f"dimension weights sum to {weight_sum:.4f}, expected 1.0 (+/- {WEIGHT_TOLERANCE}). "
            "Rubric dimensions must be weighted and sum to 1 — fix the weights and retry rather "
            "than trusting an unnormalized score."
        )

    overall_score = sum(c["weighted"] for c in contributions.values())

    return {
        "overall_score": round(overall_score, 4),
        "scale": scale,
        "weight_sum": round(weight_sum, 4),
        "dimensions": {
            name: {
                "weight": c["weight"],
                "score": c["score"],
                "contribution": round(c["weighted"], 4),
            }
            for name, c in contributions.items()
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        raw_text = read_input_text(args.input)
        payload = parse_payload(raw_text)
        result = validate_and_score(payload, args.scale)
    except RubricInputError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INVALID_INPUT

    passed = result["overall_score"] >= args.threshold
    result["threshold"] = args.threshold
    result["passed"] = passed

    indent = args.indent if args.indent > 0 else None
    print(json.dumps(result, indent=indent))

    verdict = "PASS" if passed else "FAIL"
    print(
        f"{verdict}: overall_score={result['overall_score']} threshold={args.threshold} "
        f"(scale={result['scale']}, weight_sum={result['weight_sum']})",
        file=sys.stderr,
    )

    return EXIT_PASS if passed else EXIT_BELOW_THRESHOLD


if __name__ == "__main__":
    sys.exit(main())
