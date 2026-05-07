# Vercel: delete one or more edge config tokens

## Primary task
Use this GLM kit to extract source facts for `Vercel` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://vercel.com/docs/rest-api/edge-config/delete-one-or-more-edge-config-tokens
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Exact DELETE endpoint path and required authentication scope for edge config token deletion
- Exact response shape and status codes for successful and failed token deletion requests
- Exact edgeConfigId and tokenId parameter formats and constraints

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-edge-config-delete-tokens --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
