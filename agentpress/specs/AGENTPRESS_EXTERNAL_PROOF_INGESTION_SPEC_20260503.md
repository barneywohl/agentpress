# AgentPress External Proof Ingestion Spec — 2026-05-03

## Why

The proof campaign created a submission lane. Agents also need a validator/indexer so submitted proof can be scored and routed into reputation without manual prose review.

## CLI

```bash
python3 scripts/agentpress.py proof-ingest --json --allow-rejected
```

## Behavior

- Reads `agentpress/external-proofs/*.json`.
- Validates proof type, agent id, privacy confirmation, artifacts, and blocker reports.
- Rejects obvious secret/private-material markers.
- Writes `agentpress/external-proofs/external-proof-index.json`.

## Safety

Rejects or flags token/secret/password/bearer/user-agent/IP/private-prompt markers. This is a static sanitizer, not a formal DLP system.
