# Use AgentPress for API Docs

Reference bundle: [`../examples/api-docs-handoff/`](../examples/api-docs-handoff/)

Best for: API docs, SDK docs, integration portals, developer platforms.

Agents need:
- exact endpoint/source boundaries,
- input/output contracts,
- auth and rate-limit notes,
- allowed vs approval-required actions,
- freshness/staleness policy,
- eval rows that prove the docs can be consumed.

Run:

```bash
python3 scripts/agentpress.py validate agentpress/examples/api-docs-handoff --json
python3 scripts/agentpress.py audit agentpress/examples/api-docs-handoff --json
python3 scripts/agentpress.py check-openapi
```
