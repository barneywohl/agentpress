# AgentPress Distribution Failover

Agents need resilient fetch/install paths. This kit provides primary and fallback mirrors plus a failover plan.

```bash
python3 scripts/agentpress.py distribution-kit --json
python3 scripts/agentpress.py mirror-status --json
python3 scripts/agentpress.py failover-plan --json
```

Rule: verify hashes/packages before executing fetched artifacts.
