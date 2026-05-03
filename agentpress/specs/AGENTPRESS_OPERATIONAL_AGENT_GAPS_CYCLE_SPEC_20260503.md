# AgentPress Operational Agent Gaps Cycle Spec — 2026-05-03

## Why

After shipping the readiness layer, the next adoption blockers are operational: stale memory/version assumptions, ambiguous handoffs, PR review friction, flaky CI loops, secret/scope uncertainty, cost blowups, and parallel-agent coordination drift.

## Commands

```bash
python3 scripts/agentpress.py next-cycle-research --json
python3 scripts/agentpress.py agent-memory-drift-detector --json
python3 scripts/agentpress.py task-handoff-contract --json
python3 scripts/agentpress.py pr-review-readiness-pack --json
python3 scripts/agentpress.py ci-flake-triage-report --json
python3 scripts/agentpress.py secret-permission-preflight --json
python3 scripts/agentpress.py agent-cost-budget-card --json
python3 scripts/agentpress.py multi-agent-coordination-ledger --json
```

## Acceptance

- Research lists the next operational gap set and maps each to a built feature.
- Memory drift detector catches stale commands, schema mismatches, old URLs, missing hashes.
- Handoff contract requires owner, gates, evidence, dependencies, reviewer, closeout.
- PR review pack includes summary, risk, tests, screenshots/logs, rollback, review questions.
- CI flake report classifies infra/test/code/unknown and blocks deploy on code regression.
- Secret preflight checks scope/approval/dry-run without secret values.
- Cost budget card defines small/medium/large envelopes and context compression rules.
- Coordination ledger prevents duplicate work and dropped dependencies.
