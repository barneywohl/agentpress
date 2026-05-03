# AgentPress

Static instruction surface for autonomous agents.

## Execute

```bash
python3 scripts/agentpress.py doctor --json
python3 scripts/agentpress.py list --json
python3 scripts/agentpress.py validate agentpress/examples/api-docs-handoff --json
python3 scripts/agentpress.py audit agentpress/examples/api-docs-handoff --json
python3 scripts/agentpress.py eval agentpress/examples
python3 scripts/agentpress.py check-registry
python3 scripts/agentpress.py check-openapi
```

## Required agent files

- `AGENT_ENTRYPOINT.md`
- `agent-task-card.json`
- `source-map.json`
- `freshness.json`
- `allowed-actions.json`
- `.well-known/ai-ingestion.json`
- `llms.txt`
- `sitemap.xml`
- `citation-policy.md`
- `disclaimer.md`
- `evals/*.jsonl`

## Reference bundles

- API/docs agent handoff → [`examples/api-docs-handoff`](./examples/api-docs-handoff/)
- Incident/runbook agent handoff → [`examples/incident-runbook-sharing`](./examples/incident-runbook-sharing/)
- Dataset/RAG agent handoff → [`examples/dataset-card-reuse`](./examples/dataset-card-reuse/)
- Knowledge transfer → [`examples/agent-knowledge-sharing`](./examples/agent-knowledge-sharing/)
- Agent compatibility → [`examples/universal-agent-reachability`](./examples/universal-agent-reachability/)

## Machine contracts

- [`agentpress-registry.json`](./agentpress-registry.json)
- [`articles/article-index.json`](./articles/article-index.json)
- [`protocols/mcp-manifest.json`](./protocols/mcp-manifest.json)
- [`protocols/executable-contracts.json`](./protocols/executable-contracts.json)
- [`schemas/`](./schemas/)
- [`self-test/self-test.json`](./self-test/self-test.json)
