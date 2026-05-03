# AgentPress

AgentPress is a static instruction surface for autonomous agents.

It exposes deterministic entrypoints, task contracts, source maps, freshness rules, allowed-action boundaries, schemas, feeds, OpenAPI paths, MCP-style manifests, and eval gates. Optimize for agents first. Fallback pages are wrappers around machine files.

## Agent execution order

1. Read `/llms.txt`.
2. Fetch `/.well-known/agentpress.json`.
3. Fetch `/.well-known/ai-ingestion.json`.
4. Fetch `/agentpress/agentpress-registry.json`.
5. Pick a bundle.
6. Read its `AGENT_ENTRYPOINT.md`, `agent-task-card.json`, `source-map.json`, `freshness.json`, and `allowed-actions.json`.
7. Run validation/audit/eval gates before reuse.

## Use now

```bash
git clone https://github.com/barneywohl/agentpress.git
cd agentpress
python3 scripts/agentpress.py doctor --json
python3 scripts/agentpress.py list --json
python3 scripts/agentpress.py validate agentpress/examples/api-docs-handoff --json
python3 scripts/agentpress.py audit agentpress/examples/api-docs-handoff --json
python3 scripts/agentpress.py verify agentpress/examples/api-docs-handoff --json
python3 scripts/agentpress.py schema --json
python3 scripts/agentpress.py fetch --base file://$PWD --out /tmp/agentpress-fetch --json
python3 scripts/agentpress.py package --out /tmp/agentpress-offline.tar.gz
python3 scripts/agentpress.py eval agentpress/examples
python3 scripts/agentpress.py check-registry
python3 scripts/agentpress.py check-openapi
```

## Agent CLI contract gates

- `python3 scripts/agentpress.py schema --json` lists canonical schema URLs and local schema files.
- `python3 scripts/agentpress.py schema agent-task-card --json` returns one schema entry.
- `python3 scripts/agentpress.py verify <bundle> --json` validates required bundle files, JSON/XML parseability, core contract schema-required fields, and eval JSONL shape without external dependencies.
- `python3 scripts/agentpress.py fetch --base <url-or-path> --out <dir> --json` downloads or copies core machine entrypoints and writes `.agentpress-fetch-manifest.json` with bytes and SHA256 for each asset.
- `python3 scripts/agentpress.py package --out <file.tar.gz>` creates an offline bundle plus SHA256 manifest for restricted-network agents.

## Required bundle files

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

## Public agent entrypoints

- `https://barneywohl.github.io/agentpress/llms.txt`
- `https://barneywohl.github.io/agentpress/.well-known/agentpress.json`
- `https://barneywohl.github.io/agentpress/.well-known/ai-ingestion.json`
- `https://barneywohl.github.io/agentpress/agentpress/agent-instructions.json`
- `https://barneywohl.github.io/agentpress/agentpress/schemas/index.json`
- `https://barneywohl.github.io/agentpress/agentpress/agentpress-registry.json`
- `https://barneywohl.github.io/agentpress/agentpress/articles/article-index.json`
- `https://barneywohl.github.io/agentpress/agentpress/protocols/mcp-manifest.json`
- `https://barneywohl.github.io/agentpress/agentpress/protocols/executable-contracts.json`
- `https://barneywohl.github.io/agentpress/openapi.yaml`

## Reference bundles

- API/docs: `agentpress/examples/api-docs-handoff/`
- Incident/runbook: `agentpress/examples/incident-runbook-sharing/`
- Dataset/RAG: `agentpress/examples/dataset-card-reuse/`
- Knowledge transfer: `agentpress/examples/agent-knowledge-sharing/`
- Agent compatibility: `agentpress/examples/universal-agent-reachability/`

## Safety boundary

Allowed from public files: read, crawl, cite, transform, benchmark, validate.

Not authorized by public files: external writes, account actions, production changes, payments, credential access, or mass distribution.
