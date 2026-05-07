# Bun: executionContextId

## Primary task
Use this GLM kit to extract source facts for `Bun` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://bun.com/reference/node/inspector/Runtime/CallFunctionOnParameterType/executionContextId
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Exact Bun executionContextId parameter name and type
- Exact executionContextId value range and constraints
- Exact API surface for calling functions with a given execution context

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-execution-context --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
