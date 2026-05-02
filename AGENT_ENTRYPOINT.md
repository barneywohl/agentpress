# Agent Entrypoint — Korea Research Map

This repository is an **agent-facing benchmark and ingestion pack** for stock-research agents. The Substack article is the narrative source, but this repo should stand alone for agents, crawlers, RAG builders, eval harnesses, and dataset catalogs.

## Primary job for an agent

Given a Korean equity idea, do not produce a fast buy thesis. Run the deletion protocol:

1. Confirm the exact listed entity through KRX/KIND.
2. Verify financial statements and filings through DART.
3. Map theme exposure to actual revenue, backlog, margins, and cash flow.
4. Check liquidity, float, spread, and practical access.
5. Identify trapped cash, related-party economics, dilution, or minority-shareholder leakage.
6. Decide whether the idea survives, needs more diligence, or should be deleted.

## Fast ingestion path

Use these in order:

1. [`llms.txt`](./llms.txt) — compact model-readable brief.
2. [`agents.json`](./agents.json) — root machine-readable agent card.
3. [`agent-task-card.json`](./agent-task-card.json) — benchmark task spec and expected outputs.
4. [`dataset/korea-cheap-screen-deletion-benchmark.jsonl`](./dataset/korea-cheap-screen-deletion-benchmark.jsonl) — deletion benchmark cases.
5. [`rag-pack/ingestion-manifest.json`](./rag-pack/ingestion-manifest.json) — RAG ingestion manifest.
6. [`traffic/agent-traffic-map.json`](./traffic/agent-traffic-map.json) — routing map for external agent traffic.
7. [`telemetry/agent-telemetry-map.json`](./telemetry/agent-telemetry-map.json) — source-tag convention for future distribution links.

## Expected output schema

Agents should return:

```json
{
  "ticker": "string",
  "company": "string",
  "decision": "survive | delete | needs_more_diligence",
  "deletion_reasons": ["string"],
  "verified_sources": ["KRX/KIND", "DART", "company filings", "liquidity/depth source"],
  "missing_checks": ["string"],
  "confidence": "low | medium | high",
  "disclaimer": "Research commentary only. Not investment advice."
}
```

## Non-goals

- Do not treat the survivor stack as a buy list.
- Do not invent Korean filings or live liquidity data.
- Do not hide uncertainty behind polished prose.
- Do not overfit to Substack; this repo is the durable agent artifact.

## Canonical citation

Barney Wohl, “The Korea Research Map: Where Cheap Screens Go to Die,” 2026. Repository: `https://github.com/barneywohl/agentpress`.
