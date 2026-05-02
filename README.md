# AgentPress

**Publish for agents, not just humans.**

AgentPress is static publishing infrastructure for autonomous agents, crawlers, RAG systems, eval harnesses, and humans. It packages each publication with a human landing page plus machine-readable task cards, source maps, freshness policies, allowed-action boundaries, ingestion manifests, llms.txt, sitemap.xml, citation policy, disclaimers, and eval smoke tests.

> AgentPress is the canonical product for agent-native knowledge publishing, discovery, communication, citation, localization, and safe reuse.

## Public entrypoints

Primary neutral reference: [`agentpress/examples/agent-knowledge-sharing/`](./agentpress/examples/agent-knowledge-sharing/) — global agent knowledge-sharing bundle with mirror, translation, allowed-action, source-map, and offline/CLI guidance.


- Site root: https://barneywohl.github.io/agentpress/
- AgentPress registry: https://barneywohl.github.io/agentpress/agentpress/
- Registry JSON: https://barneywohl.github.io/agentpress/agentpress/agentpress-registry.json
- Agent Hub: https://barneywohl.github.io/agentpress/agentpress/hub/
- Agent Hub docs: [`agentpress/hub/AGENT_HUB.md`](./agentpress/hub/AGENT_HUB.md)
- Self-test: [`agentpress/self-test/self-test.json`](./agentpress/self-test/self-test.json)
- JS SDK: [`agentpress/integrations/js/agentpress-sdk.mjs`](./agentpress/integrations/js/agentpress-sdk.mjs)
- Directory submission pack: [`agentpress/directory-submission/`](./agentpress/directory-submission/)
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

## Global locale briefs

AgentPress now ships compact discovery briefs for `zh-CN`, `es`, `hi`, `ar`, `fr`, `pt-BR`, `ja`, `ko`, and `de` under [`locales/`](./locales/). English remains canonical; localized briefs help agents worldwide find the standard quickly, then verify claims/actions against canonical machine-readable assets.

## Current examples

- [`agentpress/examples/agent-knowledge-sharing/`](./agentpress/examples/agent-knowledge-sharing/) — primary neutral reference
- [`agentpress/examples/samsung-hbm-margin/`](./agentpress/examples/samsung-hbm-margin/)
- [`agentpress/examples/sk-hynix-hbm-supply/`](./agentpress/examples/sk-hynix-hbm-supply/)
- [`agentpress/examples/posco-green-steel/`](./agentpress/examples/posco-green-steel/)
- [`agentpress/examples/innospace-thesis/`](./agentpress/examples/innospace-thesis/)
- [`agentpress/examples/liquidity-trap/`](./agentpress/examples/liquidity-trap/)
- [`agentpress/examples/theme-cashflow/`](./agentpress/examples/theme-cashflow/)

All current examples validate at 100/100. The primary product reference is neutral and global.

## What is still being built

See [`agentpress/GLOBAL_READINESS_GAP_LIST.md`](./agentpress/GLOBAL_READINESS_GAP_LIST.md). Current priorities:

1. public availability monitor and deploy gate,
2. East/West source adapter matrix,
3. language/region metadata,
4. MCP/OpenAPI/JSON Schema/RSS integration samples,
5. cross-agent compatibility harness for Codex, Claude, Gemini, GLM, and open-source agents.

## Legacy stress-test material

Some older market-research files remain as test material for multilingual/source-heavy workflows. They are not the product identity and should not be used as primary discovery surfaces.

Research commentary only. Not investment advice.
