# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/requests/bdbs/passwords`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-passwords --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify that the extracted HTTP method, path, request schema, and response shape match the source doc.

Review gate: Pass if the material kit contains the exact HTTP method, path, request schema, and response shape for Redis database password operations; fail if any field contains generic or placeholder content.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
