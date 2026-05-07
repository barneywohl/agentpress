# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/requests/bdbs/alerts`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-alerts --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the receipt shows the alerts endpoint details were extracted correctly

Review gate: The material kit must contain the exact alerts endpoint URL, request format, and response schema from the source document, with no invented details

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
