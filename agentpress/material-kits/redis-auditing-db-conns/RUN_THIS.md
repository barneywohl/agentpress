# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/requests/cluster/auditing-db-conns`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-auditing-db-conns --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the compact context contains the extracted POST schema and auth details

Review gate: The compact context must contain the exact POST schema, auth headers, and response shape from the source document, with no invented details

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
