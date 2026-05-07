# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/objects/crdb/cluster_info`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-cluster-info --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit redis-cluster-info --field cluster_info_response_shape to verify the proof receipt captures the exact response shape.

Review gate: Pass if the proof receipt captures the exact cluster info response shape, status codes, and metrics. Fail if the proof receipt is empty or contains placeholder values.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
