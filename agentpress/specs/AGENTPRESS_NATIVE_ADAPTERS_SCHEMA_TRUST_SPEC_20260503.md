# AgentPress Native Adapters + Schema/Trust Gates Spec — 2026-05-03

## Why

Agents operate inside existing ecosystems — Cline, Roo, OpenHands, MCP, LangChain, LlamaIndex, and CrewAI — not just generic CLI docs. They also need broad public JSON validation and trust tiers that do not inflate from self-proof.

## Commands

```bash
python3 scripts/agentpress.py native-adapter-kit --target all --json
python3 scripts/agentpress.py native-adapter-check agentpress/adapters/native --json
python3 scripts/agentpress.py schema-validate-all --json
python3 scripts/agentpress.py trust-tier-evaluate --json
```

## Outputs

- `agentpress/adapters/native/manifest.json`
- `agentpress/adapters/native/{cline,roo,openhands,mcp,langchain,llamaindex,crewai}/*.json`
- `agentpress/evidence/schema-validate-all.json`
- `agentpress/trust/trust-tier-evaluation.json`

## Acceptance

- Native kit emits target-specific config + README for all seven ecosystems.
- Native adapter check validates every generated kit.
- Schema validate all checks mapped bundle contracts plus public AgentPress JSON surfaces.
- Trust tier evaluation uses scoped proof only; no global proof inflation.
