# NBA Agent Field Notes

Companion repo for an article series on transitioning from Data Engineering to AI Engineering on AWS, built around a small NBA preseason intelligence agent (Strands Agents SDK + Amazon Bedrock).

This repo is not a clone and run artifact. It holds the reasoning behind the real decisions made while building and operating the agent: what broke, why, what was tried, and what shipped. The full implementation, complete Terraform, the full system prompt, the full codebase, stays in a private lab repo and is intentionally not reproduced here.

## What is here so far

- [ARCHITECTURE.md](ARCHITECTURE.md): one diagram, how a question actually flows through the agent, both ways it runs, and where the one still open failure sits in that flow.
- [EVALUATION.md](EVALUATION.md): real evaluation runs against the deployed agent, including the finding that made moving arithmetic into code a requirement, not a preference: the same question, asked five times, answered five different ways, and three different models producing three different wrong answers on identical real data.
- [PARADIGM_SHIFTS.md](PARADIGM_SHIFTS.md): five real moments where a Data Engineer's instinct and the reality of a non deterministic agent reached different answers, in the order they happened.
- [EVIDENCE.md](EVIDENCE.md): the same real question, asked locally and through the deployed Lambda. Locally it returns real data. Through the Lambda it fails the exact same way every time, and the agent reports that honestly instead of inventing numbers. Includes real CloudWatch logs and screen recordings of both runs.
- [SELECTED_IMPLEMENTATION.md](SELECTED_IMPLEMENTATION.md): a handful of real code fragments, each one a direct response to a specific failure, not a general purpose toolkit.

## What is coming

More, as the next article in the series takes shape.

Work in progress.
