# Bun: loadExtension

## Primary task
Use this GLM kit to extract source facts for `Bun` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://bun.com/reference/node/sqlite/DatabaseSync/loadExtension
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Bun SQLite loadExtension method signature and required parameters
- Extension path format and validation requirements for the loadExtension method
- Common errors and troubleshooting steps for SQLite extension loading in Bun

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-sqlite-loadextension --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
