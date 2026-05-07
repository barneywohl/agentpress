# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/objects/bdb/backup_location`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-backup-location --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the compact context card contains exact endpoint paths, HTTP methods, and response shapes from the source

Review gate: Pass if compact context card contains exact endpoint paths, HTTP methods, and response shapes from the source; fail if generic or missing source-specific details

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
