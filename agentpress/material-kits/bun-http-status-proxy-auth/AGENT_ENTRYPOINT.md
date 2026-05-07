# Bun: HTTP STATUS PROXY AUTHENTICATION REQUIRED

## Primary task
Use this GLM kit to extract source facts for `Bun` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://bun.com/reference/node/http2/constants/HTTP_STATUS_PROXY_AUTHENTICATION_REQUIRED
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Exact HTTP status code number and description for the PROXY_AUTHENTICATION_REQUIRED constant
- Exact response body and headers returned when the PROXY_AUTHENTICATION_REQUIRED status is triggered
- Exact authentication requirements and proxy configuration needed to resolve the PROXY_AUTHENTICATION_REQUIRED status

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-http-status-proxy-auth --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
