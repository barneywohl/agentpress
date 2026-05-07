# Redis: all debug info

## Primary task
Use this GLM kit to extract source facts for `Redis` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://redis.io/docs/latest/operate/rs/references/rest-api/requests/debuginfo/all
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Exact REST API path and HTTP method for debuginfo/all endpoint
- Exact parameters and request body shape for debuginfo/all endpoint
- Exact response shape and status codes for debuginfo/all endpoint

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-debuginfo-all --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
