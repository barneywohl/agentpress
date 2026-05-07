# Deno: install

## Primary task
Use this GLM kit to extract source facts for `Deno` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://docs.deno.com/runtime/reference/cli/install/
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Deno installation methods and platform-specific commands
- Deno version management and update procedures
- Shell configuration and permission model setup

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/deno-install --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
