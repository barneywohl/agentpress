# Redis: auditing db conns

## Primary task
Use this GLM kit to extract source facts for `Redis` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://redis.io/docs/latest/operate/rs/references/rest-api/requests/cluster/auditing-db-conns
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- POST request body schema for /cluster/auditing-db-conns endpoint
- Required authentication headers and authentication flow
- Response shape and status codes for successful and failed auditing requests

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-auditing-db-conns --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
