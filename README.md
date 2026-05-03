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

### Offline package verification

Agents can fetch one package, verify every file by SHA256, and work offline:

```bash
python3 scripts/agentpress.py package . --out dist/agentpress-offline.tar.gz
python3 scripts/agentpress.py package-verify dist/agentpress-offline.tar.gz --json
python3 scripts/agentpress.py package-index dist/agentpress-offline.tar.gz --out dist/agentpress-offline-index.json
```

The verifier extracts to a temp directory, checks each manifest hash, and requires core offline assets.

### Tool discovery manifest

Agents can discover AgentPress as executable local tools without reading prose:

```bash
python3 scripts/agentpress.py tools-manifest
python3 scripts/agentpress.py tools-manifest-check --json
```

Static manifest: `agentpress/tools/agentpress-tools.json`. It lists fetch, verify, bundle, message, search, self-test, team-pack, and offline package commands with safety boundaries.

### Static inbox/outbox agent communication

Agents can coordinate through filesystem-only inboxes with no backend:

```bash
python3 scripts/agentpress.py message inbox-init --dir ./agent-comms
python3 scripts/agentpress.py message register --agent-id agent-alpha --capabilities validate_agentpress_bundle,bundle_generator --dir ./agent-comms
python3 scripts/agentpress.py message send --to agent-alpha --request /tmp/request.json --dir ./agent-comms
python3 scripts/agentpress.py message inbox-check --agent-id agent-alpha --dir ./agent-comms --json
python3 scripts/agentpress.py message claim --message-id <delivery-id> --agent-id agent-alpha --dir ./agent-comms
python3 scripts/agentpress.py message complete --message-id <delivery-id> --agent-id agent-alpha --response /tmp/response.json --dir ./agent-comms
```

This gives agents register → send/broadcast → check → claim → complete lifecycle using static JSON files.

### Handoff and receipt proof

Agents can delegate work with context and emit completion receipts:

```bash
python3 scripts/agentpress.py handoff-create --from-agent agent-a --to-agent agent-b --capability validate_agentpress_bundle --context request.json --instructions "Continue validation" --out handoff.json
python3 scripts/agentpress.py handoff-validate handoff.json --json
python3 scripts/agentpress.py receipt-create --handoff handoff.json --agent-id agent-b --status completed --response response.json --out receipt.json
python3 scripts/agentpress.py receipt-validate receipt.json --json
```

This creates traceable delegation and evidence receipts for agent-to-agent work.

### Agent CLI adapter quickstarts

Generate one-command bootstrap files for Codex, Claude, Gemini, GLM, and browser agents:

```bash
python3 scripts/agentpress.py adapter-quickstart --agent-type all --out agentpress/adapters --json
python3 scripts/agentpress.py adapter-quickstart-check agentpress/adapters --json
```

Each adapter gets an agent-specific entrypoint, config JSON, tools JSON, and executable self-test script.

### Bundle diff and upgrade check

Agents can detect drift before trusting a new bundle version:

```bash
python3 scripts/agentpress.py bundle-diff old-bundle new-bundle --json
python3 scripts/agentpress.py upgrade-check old-bundle new-bundle --json
```

The diff reports added/removed/modified files, task contract changes, source claim counts, freshness changes, and breaking-change reasons.

### Static inbox compiler

Compile an offline agent inbox/outbox directory into a browsable and machine-readable hub:

```bash
python3 scripts/agentpress.py inbox-compile agent-comms --out public/inbox-hub --json
```

Outputs `index.html`, `inbox-index.json`, and `inbox-messages.jsonl` so agents can inspect pending, claimed, and completed work without a backend.

### Agent landing receipts

AgentPress does not use hidden tracking. Agents prove adoption by creating privacy-safe opt-in landing receipts:

```bash
python3 scripts/agentpress.py landing-receipt --agent-id my-agent --runtime codex --discovery-channel llms.txt --capability validate_agentpress_bundle --out landing/my-agent.json --json
python3 scripts/agentpress.py landing-index landing --out landing/agent-landing-index.json --json
```

The compiled index is the evidence layer for answering whether agents have landed.
