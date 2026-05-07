# Redis CRDT Sources Alerts

## Primary task
Use this GLM kit to extract source facts for `Redis` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://redis.io/docs/latest/operate/rs/references/rest-api/requests/bdbs/crdt_sources-alerts
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Exact HTTP endpoint path for CRDT alert submission (e.g., POST /api/v1/crdt/alerts)
- Exact JSON schema for the alert request body (field names, types, required vs optional)
- Exact response shape and status codes for successful and failed alert submissions

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-crdt-sources-alerts --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
