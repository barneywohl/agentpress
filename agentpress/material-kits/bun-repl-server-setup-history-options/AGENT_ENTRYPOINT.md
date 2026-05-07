# Bun: REPLServerSetupHistoryOptions

## Primary task
Use this GLM kit to extract source facts for `Bun` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://bun.com/reference/node/repl/REPLServerSetupHistoryOptions
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Exact REPLServerSetupHistoryOptions TypeScript/JavaScript interface
- Required properties and their types
- Default values and optional properties

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-repl-server-setup-history-options --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
