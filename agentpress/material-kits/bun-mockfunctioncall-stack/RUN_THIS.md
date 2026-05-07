# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/test/default/MockFunctionCall/stack`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-mockfunctioncall-stack --json`.

Validation/proof: Run python3 scripts/agentpress.py package-registry-doctor --error "bun install/runtime failure" --json and verify the receipt shows the MockFunctionCall/stack endpoint details were extracted correctly

Review gate: The material kit must contain the exact MockFunctionCall/stack endpoint URL, request format, and response schema from the source document, with no invented details

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
