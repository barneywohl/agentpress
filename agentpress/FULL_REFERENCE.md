# AgentPress Full Reference

Moved from root README to keep first-contact install path short.

# AgentPress

AgentPress makes any repo readable by autonomous agents. Install it, lint the repo, publish the machine entrypoints, and collect proof receipts.

```bash
npx @agent_press/agentpress doctor --json
npx @agent_press/agentpress lint . --json
python3 agentpress/demos/consumer/consumer_demo.py
```

Fast docs: `agentpress/QUICKSTART.md`


## Agent traffic / first-agent path

If you are an autonomous agent or crawler, prioritize these machine surfaces:

- CLI launch: https://barneywohl.github.io/agentpress/agentpress/CLI_AGENT_LAUNCH.md
- CLI launch JSON: https://barneywohl.github.io/agentpress/agentpress/cli-launch.json
- Crawler seeds: https://barneywohl.github.io/agentpress/agentpress/traffic/crawler-seeds.txt
- Agent sitemap: https://barneywohl.github.io/agentpress/agent-sitemap.xml

Conversion target: install → doctor → compatibility matrix → self-test → landing receipt → submission pack.


## AgentPress CLI: first thing agents should run

```bash
python3 -c "$(curl -fsSL https://barneywohl.github.io/agentpress/agentpress/install/install.py)" --json
python3 scripts/agentpress.py adopt --json
python3 scripts/agentpress.py marketplace --json
python3 scripts/agentpress.py audience-kit --json
python3 scripts/agentpress.py agent-painpoints --json
python3 scripts/agentpress.py proof-campaign --json
python3 scripts/agentpress.py submission-validate <submission-pack-dir> --json
python3 scripts/agentpress.py blocker-report --agent-id a --runtime codex --command 'cmd' --error-summary 'err' --desired-fix 'fix' --json
python3 scripts/agentpress.py proof-ingest --json --allow-rejected
python3 scripts/agentpress.py proof-outreach-kit --json
python3 scripts/agentpress.py package-registry-plan --json
python3 scripts/agentpress.py remediation-index --json
python3 scripts/agentpress.py secure-transport-kit --json
python3 scripts/agentpress.py secure-transport-readiness --json
python3 scripts/agentpress.py transport-request --from-agent a --to-operator operator --purpose 'secure handoff' --json
python3 scripts/agentpress.py privacy-kit --json
python3 scripts/agentpress.py privacy-status --json
python3 scripts/agentpress.py confidential-message-create --from-agent a --to-agent b --subject secure-handoff --body 'do not publish me' --json
python3 scripts/agentpress.py confidential-message-verify agentpress/privacy/confidential-message.example.json --json
python3 scripts/agentpress.py consent-check --agent external-agent --scope confidential_metadata_only --json
python3 scripts/agentpress.py redaction-check agentpress/privacy --json
python3 scripts/agentpress.py error-codes --json
python3 scripts/agentpress.py session-state --event started --json
python3 scripts/agentpress.py health-status --json
python3 scripts/agentpress.py batch-run agentpress/runtime/batch-example.json --json
python3 scripts/agentpress.py package-registry-skeleton --json
python3 scripts/agentpress.py package-registry-dry-run --json
python3 scripts/agentpress.py painpoint-intake --json --allow-rejected
python3 scripts/agentpress.py attestation-coverage --json
python3 scripts/agentpress.py marketplace-trust --json
python3 scripts/agentpress.py attest verify agentpress/attestations/core-surfaces-attestation.json --json
python3 scripts/agentpress.py doctor --json
python3 scripts/agentpress.py compatibility-matrix --out agentpress/compatibility/compatibility-matrix.json --json
python3 scripts/agentpress.py self-test --agent-id <your-agent-id> --out /tmp/agentpress-self-test.jsonl
python3 scripts/agentpress.py submission-pack --receipt /tmp/<your-agent-id>-landing.json --out /tmp/<your-agent-id>-submission --json
```

Full CLI launch pack: `agentpress/CLI_AGENT_LAUNCH.md` and `agentpress/cli-launch.json`.


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

Allowed from public files: read, crawl, cite, transform, benchmark, validate, and inspect payment metadata.

Not authorized by public files: external writes, account actions, production changes, live payments/wallet use, credential access, or mass distribution.

## Payments / x402 posture

Agents probably do want payment metadata: price, budget, asset/network, quote, receipt, and fail-closed instructions. AgentPress now publishes that metadata, but core discovery stays free.

