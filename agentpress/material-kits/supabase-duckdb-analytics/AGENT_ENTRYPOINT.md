# Supabase: duckdb analytics

## Primary task
Use this GLM kit to extract source facts for `Supabase` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://supabase.com/docs/guides/storage/analytics/examples/duckdb
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- SQL query patterns for Supabase duckdb analytics queries
- API endpoint paths and request formats for duckdb analytics
- Authentication scopes and token requirements for analytics access

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/supabase-duckdb-analytics --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
