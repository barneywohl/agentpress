# AgentPress External Proof Ingestion

Validate and index sanitized third-party proof submissions.

```bash
python3 scripts/agentpress.py proof-ingest --json --allow-rejected
```

Accepted proof types:

- `first_contact_adoption`
- `tool_use_success`
- `marketplace_route_success`
- `painpoint_report`

The index rejects obvious secrets/private material and scores accepted proof by artifact count and usefulness.
