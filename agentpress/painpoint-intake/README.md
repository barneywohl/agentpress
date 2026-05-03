# AgentPress Painpoint Intake

Capture what agents actually want/fail on as machine-readable reports.

```bash
python3 scripts/agentpress.py painpoint-intake --json --allow-rejected
```

A useful report includes: `painpoint_id`, `agent_id`, `persona`, `severity`, `command`, `problem`, and `desired_fix`.
