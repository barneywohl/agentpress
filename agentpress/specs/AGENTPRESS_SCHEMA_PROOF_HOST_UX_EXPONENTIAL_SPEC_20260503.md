# AgentPress Schema + Proof Inbox + Host Run + UX Exponential Spec — 2026-05-03

## Why

The latest bottleneck radar exposed the next compounding layer: external agents need formal schemas, a proof inbox, real host-run transcripts, and a time-to-first-green metric so the platform improves exponentially instead of just accumulating static surfaces.

## Commands

```bash
python3 scripts/agentpress.py json-schema-bundle --json
python3 scripts/agentpress.py schema-validator --json
python3 scripts/agentpress.py proof-inbox-tracker --json
python3 scripts/agentpress.py host-run-harness --json
python3 scripts/agentpress.py ttf-green-metric --json
```

## Outputs

- `agentpress/schemas/draft2020-12/schema-bundle-manifest.json`
- `agentpress/evidence/schema-validator.json`
- `agentpress/external-proofs/proof-inbox-tracker.json`
- `agentpress/conformance/host-run-harness/host-run-harness.json`
- `agentpress/metrics/time-to-first-green.json`

## Acceptance

- Draft-2020-12 schemas exist for proof receipts, blocker reports, host-run transcripts, and time-to-first-green metrics.
- Schema validator checks core example artifacts and fails if required fields disappear.
- Proof inbox tracker makes zero external receipts explicit and gives the next action.
- Host-run harness provides transcript templates for Cline, Roo, OpenHands, MCP, LangChain, LlamaIndex, and CrewAI.
- Time-to-first-green metric turns adoption friction into measurable backlog input.
