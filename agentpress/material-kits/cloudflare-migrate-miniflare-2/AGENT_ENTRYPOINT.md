# Cloudflare: migrate from miniflare 2

## Primary task
Use this GLM kit to extract source facts for `Cloudflare` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://developers.cloudflare.com/workers/testing/vitest-integration/migration-guides/migrate-from-miniflare-2
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Cloudflare Workers miniflare 2 to updated framework migration steps
- Vitest integration specific commands and configuration
- Workers runtime configuration flags and breaking changes

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/cloudflare-migrate-miniflare-2 --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
