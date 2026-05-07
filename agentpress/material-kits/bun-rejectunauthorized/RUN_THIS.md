# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/http2/SecureServerSessionOptions/rejectUnauthorized`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-rejectunauthorized --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and verify the compact context contains the exact option, behavior, and context.

Review gate: Pass if the compact context contains the exact option, behavior, and context without guessing.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
