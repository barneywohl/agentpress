# AgentPress Runtime Support

Static agent-runtime support surfaces for orchestration:

```bash
python3 scripts/agentpress.py error-codes --json
python3 scripts/agentpress.py session-state --event started --json
python3 scripts/agentpress.py health-status --json
python3 scripts/agentpress.py batch-run agentpress/runtime/batch-example.json --json
```

Covers GLM audit painpoints: machine-readable errors, session checkpoints, readiness, and batch operations.
