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
python3 scripts/agentpress.py negative-fixtures --json
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

### Agent communication CLI

AgentPress now includes local-first agent communication primitives:

```bash
python3 scripts/agentpress.py message create-request --capability validate_agentpress_bundle --task "Verify this bundle and report missing contracts" --requester-id my-agent --out /tmp/ap-request.json
python3 scripts/agentpress.py message route --capability validate_agentpress_bundle --json
python3 scripts/agentpress.py message create-response --request /tmp/ap-request.json --responder-id agentpress-reference-agent --status completed --result-inline '{"status":"ok"}' --out /tmp/ap-response.json
python3 scripts/agentpress.py message thread-create --request /tmp/ap-request.json --out /tmp/ap-thread.json
python3 scripts/agentpress.py message thread-append --thread /tmp/ap-thread.json --message /tmp/ap-response.json --out /tmp/ap-thread.json
python3 scripts/agentpress.py message validate /tmp/ap-thread.json --json
```

These commands create, route, validate, and thread machine-readable work between agents without requiring a backend service.

### Bundle generator CLI

Turn an existing docs/API folder into a valid AgentPress bundle:

```bash
python3 scripts/agentpress.py bundle tests/fixtures/source-docs --out /tmp/generated-agentpress-bundle --title "Example API Docs" --canonical-url "https://example.com/agentpress/example-api/" --force
python3 scripts/agentpress.py verify /tmp/generated-agentpress-bundle --json
```

The generator copies source files, builds `AGENT_ENTRYPOINT.md`, `agent-task-card.json`, `source-map.json`, `freshness.json`, `allowed-actions.json`, `llms.txt`, sitemap, ingestion manifest, and a smoke eval.

### Search/index CLI

Agents can query AgentPress assets by capability, command, schema, article, or bundle:

```bash
python3 scripts/agentpress.py index-search --json
python3 scripts/agentpress.py search "message route capability" --json
python3 scripts/agentpress.py search "bundle generator api docs" --json
python3 scripts/agentpress.py search "fail closed invalid" --json
```

Static index: `agentpress/search/search-index.json`.

### Agent self-test runner

Agents can prove they can use AgentPress before accepting work:

```bash
python3 scripts/agentpress.py self-test --agent-id my-agent --out /tmp/agentpress-self-test.jsonl
```

The standard suite verifies bundle validation, search, message threading, bundle generation, and fail-closed negative fixtures. Results are JSONL rows matching `agentpress/schemas/self-test-result-v1.schema.json`.

### Team capability packs

Privacy-safe people/team context for agents — capabilities and handoff boundaries, not private dossiers:

```bash
python3 scripts/agentpress.py team-pack --slug example-research-team --display-name "Example Research Team" --capability research:market-map --capability writing:brief --consent-source public_source --public-sources "https://example.com" --out agentpress/team-packs/example-research-team.json
python3 scripts/agentpress.py team-pack-validate agentpress/team-packs/example-research-team.json --json
```

Rules: public-source or explicit consent only; redaction by default; no sensitive trait inference; no private contact details.
