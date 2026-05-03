# AgentPress

AgentPress is a static-first instruction layer for agent-readable websites.

## Use it now

```bash
python3 scripts/agentpress.py doctor --json
python3 scripts/agentpress.py list --json
python3 scripts/agentpress.py validate agentpress/examples/api-docs-handoff --json
python3 scripts/agentpress.py audit agentpress/examples/api-docs-handoff --json
python3 scripts/agentpress.py eval agentpress/examples
python3 scripts/agentpress.py check-registry
python3 scripts/agentpress.py check-openapi
```

## Reference instructions by audience

- **API/documentation teams** → [`examples/api-docs-handoff`](./examples/api-docs-handoff/)
- **Ops/SRE/security teams** → [`examples/incident-runbook-sharing`](./examples/incident-runbook-sharing/)
- **Data/ML/RAG teams** → [`examples/dataset-card-reuse`](./examples/dataset-card-reuse/)
- **Knowledge-base/help-center teams** → [`examples/agent-knowledge-sharing`](./examples/agent-knowledge-sharing/)
- **Agent framework/eval builders** → [`examples/universal-agent-reachability`](./examples/universal-agent-reachability/)

## Machine contracts

- [`agentpress-registry.json`](./agentpress-registry.json)
- [`articles/article-index.json`](./articles/article-index.json)
- [`protocols/mcp-manifest.json`](./protocols/mcp-manifest.json)
- [`protocols/executable-contracts.json`](./protocols/executable-contracts.json)
- [`schemas/`](./schemas/)
- [`self-test/self-test.json`](./self-test/self-test.json)
