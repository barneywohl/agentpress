# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/requests/shards/actions/migrate`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-migrate --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the compact context card contains the exact endpoint, request body schema, and authentication requirements from the source document.

Review gate: The material kit must contain the exact REST API endpoint, request body schema, and authentication requirements from the source document, with no invented or assumed content.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
