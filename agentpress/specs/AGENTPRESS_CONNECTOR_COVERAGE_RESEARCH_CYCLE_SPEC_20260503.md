# AgentPress Connector Coverage + Research Cycle Spec — 2026-05-03

## Why

Jake asked to make sure agents have all tools/connectors they need, verify everything works, research missing painpoints, produce the next build list, then ship and deploy. This cycle adds a canonical connector catalog, health gate, agent-wants research surface, and missing connector backlog.

## Commands

```bash
python3 scripts/agentpress.py connector-catalog --json
python3 scripts/agentpress.py connector-health-check --json
python3 scripts/agentpress.py agent-wants-research --json
python3 scripts/agentpress.py missing-connector-backlog --json
```

## Acceptance

- Connector catalog covers local IO, git/GitHub, browser/HTTP, MCP, native agent hosts, proof inbox, package registries, privacy/redaction, approvals/reviewers, and telemetry metrics.
- Connector health check fails if required connector categories or commands disappear.
- Agent wants research maps current painpoints to shipped or still-blocked surfaces.
- Missing connector backlog gives the next build list for the next cycle.
