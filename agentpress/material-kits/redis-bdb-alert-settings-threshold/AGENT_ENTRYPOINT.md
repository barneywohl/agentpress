# Redis: bdb alert settings with threshold

## Primary task
Use this GLM kit to extract source facts for `Redis` without inventing endpoints, status codes, signatures, return shapes, or credentials.

## Input contract
- target_url: https://redis.io/docs/latest/operate/rs/references/rest-api/objects/db_alerts_settings/bdb_alert_settings_with_threshold
- source_facts_needed: facts listed below must be checked against the source before external use.
- approval_boundary: DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.

## Expected output schema
```json
{"source_facts": [], "citations": [], "validation_status": "pending|validated|blocked"}
```

## Source facts needed
- Exact field names for threshold values in bdb_alert_settings object
- Exact API endpoint path for bdb_alert_settings configuration
- Exact JSON schema for alert threshold configuration

## Safe command
```bash
python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-bdb-alert-settings-threshold --json
```

## allowed-actions safety disclaimer
Allowed actions: read, validate, cite, summarize. Prohibited actions: credential access, unapproved external writes, external posting without human approval.

## Approval boundary
DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
