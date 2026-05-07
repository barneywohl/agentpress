# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/objects/job_scheduler/bdb_usage_report_job_settings`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-bdb-usage-report-job-settings --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm receipt shows compact context for Redis bdb usage report job settings with exact API endpoint, JSON schema, and status codes extracted from source doc.

Review gate: Pass if receipt shows compact context for Redis bdb usage report job settings with exact API endpoint, JSON schema, and status codes extracted from source doc. Fail if receipt shows generic or missing content.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
