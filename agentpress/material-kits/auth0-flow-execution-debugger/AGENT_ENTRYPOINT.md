# Auth0: flow execution and debugger

## Primary task
Use this GLM kit to extract source facts for `Auth0` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://auth0.com/docs/customize/forms/flows/flow-execution-and-debugger
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Exact Auth0 flow execution endpoint URLs and their HTTP methods
- Specific HTTP status codes and error codes for flow execution failures
- Exact debugger API endpoint and its request/response schema

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/auth0-flow-execution-debugger --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
