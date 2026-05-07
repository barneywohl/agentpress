# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/objects/bdb/search`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-search --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify receipt shows compact search endpoint context with no missing fields

Review gate: Pass if receipt shows compact citation-ready search context; fail if generic or missing endpoint details

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
