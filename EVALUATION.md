# Evaluation Results

A scripted evaluation harness, not a one off manual check. Each run asks the same nine questions, each one targeting one distinct agent capability, against the real deployed agent: real Bedrock calls, real NBA Stats API calls, nothing mocked.

## Methodology

- Nine questions, each with an explicit date range instead of a relative one, so every question measures the capability it targets instead of re testing the same ask first behavior over and over.
- Each question runs through its own fresh agent, not one shared instance. An earlier version reused a single agent across all nine questions, and Strands' own multi turn memory let answers from one question leak into the next: by question nine the model was quoting a date that came from question one's result, with a single digit corrupted.
- Every run writes a plain markdown report: question, targeted capability, stop reason, latency, and the full answer.

## One representative run

| Question | Capability | Latency (s) |
|---|---|---|
| What were the results of the preseason games on a given date? | Basic retrieval | 3.2 |
| Which team had the biggest winning margin over a date range? | Aggregation | 5.15 |
| Who were the top scorers in a specific game? | Tool selection | 4.05 |
| How did one team perform over a date range? | Team analysis | 9.25 |
| Which teams are still undefeated over a date range? | Multi game reasoning | 10.82 |
| Compare two teams' performance over a date range. | Comparison | 10.33 |
| What happened in a game, and who led each team? | Tool chaining | 4.06 |
| Compare three named players this preseason. | Player comparison | 6.55 |
| How is my team doing this year, with no team or date given? | Ask first behavior | 1.13 |

Eight of nine questions resolve cleanly on the first turn. The ninth is deliberately underspecified, no team, no date, and the agent correctly stops and asks instead of guessing, in about a second.

## The same question, five runs, five different answers

One question asks which teams are undefeated over an eleven day window. Same agent, same model, same underlying real data, five separate runs within about twenty minutes of each other. The model reported a different set of undefeated teams every single time: six teams in one run, ten in another, seven in a third, then four, then five.

Two of the five runs show the model catching its own mistake mid answer, worth quoting verbatim because it is hard to fake:

> Philadelphia 76ers – 1–0 (beat New York 120–97 on 10/5, but lost to Boston 106–144 on 10/10) — *Actually 1–1, not undefeated*
>
> Let me correct that:

> Houston Rockets - 2-0
> Beat Dallas Mavericks 135-117 (10/9)
> Beat Dallas Mavericks 115-132 (10/11) - *Wait, this is a loss*
>
> Let me correct that:

Same question, same data, asked five times, answered five different ways. That is not a bug in one run, it is what repeated arithmetic reasoning inside a language model actually looks like.

## Three models, one real dataset, three wrong answers

The same question was also run once each against Claude Haiku, Claude Sonnet, and Amazon Nova Lite, on the identical real game data.

- Haiku self corrected inconsistently from run to run, as shown above.
- Sonnet, after visibly flailing through its own reasoning, only confidently named one team.
- Nova Lite claimed both the Clippers and the Warriors were undefeated in the same window, even though the Clippers beat the Warriors 104 to 101 on October 4, inside that exact date range. Both teams undefeated is not an inconsistent answer, it is a logically impossible one.

A bigger or different model was not the fix. The win and loss tally moved out of the model entirely and into a small deterministic function that reads the same real game data and computes the standings directly. Retested after that change: consistent, correct, and no self correction needed, because there was nothing left to get wrong.
