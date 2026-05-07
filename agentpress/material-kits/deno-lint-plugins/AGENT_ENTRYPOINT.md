# Deno: lint plugins

## Primary task
Use this GLM kit to extract source facts for `Deno` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://docs.deno.com/runtime/reference/lint_plugins/
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Exact lint plugin API signatures and types
- Exact lint plugin configuration options and parameters
- Exact lint plugin lifecycle hooks and behavior

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/deno-lint-plugins --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
