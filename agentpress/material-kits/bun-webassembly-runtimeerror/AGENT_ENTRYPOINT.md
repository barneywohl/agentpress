# Bun: RuntimeError

## Primary task
Use this GLM kit to extract source facts for `Bun` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://bun.com/reference/bun/WebAssembly/RuntimeError
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Exact RuntimeError class name and namespace in Bun WebAssembly
- Exact error properties, methods, and their signatures
- Exact error codes and their meanings, and exact conditions that trigger the RuntimeError

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-webassembly-runtimeerror --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
