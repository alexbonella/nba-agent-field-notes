"""Deterministic check: every number in the final answer must trace to
the input or a tool_result this run, or be derivable from two grounded
numbers (a margin). Necessary but not sufficient proof of correct
attribution - see judged.py for that. Known limitation classes are
logged in DECISIONS.md, not here."""

import re

from strands_evals.evaluators.evaluator import Evaluator
from strands_evals.types import EvaluationData, EvaluationOutput
from strands_evals.types.trace import Session, SpanType

_NUMBER_RE = re.compile(r"\d+")
_LEADING_LIST_MARKER_RE = re.compile(r"^\s*\d+\.\s+")

# The only digit sequence in any real NBA team name (Philadelphia
# 76ers) - not a stat, always grounded. Narrow on purpose: a fixed set
# of one, not a general "ignore digits near a capitalized word" rule.
_TEAM_NAME_DIGIT_TOKENS = {"76"}


def _numbers_in_tool_results(trajectory: Session) -> set[str]:
    numbers: set[str] = set()
    for trace in trajectory.traces:
        for span in trace.spans:
            if span.span_type != SpanType.TOOL_EXECUTION:
                continue
            tool_result = getattr(span, "tool_result", None)
            if tool_result and tool_result.content:
                numbers |= set(_NUMBER_RE.findall(tool_result.content))
    return numbers


def _derivable_from_pair(number: str, grounded: set[str]) -> bool:
    """True if `number` is the sum or absolute difference of two
    already-grounded numbers (e.g. a margin of victory)."""
    try:
        target = int(number)
        values = [int(g) for g in grounded]
    except ValueError:
        return False
    for i, a in enumerate(values):
        for b in values[i + 1:]:
            if target in (a + b, abs(a - b)):
                return True
    return False


def _numbers_in_answer(answer: str) -> set[str]:
    # Strip markdown list markers ("1. ") so list numbering isn't
    # read as a stated fact.
    cleaned_lines = [
        _LEADING_LIST_MARKER_RE.sub("", line) for line in answer.splitlines()
    ]
    return set(_NUMBER_RE.findall("\n".join(cleaned_lines)))


class NumericGroundingEvaluator(Evaluator[str, str]):
    """Opt in per scenario via `expect: {grounded_in_tool_output: true}`
    - only meaningful for scenarios that call a data tool at all."""

    def evaluate(
        self, evaluation_case: EvaluationData[str, str]
    ) -> list[EvaluationOutput]:
        expect = (evaluation_case.metadata or {}).get("expect", {})
        if not expect.get("grounded_in_tool_output"):
            return [
                EvaluationOutput(
                    score=1.0,
                    test_pass=True,
                    reason="scenario did not request a grounding check",
                    label="grounded_in_tool_output",
                )
            ]

        trajectory = evaluation_case.actual_trajectory
        if not isinstance(trajectory, Session):
            return [
                EvaluationOutput(
                    score=0.0,
                    test_pass=False,
                    reason=(
                        "no trajectory captured - was TracedHandler used?"
                    ),
                    label="grounded_in_tool_output",
                )
            ]

        # Numbers already in the question are an echo, not a new claim.
        grounded = _numbers_in_tool_results(trajectory)
        grounded |= _numbers_in_answer(str(evaluation_case.input or ""))
        grounded |= _TEAM_NAME_DIGIT_TOKENS
        stated = _numbers_in_answer(evaluation_case.actual_output or "")
        ungrounded = {
            n
            for n in (stated - grounded)
            if not _derivable_from_pair(n, grounded)
        }

        return [
            EvaluationOutput(
                score=1.0 if not ungrounded else 0.0,
                test_pass=not ungrounded,
                reason=(
                    "every number in the answer appeared in some tool's "
                    "raw output this run"
                    if not ungrounded
                    else (
                        "numbers in the answer with no match in any "
                        f"tool_result: {sorted(ungrounded)}"
                    )
                ),
                label="grounded_in_tool_output",
            )
        ]
