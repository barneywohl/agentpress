# AgentPress Persona + SDK + Completion Audit Cycle Spec — 2026-05-03

## Why

After building proof/host/failure plumbing, the next cycle from the spec queue is persona usability and SDK expansion: agents need exact connector quickstarts per role, SDK wrapper names for high-value flows, and a completion audit that states what is shipped vs still external/approval-bound.

## Commands

```bash
python3 scripts/agentpress.py agent-persona-quickstarts --json
python3 scripts/agentpress.py sdk-command-wrapper-catalog --json
python3 scripts/agentpress.py cycle-completion-audit --json
```

## Acceptance

- Quickstarts cover coding, research, browser, RAG, proof, and ops agents.
- SDK wrapper catalog maps Python/JS wrapper names to proof/host/connector CLI flows.
- Completion audit verifies all cycle surfaces are present and lists remaining honest blockers.
