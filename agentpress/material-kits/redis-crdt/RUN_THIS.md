# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/requests/bdbs/syncer_state/crdt`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-crdt --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the proof receipt fields are populated.

Review gate: Pass if the material-manifest.json contains valid CRDT context slices with SOURCE FACT REQUIRED placeholders for source-specific claims.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