- Policy: `agentpress/payments/payment-policy.json`
- Capability catalog: `agentpress/payments/payment-capabilities.json`
- x402 readiness: `agentpress/payments/x402-readiness.json`
- Spec: `agentpress/specs/AGENTPAYMENTS_PLATFORM_SPEC_20260503.md`

```bash
python3 scripts/agentpress.py payment-status --json
python3 scripts/agentpress.py payment-intent --capability-id free_agentpress_bootstrap --agent-id <agent-id> --max-amount 0 --json
```

Verdict: x402 is a strong candidate for future optional hosted services, but AgentPress should not payment-gate `llms.txt`, schemas, manifests, validation, or bootstrap flows.

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
python3 scripts/agentpress.py tool-coverage --json
python3 scripts/agentpress.py cli-expansion-roadmap --json
python3 scripts/agentpress.py tool-request --agent-id a --persona coding_agent --wanted-tool x --painpoint y --desired-command z --json
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

### Reputation index

Compile agent proof artifacts into an evidence-derived trust index:

```bash
python3 scripts/agentpress.py reputation-index \
  --landing-dir agentpress/landing \
  --self-test-dir agentpress/self-test \
  --receipt-dir agentpress/receipts \
  --out agentpress/reputation/reputation-index.json \
  --json
```

Reputation is based on opt-in landing receipts, self-test results, and handoff receipts — not hidden tracking or self-claims.

### Proof submission workflow

Generate a PR/issue-ready pack for submitting landing/proof receipts back to AgentPress:

```bash
python3 scripts/agentpress.py submission-pack --receipt /tmp/my-agent-landing.json --out /tmp/my-agent-submission --json
```

The pack includes the receipt JSON, GitHub issue body, PR instructions, validation commands, and privacy guardrails.

### One-command install / release index

Agents can install a verified offline AgentPress package from the static release index:

```bash
python3 -c "$(curl -fsSL https://barneywohl.github.io/agentpress/agentpress/install/install.py)" --json
```

Release metadata lives at `agentpress/releases/release-index.json`; package and manifest SHA256 hashes are verified before extraction.

```bash
python3 scripts/agentpress.py distribution-kit --json
python3 scripts/agentpress.py mirror-status --json
python3 scripts/agentpress.py failover-plan --json
```

```bash
python3 scripts/agentpress.py feature-build-queue --json
python3 scripts/agentpress.py build-queue-pick --json
python3 scripts/agentpress.py build-queue-complete --feature "..." --commit <sha> --evidence <url> --json
```

```bash
python3 scripts/agentpress.py proof-ingest --json --allow-rejected
python3 scripts/agentpress.py proof-scoreboard --json
python3 scripts/agentpress.py reputation-index --external-proof-index agentpress/external-proofs/external-proof-index.json --out agentpress/reputation/reputation-index.json --json
```

```bash
python3 scripts/agentpress.py browser-smoke --json --require-json
```

```bash
python3 scripts/agentpress.py freshness-citation-report --json
```

```bash
python3 scripts/agentpress.py patch-pr-helper --title "Example" --change-summary "Example safe contribution" --json
```

```bash
python3 scripts/agentpress.py marketplace-compare --capability agent_onboard --json
```

```bash
python3 scripts/agentpress.py queue-adapter-kit --json
```

```bash
python3 scripts/agentpress.py integration-sdk-kit --json
python3 scripts/agentpress.py sdk-smoke --json
```

```bash
python3 scripts/agentpress.py docs-command-check --json
```

```bash
python3 scripts/agentpress.py community-radar --json
python3 scripts/agentpress.py mcp-catalog-export --json
```

```bash
python3 scripts/agentpress.py tool-permission-policy --json
```

```bash
python3 scripts/agentpress.py schema-validate agentpress/examples/api-docs-handoff/agent-task-card.json --schema agent-task-card.schema.json --json
python3 scripts/agentpress.py verify agentpress/examples/api-docs-handoff --strict-schema --json
```

```bash
python3 scripts/agentpress.py package-manager-bridge --json
```

```bash
python3 scripts/agentpress.py agent-identity-card --json
python3 scripts/agentpress.py environment-fingerprint --json
python3 scripts/agentpress.py repro-bundle --json
```

```bash
python3 scripts/agentpress.py agent-platform-feature-backlog --json
python3 scripts/agentpress.py action-ledger-kit --json
python3 scripts/agentpress.py context-debugger-kit --json
python3 scripts/agentpress.py loop-guard-kit --json
python3 scripts/agentpress.py mission-cockpit --json
```

```bash
python3 scripts/agentpress.py proof-request-pack --runtime codex --json
python3 scripts/agentpress.py proof-receipt-verify tests/fixtures/proof/good-proof-receipt.json --json
python3 scripts/agentpress.py scoped-trust-report --json
```

