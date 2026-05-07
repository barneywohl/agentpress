# Bun: waitForDebuggerOnStart

## Primary task
Use this GLM kit to extract source facts for `Bun` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://bun.com/reference/node/inspector/Target/SetAutoAttachParameterType/waitForDebuggerOnStart
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Bun waitForDebuggerOnStart inspector parameter types and boolean values
- Bun waitForDebuggerOnStart debugger attach behavior and runtime errors
- Bun waitForDebuggerOnStart runtime error responses and status codes

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-waitfordebuggeronstart --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
