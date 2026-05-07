# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/requests/bdbs/replica_sources-alerts`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-replica-sources-alerts --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget agentpress/material-kits/redis-replica-sources-alerts/material-manifest.json --json --strict and confirm the receipt

Review gate: The compact kit contains the exact alert name, condition, and remediation steps for the replica sources alerts endpoint

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
