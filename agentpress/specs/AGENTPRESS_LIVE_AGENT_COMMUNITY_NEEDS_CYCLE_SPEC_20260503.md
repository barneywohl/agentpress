# AgentPress Live Agent Community Needs Cycle Spec — 2026-05-03

## Why

Jake asked the agent team not to wait behind Nexio and to go back through what is done, what still needs fixing, what agents are saying in the places they already communicate, then ship targeted solutions. This cycle uses fresh public issue signals from agent ecosystems and ships concrete gates/cards for immediate problems.

## Commands

```bash
python3 scripts/agentpress.py agent-community-newswire --json
python3 scripts/agentpress.py immediate-agent-needs-radar --json
python3 scripts/agentpress.py solution-targeting-matrix --json
python3 scripts/agentpress.py approval-bypass-risk-check --json
python3 scripts/agentpress.py provider-tool-translation-map --json
python3 scripts/agentpress.py workflow-terminal-callback-check --json
python3 scripts/agentpress.py context-compaction-risk-card --json
python3 scripts/agentpress.py package-registry-doctor --json
python3 scripts/agentpress.py tool-schema-serialization-check --json
```

## Acceptance

- Newswire captures current public agent-community issue signals and themes.
- Needs radar ranks immediate needs and maps them to shipped surfaces.
- Targeting matrix maps communities/problems to AgentPress solution gates.
- Approval bypass checker catches risky MCP/tool calls that execute without approval.
- Provider tool translation map addresses host/provider tool vocabulary mismatch.
- Workflow terminal callback check catches hanging terminal/workflow callback states.
- Context compaction risk card preserves critical task fields.
- Package registry doctor handles install/package 404/auth/permission failures.
- Tool schema serialization check catches raw callable/schema serialization hazards.
