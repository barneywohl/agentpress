# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/http2/Http2ServerResponse/errored`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-http2-errored --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and verify the kit contains extracted property definition, conditions, and error handling patterns

Review gate: Kit must contain exact property definition, exact conditions for true/false, and exact error handling patterns extracted from source document

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
