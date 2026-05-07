# Cloudflare: migrate from unstable dev

## Primary task
Use this GLM kit to extract source facts for `Cloudflare` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://developers.cloudflare.com/workers/testing/vitest-integration/migration-guides/migrate-from-unstable-dev
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Exact unstable-dev version numbers and deprecation timeline
- Specific migration CLI commands and step-by-step procedures
- Target stable runtime environment variables and configuration

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/cloudflare-migrate-unstable-dev --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
