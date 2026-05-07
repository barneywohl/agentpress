# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/requests/nodes/actions`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-actions --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm receipt shows compact context for Redis actions

Review gate: Pass if material-manifest.json exists at agentpress/material-kits/redis-actions/material-manifest.json with valid JSON

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
