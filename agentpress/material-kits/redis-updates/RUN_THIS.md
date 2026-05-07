# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/requests/crdbs/updates`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-updates --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm compact context is generated

Review gate: Pass if compact citation-ready context for Redis updates is produced without generic filler

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
