# Vercel: put firewall configuration

## Primary task
Use this GLM kit to extract source facts for `Vercel` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://vercel.com/docs/rest-api/security/put-firewall-configuration
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Exact endpoint path and HTTP method for put-firewall-configuration
- Required request body schema and field definitions for firewall rules
- Authentication method, required scopes, and required headers for the endpoint

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/vercel-put-firewall --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
