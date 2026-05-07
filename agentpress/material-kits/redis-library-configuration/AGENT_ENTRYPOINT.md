# Redis: library configuration

## Primary task
Use this GLM kit to extract source facts for `Redis` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://redis.io/docs/latest/operate/oss_and_stack/stack-with-enterprise/deprecated-features/triggers-and-functions/concepts/library_configuration
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Redis library configuration JSON schema and parameter types
- Configuration API endpoints and their request/response shapes
- Configuration validation rules and error codes

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-library-configuration --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
