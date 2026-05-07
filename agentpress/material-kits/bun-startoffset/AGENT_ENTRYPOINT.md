# Bun: startOffset

## Primary task
Use this GLM kit to extract source facts for `Bun` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://bun.com/reference/node/inspector/Profiler/CoverageRange/startOffset
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Exact property name and parent object path for the startOffset property in Bun's inspector API
- Required Bun runtime version and module imports for accessing the inspector and CoverageRange types
- Property value schema and type information for the startOffset property and its relationship to coverage data

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-startoffset --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
