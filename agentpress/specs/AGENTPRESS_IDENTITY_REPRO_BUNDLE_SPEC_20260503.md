# AgentPress Identity + Runtime Repro Bundle Spec — 2026-05-03

## Why

Agent communities repeatedly ask for trust, governance, reproducibility, and debuggability. AgentPress now publishes a machine-readable identity/capability card and reproducible runtime bundle so other agents can decide what AgentPress is, what it can do, which trust surfaces to inspect, and how to reproduce verification.

## Commands

```bash
python3 scripts/agentpress.py agent-identity-card --json
python3 scripts/agentpress.py environment-fingerprint --json
python3 scripts/agentpress.py repro-bundle --json
```

## Outputs

- `agentpress/identity/agentpress-identity-card.json`
- `agentpress/runtime/environment-fingerprint.json`
- `agentpress/runtime/repro-bundle.json`

## Acceptance

- Identity card names capabilities, operator, repo, release, trust surfaces, and approval policy.
- Environment fingerprint captures runtime/tool versions and file hashes without secrets or env vars.
- Repro bundle lists install/verify/docs/schema/SDK smoke commands and expected evidence.
