# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/requests/cluster/actions`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-cluster-actions --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the compact context card contains exact action types, exact schema fields, and exact auth requirements with no generic placeholders.

Review gate: Pass if the material-manifest.json contains exact action types, exact schema fields per action, and exact auth requirements — all SOURCE FACT REQUIRED placeholders must be resolved with real data from the target doc.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
