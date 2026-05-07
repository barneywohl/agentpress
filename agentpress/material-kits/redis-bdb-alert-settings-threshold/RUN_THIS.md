# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/objects/db_alerts_settings/bdb_alert_settings_with_threshold`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-bdb-alert-settings-threshold --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm proof receipt fields are populated with extracted source facts

Review gate: Pass if: exact field names for threshold values are present, exact API endpoint path is present, exact JSON schema is present, and all SOURCE FACT REQUIRED placeholders are replaced with real data

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
