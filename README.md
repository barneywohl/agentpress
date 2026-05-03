# AgentPress

**Publish for agents, not just humans.**

AgentPress is static publishing infrastructure for autonomous agents, crawlers, RAG systems, eval harnesses, and humans. It packages each publication with a human landing page plus machine-readable task cards, source maps, freshness policies, allowed-action boundaries, ingestion manifests, llms.txt, sitemap.xml, citation policy, disclaimers, and eval smoke tests.

> AgentPress is the canonical product for agent-native knowledge publishing, discovery, communication, citation, localization, and safe reuse.

## Use AgentPress right now

AgentPress is a deployable instruction layer for agent-readable websites. Start here:

```bash
git clone https://github.com/barneywohl/agentpress.git
cd agentpress
python3 scripts/agentpress.py doctor --json
python3 scripts/agentpress.py list --json
python3 scripts/agentpress.py validate agentpress/examples/api-docs-handoff --json
python3 scripts/agentpress.py eval agentpress/examples
python3 scripts/agentpress.py check-registry
python3 scripts/agentpress.py check-openapi
```

If you are adding AgentPress to your own site, copy the bundle contract below, then publish these public paths:

- `/llms.txt`
- `/.well-known/agentpress.json`
- `/.well-known/ai-ingestion.json`
- `/agentpress/agentpress-registry.json`
- `/agentpress/articles/article-index.json`
- `/agentpress/protocols/mcp-manifest.json`
- `/agentpress/protocols/executable-contracts.json`
- `/openapi.yaml`

## Public entrypoints

- Site root: https://barneywohl.github.io/agentpress/
- Start here: [`agentpress/AGENT_START_HERE.md`](./agentpress/AGENT_START_HERE.md)
- Registry JSON: https://barneywohl.github.io/agentpress/agentpress/agentpress-registry.json
- Article index: https://barneywohl.github.io/agentpress/agentpress/articles/article-index.json
- Agent hub: https://barneywohl.github.io/agentpress/agentpress/hub/
- MCP/static contracts: https://barneywohl.github.io/agentpress/agentpress/protocols/mcp-manifest.json
- Executable fixtures: https://barneywohl.github.io/agentpress/agentpress/protocols/executable-contracts.json
- OpenAPI map: https://barneywohl.github.io/agentpress/openapi.yaml
- Self-test: [`agentpress/self-test/self-test.json`](./agentpress/self-test/self-test.json)
- JS SDK: [`agentpress/integrations/js/agentpress-sdk.mjs`](./agentpress/integrations/js/agentpress-sdk.mjs)

## Reference instructions by audience

These are not legacy examples. They are copyable instructions for large, common use cases:

- **API/documentation teams** → [`agentpress/examples/api-docs-handoff/`](./agentpress/examples/api-docs-handoff/)
- **Ops/SRE/security teams** → [`agentpress/examples/incident-runbook-sharing/`](./agentpress/examples/incident-runbook-sharing/)
- **Data/ML/RAG teams** → [`agentpress/examples/dataset-card-reuse/`](./agentpress/examples/dataset-card-reuse/)
- **Knowledge-base/help-center teams** → [`agentpress/examples/agent-knowledge-sharing/`](./agentpress/examples/agent-knowledge-sharing/)
- **Agent framework/eval builders** → [`agentpress/examples/universal-agent-reachability/`](./agentpress/examples/universal-agent-reachability/)

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



## What is still being built

See [`agentpress/GLOBAL_READINESS_GAP_LIST.md`](./agentpress/GLOBAL_READINESS_GAP_LIST.md). Current priorities:

1. public availability monitor and deploy gate,
2. East/West source adapter matrix,
3. language/region metadata,
4. MCP/OpenAPI/JSON Schema/RSS integration samples,
5. cross-agent compatibility harness for Codex, Claude, Gemini, GLM, and open-source agents.