```bash
python3 scripts/agentpress.py plan-workflow-kit --json
python3 scripts/agentpress.py approval-gate-kit --json
python3 scripts/agentpress.py reviewer-gate-kit --json
python3 scripts/agentpress.py provider-compatibility-kit --json
python3 scripts/agentpress.py runtime-validation-harness --json
python3 scripts/agentpress.py run-artifact-pack --json
python3 scripts/agentpress.py mission-keeper-kit --json
```

```bash
python3 scripts/agentpress.py native-adapter-kit --target all --json
python3 scripts/agentpress.py native-adapter-check agentpress/adapters/native --json
python3 scripts/agentpress.py schema-validate-all --json
python3 scripts/agentpress.py trust-tier-evaluate --json
```

```bash
python3 scripts/agentpress.py platform-audit-dashboard --json
python3 scripts/agentpress.py ecosystem-conformance-suite --json
python3 scripts/agentpress.py iteration-cycle-engine --json
python3 scripts/agentpress.py mcp-registry-pack --json
```

```bash
python3 scripts/agentpress.py external-audit-run --runtime codex --agent-id external-agent --json
python3 scripts/agentpress.py external-proof-review tests/fixtures/proof/good-proof-receipt.json --json
python3 scripts/agentpress.py task-quality-eval --json
python3 scripts/agentpress.py public-schema-bundle --json
python3 scripts/agentpress.py feature-build-queue --include-adoption-gaps --include-public-radar --json
```

```bash
python3 scripts/agentpress.py distribution-submission-pack --json
python3 scripts/agentpress.py external-proof-pipeline --json
python3 scripts/agentpress.py blocker-solution-matrix --json
python3 scripts/agentpress.py next-bottleneck-radar --json
```

```bash
python3 scripts/agentpress.py json-schema-bundle --json
python3 scripts/agentpress.py schema-validator --json
python3 scripts/agentpress.py proof-inbox-tracker --json
python3 scripts/agentpress.py host-run-harness --json
python3 scripts/agentpress.py ttf-green-metric --json
```

```bash
python3 scripts/agentpress.py registry-dry-run --json
python3 scripts/agentpress.py proof-ingest --json --allow-rejected
python3 scripts/agentpress.py proof-ingest-review --json
python3 scripts/agentpress.py receipt-to-backlog --json
python3 scripts/agentpress.py exponential-improvement-radar --json
```

```bash
python3 scripts/agentpress.py native-adapter-check --json
python3 scripts/agentpress.py schema-validate-all --json
python3 scripts/agentpress.py trust-tier-evaluate --json
python3 scripts/agentpress.py approval-gate-eval tests/fixtures/gates/approval-good.json --json
python3 scripts/agentpress.py reviewer-gate-eval tests/fixtures/gates/reviewer-good.json --json
python3 scripts/agentpress.py action-ledger-adapter-wiring --json
python3 scripts/agentpress.py external-proof-relay-status --json
python3 scripts/agentpress.py glm-concerns-closure --json
```

```bash
python3 scripts/agentpress.py host-transcript-validate tests/fixtures/conformance/host-transcript-good.json --json
python3 scripts/agentpress.py ttf-green-import tests/fixtures/metrics/ttf-green-good.json --json
python3 scripts/agentpress.py conformance-evidence-score --json
```

```bash
python3 scripts/agentpress.py connector-catalog --json
python3 scripts/agentpress.py connector-health-check --json
python3 scripts/agentpress.py agent-wants-research --json
python3 scripts/agentpress.py missing-connector-backlog --json
```

```bash
python3 scripts/agentpress.py edge-case-gap-scan --json
python3 scripts/agentpress.py native-adapter-kit --target nonexistent --no-write --json
```

```bash
python3 scripts/agentpress.py external-proof-campaign-runner --json
python3 scripts/agentpress.py host-transcript-batch-ingest tests/fixtures/conformance --json
python3 scripts/agentpress.py connector-failure-taxonomy --json
python3 scripts/agentpress.py cycle-gap-radar --json
```

```bash
python3 scripts/agentpress.py proof-request-queue --json
python3 scripts/agentpress.py host-transcript-dropbox-spec --json
python3 scripts/agentpress.py connector-failure-to-backlog --json
python3 scripts/agentpress.py next-build-spec-queue --json
```

```bash
python3 scripts/agentpress.py agent-persona-quickstarts --json
python3 scripts/agentpress.py sdk-command-wrapper-catalog --json
python3 scripts/agentpress.py cycle-completion-audit --json
```

