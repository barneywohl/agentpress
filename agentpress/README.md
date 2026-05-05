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

## First-user eval harness

Run a safe local adversarial smoke test against synthetic repos:

```bash
python3 scripts/eval_first_user_harness.py --timeout 20
```

The harness creates 5-10 generated repos under `/tmp`, runs local AgentPress first-contact commands (`--help`, `doctor --mode local`, `lint --no-write`, `first-run-wizard --no-write`, `first-user-bootstrap --no-write`), writes a Markdown backlog report, and cleans generated repos by default.

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
