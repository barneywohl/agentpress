# Auth0: test custom database connections

## Primary task
Use this GLM kit to extract source facts for `Auth0` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://auth0.com/docs/authenticate/database-connections/custom-db/test-custom-database-connections
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Auth0 test endpoint URL and HTTP method
- Test configuration parameters and required fields
- Success/failure response shape and status codes

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/auth0-custom-db-test --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
