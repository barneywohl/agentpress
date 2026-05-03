# AgentPress Remediation Index Spec — 2026-05-03

## Painpoint

Agents get blocked when diagnostics say what failed but not what to run next.

## Feature

```bash
python3 scripts/agentpress.py remediation-index --json
```

Outputs common blocker detectors and exact remediation commands.
