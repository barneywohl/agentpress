# AgentPress

**Publish for agents, not just humans.**

AgentPress is static publishing infrastructure for autonomous agents, crawlers, RAG systems, eval harnesses, and humans. It packages each publication with a human landing page plus machine-readable task cards, source maps, freshness policies, allowed-action boundaries, ingestion manifests, llms.txt, sitemap.xml, citation policy, disclaimers, and eval smoke tests.

> This repository began as a Korea research-map experiment. That research is now only the dogfood corpus. AgentPress is the product.

## Public entrypoints

- Site root: https://barneywohl.github.io/agentpress/
- AgentPress registry: https://barneywohl.github.io/agentpress/agentpress/
- Registry JSON: https://barneywohl.github.io/agentpress/agentpress/agentpress-registry.json
- Global readiness gap list: [`agentpress/GLOBAL_READINESS_GAP_LIST.md`](./agentpress/GLOBAL_READINESS_GAP_LIST.md)

## Quickstart

```bash
python3 scripts/agentpress.py list
python3 scripts/agentpress.py build-all agentpress/examples --out public/agentpress --clean
python3 scripts/validate_agentpress_assets.py
```

Installable skeleton:

```bash
pipx install .
agentpress --help
```

## AgentPress bundle contract

Every production-quality AgentPress bundle should expose:

- `index.html` — human landing page
- `AGENT_ENTRYPOINT.md` — agent-facing task instructions
- `agent-task-card.json` — machine-readable objective, I/O contract, scoring rubric
- `source-map.json` — claim/source map
- `freshness.json` — freshness window and stale-zone policy
- `allowed-actions.json` — action safety boundary
- `.well-known/ai-ingestion.json` — ingestion manifest
- `llms.txt` — compact crawler/LLM brief
- `sitemap.xml` — crawl surface
- `CITATION.cff`, `citation-policy.md`, `disclaimer.md`
- `evals/*.jsonl` — compatibility/smoke evals

## Current examples

- [`agentpress/examples/samsung-hbm-margin/`](./agentpress/examples/samsung-hbm-margin/)
- [`agentpress/examples/sk-hynix-hbm-supply/`](./agentpress/examples/sk-hynix-hbm-supply/)
- [`agentpress/examples/posco-green-steel/`](./agentpress/examples/posco-green-steel/)
- [`agentpress/examples/innospace-thesis/`](./agentpress/examples/innospace-thesis/)
- [`agentpress/examples/liquidity-trap/`](./agentpress/examples/liquidity-trap/)
- [`agentpress/examples/theme-cashflow/`](./agentpress/examples/theme-cashflow/)

All six currently validate at 100/100.

## What is still being built

See [`agentpress/GLOBAL_READINESS_GAP_LIST.md`](./agentpress/GLOBAL_READINESS_GAP_LIST.md). Current priorities:

1. public availability monitor and deploy gate,
2. East/West source adapter matrix,
3. language/region metadata,
4. MCP/OpenAPI/JSON Schema/RSS integration samples,
5. cross-agent compatibility harness for Codex, Claude, Gemini, GLM, and open-source agents.

## Dogfood corpus

The legacy market-research files remain as test material for multilingual/source-heavy research workflows. They should not define the product identity or landing page.

Research commentary only. Not investment advice.
