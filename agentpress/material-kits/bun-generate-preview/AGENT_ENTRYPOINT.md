# Bun: generatePreview

## Primary task
Use this GLM kit to extract source facts for `Bun` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://bun.com/reference/node/inspector/Debugger/EvaluateOnCallFrameParameterType/generatePreview
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Exact method signature for generatePreview (e.g., generatePreview(config))
- Required parameters and their types for the method call
- Return shape and status codes for success and failure scenarios

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-generate-preview --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
