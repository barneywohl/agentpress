# Redis: dataset import sources

## Primary task
Use this GLM kit to extract source facts for `Redis` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://redis.io/docs/latest/operate/rs/references/rest-api/objects/bdb/dataset_import_sources
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Exact Redis REST API endpoints for dataset import sources (e.g., POST /v1/import, GET /v1/import/{id})
- Exact HTTP status codes for success and failure responses (e.g., 200 OK, 400 Bad Request, 404 Not Found)
- Exact JSON request/response schemas for the import-source objects (e.g., required fields, field types, field constraints)

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-dataset-import-sources --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
