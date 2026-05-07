# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/requests/bdbs/crdt_sources-alerts`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-crdt-sources-alerts --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm the kit passes with no errors and the manifest contains the extracted source facts

Review gate: The material kit must contain the exact CRDT alert endpoint path, the exact JSON request schema, and the exact response shape as extracted from the source document, with no invented fields or assumptions

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
