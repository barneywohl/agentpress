# Redis: bdb usage report job settings

## Primary task
Use this GLM kit to extract source facts for `Redis` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://redis.io/docs/latest/operate/rs/references/rest-api/objects/job_scheduler/bdb_usage_report_job_settings
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Exact API endpoint for job scheduler configuration
- Exact JSON schema for job settings payload
- Exact status codes returned by job scheduler API

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-bdb-usage-report-job-settings --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
