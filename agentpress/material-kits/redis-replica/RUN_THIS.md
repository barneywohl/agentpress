# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/requests/bdbs/syncer_state/replica`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-replica --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm compact context budget passes with SOURCE FACT items extracted

Review gate: Pass if material-manifest.json exists at agentpress/material-kits/redis-replica/ with validated SOURCE FACT items for HTTP method, response shape, and auth requirements

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
