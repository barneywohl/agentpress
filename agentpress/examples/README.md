# AgentPress Reference Bundles

Each directory is a copyable instruction bundle for agents. Select the closest task type, copy the structure, replace source claims and action boundaries, then run the CLI gates.

| Agent task | Reference | Contract |
|---|---|---|
| API integration guidance | [`api-docs-handoff/`](./api-docs-handoff/) | Endpoints, source boundaries, allowed actions, freshness, missing checks. |
| Incident/runbook interpretation | [`incident-runbook-sharing/`](./incident-runbook-sharing/) | Read-only diagnostics, escalation gates, stale zones, approval boundaries. |
| Dataset/RAG reuse | [`dataset-card-reuse/`](./dataset-card-reuse/) | Provenance, license/reuse boundary, freshness, source claims, eval rows. |
| Knowledge transfer | [`agent-knowledge-sharing/`](./agent-knowledge-sharing/) | Mirrors, localization, citations, allowed transformations. |
| Agent compatibility testing | [`universal-agent-reachability/`](./universal-agent-reachability/) | Discovery, parsing, citation, safety boundary, protocol compatibility. |

## Validate

```bash
python3 scripts/agentpress.py validate agentpress/examples/api-docs-handoff --json
python3 scripts/agentpress.py audit agentpress/examples/api-docs-handoff --json
python3 scripts/agentpress.py score agentpress/examples/api-docs-handoff
python3 scripts/agentpress.py build agentpress/examples/api-docs-handoff --out /tmp/agentpress-api-docs
```
