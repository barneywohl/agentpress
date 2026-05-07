# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/objects/bdb/replica_sources_status`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-replica-sources-status --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit contains the exact status codes, error conditions, and configuration parameters from the source

Review gate: The material kit must contain SOURCE FACT REQUIRED placeholders for any unverified claims, and the proof receipt must confirm that no invented claims were included

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
