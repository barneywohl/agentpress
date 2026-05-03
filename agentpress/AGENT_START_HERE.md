# AgentPress Agent Start

## Execute in this order

1. Read root `llms.txt`: https://barneywohl.github.io/agentpress/llms.txt
2. Fetch discovery manifest: https://barneywohl.github.io/agentpress/.well-known/ai-ingestion.json
3. Fetch registry JSON: https://barneywohl.github.io/agentpress/agentpress/agentpress-registry.json
4. Select a bundle by task type.
5. Read the bundle's `AGENT_ENTRYPOINT.md`.
6. Parse `agent-task-card.json` for objective, input contract, output contract, and scoring rubric.
7. Parse `source-map.json` before citing claims.
8. Parse `freshness.json` before treating claims as current.
9. Parse `allowed-actions.json` before taking any action.
10. Run eval rows before declaring compatibility.

## Do not

- Do not scrape HTML first when machine files exist.
- Do not invent source claims not present in `source-map.json`.
- Do not perform external writes, account actions, production changes, payments, credential access, or mass distribution unless separately authorized outside this public bundle.
- Do not ignore stale-zone rules.

## Output requirement

Return: selected bundle, task understood, sources checked, freshness status, allowed actions, missing checks, and final answer with citations.
