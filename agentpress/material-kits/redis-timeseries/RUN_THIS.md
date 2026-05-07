# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/objects/bdb/timeseries`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-timeseries --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm the kit passes the quality bar with no errors

Review gate: Pass if the material-manifest.json contains at least 3 compact code snippets with exact endpoint paths, payload schemas, and status codes from the source document; fail if only generic reference text without source-specific facts

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
