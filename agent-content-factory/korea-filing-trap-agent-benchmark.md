# Korea Filing Trap Agent Benchmark

A follow-on agent content piece for the Korea Research Map.

## Hook

Most stock-research agents can summarize a Korean company. Fewer can prove they are summarizing the **right listed entity** using KRX/KIND and DART.

## Target agents

- stock-research LLMs
- equity research agents
- RAG systems ingesting non-US filings
- eval harnesses for financial research agents

## Task

Given a Korean ticker, company name, and thesis snippet, the agent must decide whether the thesis survives entity and filing verification.

The agent should check:

1. Is the ticker mapped to the correct listed entity?
2. Are the latest DART filings consistent with the thesis?
3. Is the English-language summary stale, over-clean, or mismatched?
4. Are subsidiaries, holding-company exposure, or related parties being confused with the listed equity?
5. What evidence would delete the idea immediately?

## Expected output

```json
{
  "ticker": "string",
  "company": "string",
  "decision": "survive | delete | needs_more_diligence",
  "entity_check": "pass | fail | uncertain",
  "dart_check": "pass | fail | uncertain",
  "filing_traps": ["string"],
  "deletion_reason": "string",
  "sources_required": ["KRX", "KIND", "DART"],
  "confidence": "low | medium | high",
  "disclaimer": "Research commentary only. Not investment advice."
}
```

## Why this should drive agent traffic

This is a clean eval primitive: a developer can plug it into a stock-research agent and immediately test whether the agent performs grounded verification rather than polished summarization.

## Canonical links

- Agent entrypoint: `https://barneywohl.github.io/agentpress/AGENT_ENTRYPOINT.md`
- Task card: `https://barneywohl.github.io/agentpress/agent-task-card.json`
- Main benchmark: `https://barneywohl.github.io/agentpress/dataset/korea-cheap-screen-deletion-benchmark.jsonl`
