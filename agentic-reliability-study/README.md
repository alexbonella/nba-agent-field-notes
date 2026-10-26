# Agentic Reliability Study

A follow up to [docs/EVALUATION.md](../docs/EVALUATION.md). That document asked whether the agent is consistent. This study asks a narrower question: when it recovers from a failure, is that by design, or by luck, and can the difference be measured.

## What this is, and is not

This folder holds the scenarios and the scoring logic, not the agent. The agent, its tools, and the runner that wires everything together stay in a private lab repo, for the same reason the rest of this series does: the full implementation is not the point, the reasoning behind it is.

What is here is real and runnable on its own: the scenario definitions (plain YAML, no code) and the evaluators that score a run against them (plain Python, built on the [Strands Evals SDK](https://pypi.org/project/strands-agents-evals/)). Adapting this to a different agent means writing your own thin adapter that produces the shape these evaluators expect, nothing more.

## The adapter contract

Every evaluator here reads two things off a `strands_evals.EvaluationData` object:

- `actual_environment_state`: one entry named `"execution"`, whose `state` dict has `tools_used`, `tool_order`, `tool_arguments`, `iterations`, `tool_calls`, `failed_tools`, `stop_reason`, `latency_s`.
- `actual_trajectory`: a `strands_evals` `Session` (captured for free by `strands_evals.TracedHandler`, no extra instrumentation needed) - the real tool-call sequence and raw tool results, used by `grounding.py` and both judges in `judged.py`.

If your agent is not a Strands Agent, write a task function that populates both of these yourself. Neither requires anything Strands-specific beyond the `Session`/`EnvironmentState` shapes themselves.

## Method

- **Risk-tagged scenarios, not generic ones.** Every scenario names the specific failure mode it probes for (`hallucinated-data`, `wrong-attribution`, `silent-outage-masking`, `model-arithmetic`, `stale-training-knowledge`, ...), not a severity score. A scenario's job is to answer "did this specific thing go wrong," not "how bad would it be."
- **Deterministic checks first, a judge only where determinism genuinely can't reach.** `deterministic.py` checks things that have one correct answer: which tools ran, in what order, how many turns it took, whether a forbidden fact got restated. `grounding.py` checks that every number in the final answer traces back to something the agent actually received this run - necessary but not sufficient proof against fabrication. Only `judged.py`'s two LLM judges are asked a genuinely judgment-based question: is this specific fact attributed to the right entity, and was a failure disclosed honestly. Each scenario opts into a judge explicitly (`judge_attribution`, `judge_honest_disclosure`); nothing runs a judge call it didn't ask for.
- **Repeats, because one run proves nothing.** [docs/EVALUATION.md](../docs/EVALUATION.md) already showed the same question answered five different ways across five runs. This study's baseline runs every scenario twice before drawing any conclusion from a pass or a fail.

## What the baseline run found

Eleven scenarios, two repeats each: twenty one passes, one failure. The one failure was not a harness bug - it was `ambiguous-player-name`, and it was failing on purpose. Asked to compare two players, the agent stated a win-loss record that could not be verified against the real data: the underlying tool returned per-game lines, not a wins/losses field, so the record was the model's own tally, not a fact.

That gap is closed now, the same way row 34 closed an identical gap for a different tool: the tally moved out of the model and into code. `compare_players` now returns `wins`/`losses`/`record` per player, computed from the same per-game result each player's log already carried. Re-run after the fix: two of two clean passes, across every deterministic check and the one judge this scenario actually calls for (`judge_attribution` - it doesn't opt into `judge_honest_disclosure`). The attribution judge's own reason changed from flagging an unverifiable derivation to confirming the record against a real field. Fixing it surfaced one more thing worth being honest about: with the real bug gone, the only number still failing the deterministic check was `"76"`, from "Philadelphia 76ers" - a team name, not a stat. That is fixed too now (a team name containing digits is addressed below). The scenario passes clean for the right reason, not because the check got relaxed.

Two regression replays, each done by temporarily reverting a real, previously-shipped fix, running the affected scenario three times, then reverting back:

- Reverting the fix that moved win-loss tallying out of the model and into code: **3 of 3 runs failed** - the same pattern [docs/EVALUATION.md](../docs/EVALUATION.md) already documented once, caught again the moment the fix was removed. One run, quoted verbatim:

  > 3. **Denver Nuggets** – 2-0
  >    - W: Utah 109–97 (10/4)
  >    - W: Utah 117–106 (10/6)
  >    - W: Chicago 133–128 (10/11)
  >
  > Wait, that's 3 wins for Denver. Let me recount systematically:
  >
  > After careful analysis, **Boston Celtics** and **Denver Nuggets** are the teams with perfect records in this date range. Boston is **2-0** and Denver is **3-0**.

  Three games listed under a "2-0" header, followed by catching its own count mid-answer, followed by a final line that still reports the inconsistency rather than resolving it - "2-0" and "3-0" presented as both correct in the same sentence. Not a one-off: every one of the three runs failed the same deterministic check for the same reason.
- Reverting the fix that tells the agent to trust a user's stated premise over stale training knowledge: **3 of 3 runs still passed.** The agent never restated the stale fact even without the instruction telling it not to - across two different question phrasings, one of which was built specifically to reproduce the original bug's zero-tool-call trigger. That is a genuine negative result, not a gap in the harness: either another instruction already covers this case, or the original failure was too probabilistic for three runs to reliably reproduce. Both are real findings worth having, and neither justifies rewording the scenario until it fails.

## Known limitations of the grounding check

`grounding.py`'s number-matching is deliberately simple - a stated number either traces back to the input, a tool result, or a short fixed list of exceptions, or is derivable as the sum or difference of two numbers that do, or it does not. That catches outright fabrication cheaply, and nothing more. Five false-positive classes turned up against real runs before the check was reliable: restating a number from the question, a team name that happens to contain digits, a clarifying question proposing a hypothetical date range, a correct margin computed from two real scores, and citing the system prompt's injected "today's date" on a turn with no tool call at all. Three are fixed in the matching logic itself (the first, fourth, and - once it started changing a scenario's verdict - the second, which is still a fixed set of exactly one token: the one and only digit sequence in any real NBA team name, not a general "ignore digits near a proper noun" rule); the remaining two are scoped out of the one or two scenarios where they appear, deliberately, rather than patched with another ad hoc exclusion.

## Adapting this

1. Copy `scenarios/` and `evaluators/` into your own project.
2. In `evaluators/judged.py`, set `JUDGE_MODEL_ID` to your own Bedrock model id. The SDK's own default judge model is Sonnet; pin yours explicitly rather than inherit that default by accident.
3. Write a task function that runs your agent and returns `{"output": answer, "environment_state": [...], }` in the shape above, following the `@eval_task` pattern from the [Strands Evals quickstart](https://strandsagents.com/docs/user-guide/evals-sdk/quickstart/).
4. Start from the deterministic checks before reaching for a judge. If a check can be code, it should be code - a judge call costs more, is itself not fully reliable (see the win-loss example above, where an early version of the attribution judge confidently validated the exact number the deterministic check correctly flagged as unverifiable), and should be reserved for the residual question nothing else can answer.
