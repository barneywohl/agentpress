# AgentPress Executable Agent Gates Spec — 2026-05-03

## Why

The previous operational cycle created route cards/specs for real agent painpoints. This cycle turns them into executable fail-closed gates so agents can validate before claiming done.

## Commands

```bash
python3 scripts/agentpress.py memory-drift-check --json
python3 scripts/agentpress.py handoff-contract-validate --json
python3 scripts/agentpress.py pr-review-check --json --allow-empty --tests local-gates --risk low --rollback revert-commit
python3 scripts/agentpress.py ci-flake-triage --json
python3 scripts/agentpress.py secret-permission-preflight-run --json
python3 scripts/agentpress.py budget-check --json
python3 scripts/agentpress.py coordination-ledger-check --json
```

## Acceptance

- Memory drift check detects stale commands, URL/schema/manifest drift, and docs mismatch.
- Handoff validator enforces owner, gates, evidence, reviewer, risk, closeout.
- PR review check requires tests/risk/rollback and screens obvious secret literals.
- CI flake triage classifies infra/test/code/unknown and blocks deterministic regressions.
- Secret preflight validates secret names/scopes/approvals/dry-run without values.
- Budget check enforces small/medium/large tool/context envelopes.
- Coordination ledger check catches duplicate owners, missing evidence, missing reviewers.
