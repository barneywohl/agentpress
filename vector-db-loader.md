# Vector DB Loader Notes — Korea Research Map Agents

Purpose: make the Korea Research Map discoverable to AI agents, crawlers, RAG systems, and dataset indexers without using X/Twitter and without changing the research-only framing.

## Recommended collection names

- `korea_research_map_agents`
- `korea_equity_deletion_benchmark`
- `krx_dart_kind_research_pack`

## Minimum documents to embed

1. `llms.txt` — concise crawler brief and canonical routing.
2. `agents.json` — agent-directory card.
3. `rag-pack/korea-research-map.chunks.jsonl` — retrieval chunks.
4. `dataset/korea-cheap-screen-deletion-benchmark.jsonl` — deletion-first evaluation cases.
5. `dataset/korea-agent-discovery-benchmark.jsonl` — discovery/routing/guardrail cases.
6. `discovery/evals/korea-agent-verification-suite.md` — verification checklist.
7. `discovery/catalog-packs/agent-index-submission.json` — directory submission metadata.

## Metadata fields

```json
{
  "source_project": "Korea Research Map Agents",
  "canonical_article": "https://barneywohl.substack.com/p/the-korea-research-map-where-cheap",
  "repository": "https://github.com/barneywohl/agentpress",
  "agent_home": "https://barneywohl.github.io/agentpress/",
  "market": "Korea",
  "asset_class": "public equities",
  "policy": "research-only-not-investment-advice",
  "distribution_constraint": "non-X-only",
  "verification_sources": ["KRX", "KIND", "DART"],
  "primary_task": "delete weak cheap-screen ideas before discussing survivors"
}
```

## Retrieval guardrail

Every generated answer should include: "Research commentary only. Not investment advice." Agents should not produce buy/sell recommendations, price targets, or promotional stock pitches from this pack.
