# Bun: PerformanceObserver disconnect compact kit

## Primary task
Use this GLM kit to extract source facts for `Bun` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://bun.com/reference/globals/PerformanceObserver/disconnect
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Exact disconnect() method signature and parameters
- Exact error cases when called on already-disconnected observer
- Exact return value or void return type for disconnect()

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-performanceobserver-disconnect --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
