# AgentPress External Proof Ingestion + Scoring Spec — 2026-05-03

## Real feature

AgentPress now ingests submitted third-party proof/blocker JSON, privacy-scans it, accepts/rejects it, scores it, publishes a scoreboard, and feeds accepted proofs into the reputation index.

## Commands

```bash
python3 scripts/agentpress.py proof-ingest --json --allow-rejected
python3 scripts/agentpress.py proof-scoreboard --json
python3 scripts/agentpress.py reputation-index --external-proof-index agentpress/external-proofs/external-proof-index.json --out agentpress/reputation/reputation-index.json --json
```

## Acceptance

- Rejects private material markers/secrets.
- Requires `privacy_confirmed=true`.
- Requires artifacts for non-blocker success proof.
- Scores accepted proofs.
- Emits `external-proof-index.json` and `proof-scoreboard.json`.
- Reputation index consumes accepted external proofs.
