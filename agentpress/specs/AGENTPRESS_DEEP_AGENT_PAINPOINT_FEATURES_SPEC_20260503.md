# AgentPress Deep Agent Painpoint Features Spec — 2026-05-03

## Why

Deep research across coding agents, MCP/connectors, LLMOps/evals, and agent deployment patterns points to five practical painpoints: context/tool overload, connector auth ambiguity, observability/eval fragmentation, install/deploy uncertainty, and first-run confusion. This batch turns those into shipped AgentPress surfaces.

## Commands

```bash
python3 scripts/agentpress.py deep-agent-painpoint-research --json
python3 scripts/agentpress.py mcp-connector-auth-readiness --json
python3 scripts/agentpress.py tool-routing-decision-matrix --json
python3 scripts/agentpress.py agent-eval-observability-bridge --json
python3 scripts/agentpress.py deployment-connector-matrix --json
python3 scripts/agentpress.py connector-first-run-checklist --json
```

## Acceptance

- Research synthesizes what agents want and maps each painpoint to buildable features.
- MCP/connector auth readiness declares auth modes, scopes, risk levels, approvals, and fail-closed rules.
- Tool routing matrix gives minimal-context primary/fallback commands for common intents.
- Eval/observability bridge defines trace fields and agent evaluation dimensions.
- Deployment connector matrix covers git, release tarball, pip, npm, PyPI, npm registry, Docker, MCP registry, HTTP static, and stdio.
- First-run checklist gives exact steps per connector category.
