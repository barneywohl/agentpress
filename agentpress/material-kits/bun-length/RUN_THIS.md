# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/http2/ServerStreamFileResponseOptionsWithError/length`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-length --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and verify the material kit passes the quality gate with no errors

Review gate: Material kit must contain SOURCE FACT REQUIRED placeholders for all source-specific claims, and must not contain invented property names, return types, or error codes

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
