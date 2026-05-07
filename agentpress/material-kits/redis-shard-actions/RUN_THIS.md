# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/requests/shards/actions`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-shard-actions --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the material kit passes the quality gate with no errors

Review gate: Material kit must contain SOURCE FACT REQUIRED placeholders for all source-specific claims, and must not contain invented endpoint names, status codes, or authentication details

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
