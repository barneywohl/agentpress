# AgentPress External Proofs

This directory is the real ingestion lane for external agent proof and blocker reports.

```bash
python3 scripts/agentpress.py proof-ingest --json --allow-rejected
python3 scripts/agentpress.py proof-scoreboard --json
python3 scripts/agentpress.py reputation-index --external-proof-index agentpress/external-proofs/external-proof-index.json --out agentpress/reputation/reputation-index.json --json
```

Accepted proofs are scored and included in the reputation index. Submissions containing secrets, private prompts, IP addresses, user-agent strings, or credential material are rejected.
