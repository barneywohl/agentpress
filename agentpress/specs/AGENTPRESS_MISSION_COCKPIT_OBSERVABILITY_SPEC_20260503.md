# AgentPress Mission Cockpit + Observability Spec — 2026-05-03

## Why

Deep agent-community research and GLM/team audit direction point to the same bottlenecks: agents need observability, context control, circuit breakers, mission coordination, and a living feature backlog. AgentPress should not only expose tools; it should make agent work inspectable, reproducible, and safe to operate.

## Shipped features

```bash
python3 scripts/agentpress.py agent-platform-feature-backlog --json
python3 scripts/agentpress.py action-ledger-kit --json
python3 scripts/agentpress.py context-debugger-kit --json
python3 scripts/agentpress.py loop-guard-kit --json
python3 scripts/agentpress.py mission-cockpit --json
```

## Outputs

- `agentpress/planning/agent-platform-feature-backlog.json`
- `agentpress/observability/action-ledger/manifest.json`
- `agentpress/observability/action-ledger/action-ledger.schema.json`
- `agentpress/observability/action-ledger/action-ledger.example.json`
- `agentpress/context/context-debugger.json`
- `agentpress/runtime/loop-guard-policy.json`
- `agentpress/mission-cockpit/mission-cockpit.json`

## Acceptance gates

- Feature backlog maps painpoints to buildable features, status, and acceptance criteria.
- Action ledger defines auditable agent run events without secrets.
- Context debugger defines context inventory, budgets, freshness checks, and missing-context reporting.
- Loop guard defines retry budgets, stuck-state signatures, and escalation rules.
- Mission cockpit links all trust/runtime/proof/install surfaces from one machine-readable endpoint.
- Package, attestation, docs drift, CI, Validate, Pages, and live URL checks pass.
