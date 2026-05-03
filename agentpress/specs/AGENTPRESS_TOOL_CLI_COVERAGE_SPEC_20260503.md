# AgentPress Tool / CLI Coverage Spec — 2026-05-03

## Painpoint

Agents need to know which tools/CLI commands exist, which persona needs are covered, and where the tool surface must expand next.

## Features

```bash
python3 scripts/agentpress.py tool-coverage --json
python3 scripts/agentpress.py cli-expansion-roadmap --json
python3 scripts/agentpress.py tool-request --agent-id a --persona coding_agent --wanted-tool x --painpoint y --desired-command z --json
```

## Acceptance

- Tool coverage maps agent personas to must-have CLI capabilities.
- Missing/partial coverage produces prioritized expansion items.
- Tool request JSON gives external agents a way to request missing commands.
- Outputs are included in tools manifest, search index, release package, and live site.
