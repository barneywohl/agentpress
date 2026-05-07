# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://redis.io/docs/latest/operate/rs/references/rest-api/objects/bdb/snapshot_policy`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/redis-snapshot-policy --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm the receipt shows the material-manifest.json at agentpress/material-kits/redis-snapshot-policy/material-manifest.json with valid content.

Review gate: The material-manifest.json must contain the exact snapshot policy API endpoint, exact parameter names, and exact field types extracted from the source document, with no invented content.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
