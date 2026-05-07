# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/objects/bdb/replica_sync`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-replica-sync --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm the replica sync context is compact and citation-ready

Review gate: The material-manifest.json contains SOURCE FACT REQUIRED placeholders that are ready to be filled with real source facts from the Redis documentation

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
