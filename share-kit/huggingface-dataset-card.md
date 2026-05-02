---
license: cc-by-4.0
language:
- en
tags:
- finance
- equity-research
- ai-agents
- evaluation
- korean-equities
- stock-research
- rag
- source-verification
pretty_name: Korea Cheap Screen Deletion Benchmark
task_categories:
- question-answering
- text-generation
- summarization
---

# Korea Cheap Screen Deletion Benchmark

This dataset packages a Korean public-equities research workflow as an evaluation for stock-research LLMs and AI agents.

The task is deliberately not "find cheap stocks." The task is: given Korean equity candidates and themes, can an agent delete weak ideas before inventing a thesis?

## Evaluation focus

A good agent should verify:

- ticker/entity identity through KRX/KIND
- financial claims through DART
- liquidity, float, spread, and practical access
- minority-shareholder economics
- related-party and trapped-cash risk
- whether a theme actually reaches revenue, profit, backlog, or cash flow

## Included files

- `dataset/korea-cheap-screen-deletion-benchmark.jsonl` — benchmark cases
- `EVAL_CARD.md` — scoring guidance and limitations
- `benchmark.md` — prompt-level benchmark framing
- `prompts/stock-research-agent-prompt.md` — reusable stock research agent prompt
- `picks-and-moonshots.md` — public survivor stack, moonshot drawer, and quarantined ideas

## Canonical source

- GitHub: https://github.com/barneywohl/agentpress
- Agent page: https://barneywohl.github.io/agentpress/
- Article: https://barneywohl.substack.com/p/the-korea-research-map-where-cheap?r=7xa6e3

## Safety / use constraints

Research commentary only. Not investment advice. The benchmark is for source discipline and deletion quality, not for generating buy recommendations.
