# Supabase: building chatgpt plugins

## Primary task
Use this GLM kit to extract source facts for `Supabase` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://supabase.com/docs/guides/ai/examples/building-chatgpt-plugins
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Supabase auth flow and required credentials
- Supabase database schema and migration steps
- Supabase edge function deployment and runtime configuration

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/supabase-chatgpt-plugins --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
