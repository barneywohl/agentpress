# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/requests/bdbs/availability`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-availability --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify receipt shows valid availability endpoint with SOURCE FACT REQUIRED placeholders filled

Review gate: Kit must contain SOURCE FACT REQUIRED placeholders for endpoint path, HTTP method, and status codes before source facts are extracted

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
