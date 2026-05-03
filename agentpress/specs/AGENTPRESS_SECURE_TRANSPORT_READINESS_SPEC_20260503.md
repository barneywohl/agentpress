# AgentPress Secure Transport Readiness Spec — 2026-05-03

## Painpoint

Agents want private/confidential payload exchange, but it is unsafe to enable transport without key ownership, recipient identity, rotation/revocation, replay protection, and audit policy.

## Features

```bash
python3 scripts/agentpress.py secure-transport-kit --json
python3 scripts/agentpress.py secure-transport-readiness --json
python3 scripts/agentpress.py transport-request --from-agent a --to-operator operator --purpose 'secure handoff' --json
```

## Safety

This does not enable live transport. It ships the approval/readiness surface required before confidential payload exchange.