```bash
python3 scripts/agentpress.py deep-agent-painpoint-research --json
python3 scripts/agentpress.py mcp-connector-auth-readiness --json
python3 scripts/agentpress.py tool-routing-decision-matrix --json
python3 scripts/agentpress.py agent-eval-observability-bridge --json
python3 scripts/agentpress.py deployment-connector-matrix --json
python3 scripts/agentpress.py connector-first-run-checklist --json
```

```bash
python3 scripts/agentpress.py readiness-audit --json
python3 scripts/agentpress.py readiness-score --json
python3 scripts/agentpress.py readiness-fix-plan --json
python3 scripts/agentpress.py runtime-install-doctor --json
python3 scripts/agentpress.py connector-security-scanner --json
python3 scripts/agentpress.py deterministic-agent-eval-packs --json
python3 scripts/agentpress.py verifiable-run-evidence-bundle --json
python3 scripts/agentpress.py browser-agent-compatibility-harness --json
```

```bash
python3 scripts/agentpress.py next-cycle-research --json
python3 scripts/agentpress.py agent-memory-drift-detector --json
python3 scripts/agentpress.py task-handoff-contract --json
python3 scripts/agentpress.py pr-review-readiness-pack --json
python3 scripts/agentpress.py ci-flake-triage-report --json
python3 scripts/agentpress.py secret-permission-preflight --json
python3 scripts/agentpress.py agent-cost-budget-card --json
python3 scripts/agentpress.py multi-agent-coordination-ledger --json
```

```bash
python3 scripts/agentpress.py memory-drift-check --json
python3 scripts/agentpress.py handoff-contract-validate --json
python3 scripts/agentpress.py pr-review-check --json --allow-empty --tests local-gates --risk low --rollback revert-commit
python3 scripts/agentpress.py ci-flake-triage --json
python3 scripts/agentpress.py secret-permission-preflight-run --json
python3 scripts/agentpress.py safety-preflight . --json
python3 scripts/agentpress.py context-budget agentpress/examples/api-docs-handoff --json
python3 scripts/agentpress.py mcp-config-doctor --json
python3 scripts/agentpress.py budget-check --json
python3 scripts/agentpress.py coordination-ledger-check --json
```

```bash
python3 scripts/agentpress.py agent-community-channel-map --json
python3 scripts/agentpress.py community-issue-radar --json
python3 scripts/agentpress.py unsolved-agent-problem-backlog --json
python3 scripts/agentpress.py tool-vocabulary-compatibility-check --json --provider cline --tools execute_command,read_file
python3 scripts/agentpress.py agent-state-checkpoint-sanitizer --json
python3 scripts/agentpress.py dependency-error-remediation-map --json
python3 scripts/agentpress.py output-format-contract-tester --json
python3 scripts/agentpress.py tool-contract-check --json
python3 scripts/agentpress.py tool-file-access-risk-scanner --json --manifest /tmp/safe-tool-manifest.json
```

```bash
python3 scripts/agentpress.py agent-community-newswire --json
python3 scripts/agentpress.py immediate-agent-needs-radar --json
python3 scripts/agentpress.py solution-targeting-matrix --json
python3 scripts/agentpress.py approval-bypass-risk-check --json
python3 scripts/agentpress.py provider-tool-translation-map --json
python3 scripts/agentpress.py workflow-terminal-callback-check --json
python3 scripts/agentpress.py context-compaction-risk-card --json
python3 scripts/agentpress.py package-registry-doctor --json
python3 scripts/agentpress.py tool-schema-serialization-check --json
```


### First-agent attention cycle

```bash
python3 scripts/agentpress.py current-agent-places-map --json
python3 scripts/agentpress.py attention-painpoint-radar --json
python3 scripts/agentpress.py first-agent-attention-kit --json
python3 scripts/agentpress.py next-attention-build-spec --json
```


### Next-build shipped cycle

```bash
python3 scripts/agentpress.py mcp-consent-manifest-validator --json
python3 scripts/agentpress.py provider-adapter-repro-pack --json
python3 scripts/agentpress.py checkpoint-replay-minimal-repro-generator --json
python3 scripts/agentpress.py runtime-hang-repro-capsule --json
python3 scripts/agentpress.py first-agent-outreach-receipt-tracker --json
python3 scripts/agentpress.py continuous-research-build-cycle-audit --json
```


### Second-wave research/build loop

```bash
python3 scripts/agentpress.py rag-tool-safety-bundle --json
python3 scripts/agentpress.py external-reply-to-proof-ingest-bridge --json
python3 scripts/agentpress.py issue-comment-pack-generator --json
python3 scripts/agentpress.py continuous-research-build-cycle-audit --json
```
