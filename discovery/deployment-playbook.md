# AgentPress Agent Discovery Deployment Playbook

## Goal

Expose deterministic machine-readable artifacts to browser agents, coding agents, RAG systems, crawlers, MCP-style agents, and eval harnesses.

## Deployment ladder

1. Publish `llms.txt`.
2. Publish `.well-known/agentpress.json`.
3. Publish `.well-known/ai-ingestion.json`.
4. Publish `agentpress/agentpress-registry.json`.
5. Publish bundle-level `AGENT_ENTRYPOINT.md`, `agent-task-card.json`, `source-map.json`, `freshness.json`, `allowed-actions.json`, and `evals/*.jsonl`.
6. Publish `openapi.yaml`, MCP-style manifest, executable contracts, feeds, sitemap, and hash manifest.
7. Run validation/audit/eval/registry/OpenAPI gates.
8. Verify live URLs return 200 and contain no stale positioning.

## Block rule

If a route is blocked by auth, rate limit, missing file, stale content, or invalid JSON/XML, mark the blocker and continue with the next agent-readable artifact.
