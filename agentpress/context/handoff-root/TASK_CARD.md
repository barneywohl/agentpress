# AgentPress focused handoff root

Root: `/private/tmp/agentpress-publish-commit`
Generated: 2026-05-05T18:11:36Z

## Use this root when
- The full repository is too large for an agent context.
- A worker needs a focused source map, freshness receipt, and acceptance gates.

## Start commands
```bash
python3 scripts/agentpress.py context-budget /private/tmp/agentpress-publish-commit/agentpress/context/handoff-root --source-map source-map.json --freshness freshness.json --json --strict
python3 scripts/agentpress.py doctor /private/tmp/agentpress-publish-commit --json
python3 scripts/agentpress.py cli-gap-audit /private/tmp/agentpress-publish-commit --json --strict
```

## Selected files
- `tests/fixtures/source-docs/README.md` (213 bytes)
- `agentpress/package-registry/skeleton/python/pyproject.toml` (271 bytes)
- `agentpress/examples/api-docs-handoff/README.md` (309 bytes)
- `agentpress/package-registry/README.md` (357 bytes)
- `agentpress/package-registry/skeleton/README.md` (380 bytes)
- `agentpress/examples/api-docs-handoff/llms.txt` (400 bytes)
- `agentpress/attestations/README.md` (457 bytes)
- `agentpress/tools/tool-schema-serialization-result.json` (722 bytes)
- `agentpress/attestations/docs-command-check-attestation.json` (750 bytes)
- `agentpress/hub/subscriptions/README.md` (853 bytes)
- `agentpress/schemas/self-test-result-v1.schema.json` (1024 bytes)
- `agentpress/attestations/package-manager-bridge-attestation.json` (1087 bytes)
- `agentpress/attestations/tool-cli-coverage-attestation.json` (1102 bytes)
- `agentpress/attestations/native-adapters-schema-trust-attestation.json` (1146 bytes)
- `agentpress/schemas/draft2020-12/host_run_transcript.schema.json` (1219 bytes)
- `agentpress/attestations/strict-schema-ci-gates-attestation.json` (1277 bytes)
- `agentpress/attestations/schema-proof-host-ux-exponential-attestation.json` (1551 bytes)
- `tests/fixtures/strict-schema/invalid-agent-task-card.json` (2121 bytes)
- `tests/fixtures/strict-schema/valid-agent-task-card.json` (2153 bytes)
- `tests/test_next_agent_tools.py` (3003 bytes)
- `agentpress/schemas/README.md` (6517 bytes)
- `agentpress/evals/README.md` (78 bytes)
- `tests/fixtures/conformance/host-transcript-bad.json` (81 bytes)
- `tests/fixtures/source-docs/api/errors.md` (85 bytes)
- `agentpress/distribution/submission-pack/README.md` (87 bytes)
- `agentpress/mcp/registry-pack/README.md` (91 bytes)
- `agentpress/articles/README.md` (94 bytes)
- `agentpress/examples/api-docs-handoff/disclaimer.md` (96 bytes)
- `agentpress/connectors/ecosystem-packs/openhands-mcp-tool-guide.md` (103 bytes)
- `agentpress/connectors/ecosystem-packs/multi-agent-tool-registry-example.md` (131 bytes)
- `agentpress/runtime/README.md` (131 bytes)
- `agentpress/global/README.eu.md` (145 bytes)
- `agentpress/global/README.en.md` (151 bytes)
- `agentpress/external-audits/first-contact/README.md` (152 bytes)
- `agentpress/global/README.asia.md` (154 bytes)
- `agentpress/context/README.md` (164 bytes)
- `agentpress/identity/README.md` (168 bytes)
- `tests/fixtures/source-docs/openapi.yaml` (174 bytes)
- `agentpress/mission-cockpit/README.md` (176 bytes)
- `agentpress/policies/README.md` (177 bytes)
- `agentpress/adapters/native/mcp/README.md` (180 bytes)
- `agentpress/adapters/native/crewai/README.md` (195 bytes)
- `agentpress/global/README.india.md` (206 bytes)
- `agentpress/specs/AGENTPRESS_ATTESTATION_COVERAGE_SPEC_20260503.md` (208 bytes)
- `agentpress/adapters/native/llamaindex/README.md` (212 bytes)
- `agentpress/external-proofs/rc4-public-proof/self-test.jsonl.stdout.txt` (215 bytes)
- `agentpress/adapters/native/langchain/README.md` (220 bytes)
- `agentpress/adapters/native/openhands/README.md` (227 bytes)
- `tests/fixtures/conformance/host-transcript-good.json` (231 bytes)
- `agentpress/adapters/native/roo/README.md` (239 bytes)
