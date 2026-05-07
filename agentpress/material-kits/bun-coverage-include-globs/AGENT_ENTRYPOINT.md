# Bun: coverageIncludeGlobs

## Primary task
Use this GLM kit to extract source facts for `Bun` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://bun.com/reference/node/test/default/RunOptions/coverageIncludeGlobs
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Exact coverageIncludeGlobs option name, type, and default value in Bun test documentation
- Exact glob pattern syntax and supported pattern types for coverageIncludeGlobs in Bun test runs
- Exact RunOptions schema including all coverage-related options and their types

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-coverage-include-globs --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
