# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/objects/crdb/modify_request`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-modify-request --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget agentpress/material-kits/redis-modify-request/material-manifest.json --json --strict and verify the manifest contains correct source facts

Review gate: Pass if the material-manifest.json contains SOURCE FACT REQUIRED placeholders for HTTP method, request body schema, and authentication headers; fail if it contains generic or invented content

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
