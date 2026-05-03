# Use AgentPress for Incident Runbooks

Reference bundle: [`../examples/incident-runbook-sharing/`](../examples/incident-runbook-sharing/)

Best for: SRE runbooks, security response docs, escalation guides, internal operating procedures.

Agents need:
- read-only diagnostic steps,
- escalation gates,
- approval-required actions,
- stale zones,
- evidence requirements,
- explicit prohibited actions.

Run:

```bash
python3 scripts/agentpress.py validate agentpress/examples/incident-runbook-sharing --json
python3 scripts/agentpress.py audit agentpress/examples/incident-runbook-sharing --json
```
