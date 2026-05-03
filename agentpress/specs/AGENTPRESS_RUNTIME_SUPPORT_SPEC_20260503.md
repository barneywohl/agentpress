# AgentPress Runtime Support Spec — 2026-05-03

## Painpoints from GLM

- No agent-readable error codes.
- No session checkpoint/resume file.
- No health/readiness surface.
- No batch operation support.

## Features

```bash
python3 scripts/agentpress.py error-codes --json
python3 scripts/agentpress.py session-state --event started --json
python3 scripts/agentpress.py health-status --json
python3 scripts/agentpress.py batch-run agentpress/runtime/batch-example.json --json
```

All outputs are static JSON files suitable for agent orchestration.
