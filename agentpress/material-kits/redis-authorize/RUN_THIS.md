# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/requests/users/authorize`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-authorize --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm receipt shows compact context generated for Redis authorize endpoint

Review gate: Material manifest contains SOURCE FACT REQUIRED placeholders for endpoint path, parameters, response shape, and error codes; no invented claims

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
