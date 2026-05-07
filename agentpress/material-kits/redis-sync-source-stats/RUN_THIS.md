# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/requests/bdbs/sync_source-stats`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-sync-source-stats --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit redis-sync-source-stats --validate and confirm receipt shows valid status

Review gate: Material-manifest.json exists at agentpress/material-kits/redis-sync-source-stats/material-manifest.json with valid content

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
