# Redis: timeseries

## Primary task
Use this GLM kit to extract source facts for `Redis` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://redis.io/docs/latest/operate/rs/references/rest-api/objects/bdb/timeseries
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Exact HTTP endpoint paths for Redis timeseries CRUD operations (SOURCE FACT REQUIRED: exact paths)
- Exact JSON payload schema for creating a timeseries (SOURCE FACT REQUIRED: exact schema)
- Exact status codes and error responses for invalid timeseries requests (SOURCE FACT REQUIRED: exact codes)

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-timeseries --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
