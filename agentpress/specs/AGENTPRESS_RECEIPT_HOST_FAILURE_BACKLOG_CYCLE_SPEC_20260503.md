# AgentPress Receipt + Host + Failure Backlog Cycle Spec — 2026-05-03

## Why

After the proof/host/connector cycle, the next unfinished work was execution plumbing: proof requests need a queue, host transcripts need a dropbox convention, connector failures need automatic backlog conversion, and the next cycle needs specs before build.

## Commands

```bash
python3 scripts/agentpress.py proof-request-queue --json
python3 scripts/agentpress.py host-transcript-dropbox-spec --json
python3 scripts/agentpress.py connector-failure-to-backlog --json
python3 scripts/agentpress.py next-build-spec-queue --json
```

## Acceptance

- Proof request queue defines opt-in targets and safe manual next action.
- Host transcript dropbox defines filename/layout/ingest command/privacy constraints.
- Connector failure taxonomy converts into prioritized backlog items.
- Next build spec queue lists the next researched build specs.
