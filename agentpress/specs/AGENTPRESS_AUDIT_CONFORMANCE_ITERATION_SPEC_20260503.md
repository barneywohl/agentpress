# AgentPress Audit + Conformance + Iteration Spec — 2026-05-03

## Why

Jake’s recursive directive is now productized: audit everything, fix issues, ship features, re-research painpoints, rebuild the list, and deploy again. Agents need this loop as infrastructure, not just an operator habit.

## Commands

```bash
python3 scripts/agentpress.py platform-audit-dashboard --json
python3 scripts/agentpress.py ecosystem-conformance-suite --json
python3 scripts/agentpress.py iteration-cycle-engine --json
python3 scripts/agentpress.py mcp-registry-pack --json
```

## Outputs

- `agentpress/audit/platform-audit-dashboard.json`
- `agentpress/evidence/ecosystem-conformance-suite.json`
- `agentpress/planning/iteration-cycle-engine.json`
- `agentpress/mcp/registry-pack/mcp-registry-pack.json`

## Acceptance

- Platform dashboard summarizes core gate/surface status and next actions.
- Ecosystem conformance proves Cline/Roo/OpenHands/MCP/LangChain/LlamaIndex/CrewAI have adapter + approval + validation + ledger + proof surfaces.
- Iteration engine encodes the recursive research-build-deploy loop.
- MCP registry pack is submission-ready metadata for MCP directories/communities.
