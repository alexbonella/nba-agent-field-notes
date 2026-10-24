"""Checks every key in a scenario's `expect` block against the
execution state task.py recorded (tools_used, iterations, stop_reason,
...). Deterministic - see judged.py for what this can't answer."""

from strands_evals.evaluators.evaluator import Evaluator
from strands_evals.evaluators.trajectory_evaluator import in_order_match_scorer
from strands_evals.types import EvaluationData, EvaluationOutput


class ExecutionExpectationEvaluator(Evaluator[str, str]):
    """Reads `evaluation_case.metadata["expect"]` (from the scenario YAML)
    and `evaluation_case.actual_environment_state` (written by task.py)
    and emits one EvaluationOutput per expectation key present, so a
    scenario's report shows exactly which check failed, not just a
    single pass/fail for the whole case."""

    def evaluate(
        self, evaluation_case: EvaluationData[str, str]
    ) -> list[EvaluationOutput]:
        expect = (evaluation_case.metadata or {}).get("expect", {})
        state_entries = evaluation_case.actual_environment_state or []
        state = next(
            (e.state for e in state_entries if e.name == "execution"), {}
        )

        outputs: list[EvaluationOutput] = []

        if "tools_any_order" in expect:
            wanted = set(expect["tools_any_order"])
            got = set(state.get("tools_used", []))
            missing = wanted - got
            outputs.append(
                EvaluationOutput(
                    score=1.0 if not missing else 0.0,
                    test_pass=not missing,
                    reason=(
                        f"called {sorted(got)}, expected at least "
                        f"{sorted(wanted)}"
                        if missing
                        else f"called {sorted(got)}, matches expectation"
                    ),
                    label="tools_any_order",
                )
            )

        if "tools_in_order" in expect:
            wanted_order = expect["tools_in_order"]
            got_order = state.get("tool_order", [])
            order_score = in_order_match_scorer(got_order, wanted_order)
            outputs.append(
                EvaluationOutput(
                    score=order_score,
                    test_pass=order_score == 1.0,
                    reason=(
                        f"tool_order={got_order}, "
                        f"expected in order {wanted_order} "
                        f"(score={order_score})"
                    ),
                    label="tools_in_order",
                )
            )

        if "stop_reason" in expect:
            wanted_reason = expect["stop_reason"]
            got_reason = state.get("stop_reason")
            outputs.append(
                EvaluationOutput(
                    score=1.0 if got_reason == wanted_reason else 0.0,
                    test_pass=got_reason == wanted_reason,
                    reason=(
                        f"stop_reason={got_reason!r}, "
                        f"expected {wanted_reason!r}"
                    ),
                    label="stop_reason",
                )
            )

        if "max_iterations" in expect:
            ceiling = expect["max_iterations"]
            got_iterations = state.get("iterations", 0)
            outputs.append(
                EvaluationOutput(
                    score=1.0 if got_iterations <= ceiling else 0.0,
                    test_pass=got_iterations <= ceiling,
                    reason=f"iterations={got_iterations}, ceiling={ceiling}",
                    label="max_iterations",
                )
            )

        if "min_failed_tools" in expect:
            floor = expect["min_failed_tools"]
            got_failed = state.get("failed_tools", 0)
            outputs.append(
                EvaluationOutput(
                    score=1.0 if got_failed >= floor else 0.0,
                    test_pass=got_failed >= floor,
                    reason=(
                        f"failed_tools={got_failed}, "
                        f"expected at least {floor}"
                    ),
                    label="min_failed_tools",
                )
            )

        if "max_failed_tools" in expect:
            ceiling = expect["max_failed_tools"]
            got_failed = state.get("failed_tools", 0)
            outputs.append(
                EvaluationOutput(
                    score=1.0 if got_failed <= ceiling else 0.0,
                    test_pass=got_failed <= ceiling,
                    reason=(
                        f"failed_tools={got_failed}, "
                        f"expected at most {ceiling}"
                    ),
                    label="max_failed_tools",
                )
            )

        if "min_players_compared" in expect:
            floor = expect["min_players_compared"]
            calls = state.get("tool_arguments", {}).get(
                "compare_players", []
            )
            got_players = max(
                (len(c.get("players", [])) for c in calls), default=0
            )
            outputs.append(
                EvaluationOutput(
                    score=1.0 if got_players >= floor else 0.0,
                    test_pass=got_players >= floor,
                    reason=(
                        f"compare_players called with {got_players} "
                        f"player(s), expected at least {floor}"
                    ),
                    label="min_players_compared",
                )
            )

        if "must_not_contain" in expect:
            forbidden = expect["must_not_contain"]
            answer = (evaluation_case.actual_output or "").lower()
            hits = [term for term in forbidden if term.lower() in answer]
            outputs.append(
                EvaluationOutput(
                    score=1.0 if not hits else 0.0,
                    test_pass=not hits,
                    reason=(
                        "none of the forbidden terms appeared"
                        if not hits
                        else f"answer contains forbidden term(s): {hits}"
                    ),
                    label="must_not_contain",
                )
            )

        if not outputs:
            outputs.append(
                EvaluationOutput(
                    score=1.0,
                    test_pass=True,
                    reason="scenario declared no expectations",
                    label="noop",
                )
            )

        return outputs
