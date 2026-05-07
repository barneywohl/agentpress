# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/requests/shards/actions/failover`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-failover --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify receipt contains endpoint, auth, and request body

Review gate: Pass if receipt contains exact endpoint, auth, and request body; fail if generic or missing

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
