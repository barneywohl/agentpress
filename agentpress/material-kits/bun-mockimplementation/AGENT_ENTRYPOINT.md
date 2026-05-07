# Bun: mockImplementation

## Primary task
Use this GLM kit to extract source facts for `Bun` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://bun.com/reference/node/test/default/MockFunctionContext/mockImplementation
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Exact Bun mockImplementation API signature (e.g., mockImplementation(mockFunction: Function))
- Exact parameter types and return types for the mockImplementation method (e.g., mockFunction: Function, returns: void)
- Exact error handling behavior when mockImplementation is called incorrectly (e.g., throws TypeError when mockFunction is not a function)

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-mockimplementation --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
