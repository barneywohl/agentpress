# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/requests/debuginfo/node`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-debuginfo-node --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm compact kit card generated with SOURCE FACT REQUIRED placeholders filled

Review gate: Kit card contains exact /debuginfo/node response shape, exact status codes, and exact auth headers — no generic placeholders

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
