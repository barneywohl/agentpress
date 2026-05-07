# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/requests/debuginfo/all`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-debuginfo-all --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify that the compact context card includes the exact REST API path, HTTP method, parameters, response shape, and authentication requirements from the source document.

Review gate: The compact context card must include the exact REST API path, HTTP method, parameters, response shape, and authentication requirements from the source document, and must not include any information not present in the source document.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
