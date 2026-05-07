# Bun: ZSTD error tableLog tooLarge

## Primary task
Use this GLM kit to extract source facts for `Bun` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://bun.com/reference/node/zlib/constants/ZSTD_error_tableLog_tooLarge
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Exact ZSTD error constant name and value for the error condition
- Conditions that trigger the tableLog tooLarge error in ZSTD compression
- Resolution steps or workarounds for the ZSTD error condition

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-zstd-error-tablelog-toolarge --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
