# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/objects/statistics/db-metrics`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-db-metrics --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify that the receipt contains the exact endpoint path, the exact JSON schema, and the exact authentication headers.

Review gate: Pass if the material-manifest.json contains the exact endpoint path, the exact JSON schema, and the exact authentication headers, all verified against the source document.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
