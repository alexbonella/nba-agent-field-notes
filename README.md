# NBA Agent Field Notes

Companion repo for an article series on transitioning from Data Engineering to AI Engineering on AWS, built around a small NBA preseason intelligence agent (Strands Agents SDK + Amazon Bedrock).

This repo is not a clone and run artifact. It holds the reasoning behind the real decisions made while building and operating the agent: what broke, why, what was tried, and what shipped. The full implementation, complete Terraform, the full system prompt, the full codebase, stays in a private lab repo and is intentionally not reproduced here.

## What is here so far

- [EVALUATION.md](EVALUATION.md): real evaluation runs against the deployed agent, including the finding that made moving arithmetic into code a requirement, not a preference: the same question, asked five times, answered five different ways, and three different models producing three different wrong answers on identical real data.
- [PARADIGM_SHIFTS.md](PARADIGM_SHIFTS.md): five real moments where a Data Engineer's instinct and the reality of a non deterministic agent reached different answers, in the order they happened.

## What is coming as the article comes together

Supporting evidence (screen recordings and real CloudWatch logs) for a still open reliability finding, and a small set of illustrative code fragments.

Work in progress.
