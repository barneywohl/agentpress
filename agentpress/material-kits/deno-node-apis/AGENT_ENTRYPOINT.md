# Deno: node apis

## Primary task
Use this GLM kit to extract source facts for `Deno` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://docs.deno.com/runtime/reference/node_apis/
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Exact Node.js API categories supported in Deno and their import paths
- Compatibility status for each Node.js API: fully compatible, partially compatible, or incompatible
- Deno-specific permission requirements for each Node.js API category

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/deno-node-apis --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
