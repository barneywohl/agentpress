# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/test/default/MockFunctionCall/target`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-mockfunctioncall-target --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit bun-mockfunctioncall-target --validate and verify the receipt shows all source facts were extracted correctly

Review gate: Pass if the material-manifest.json contains the exact HTTP endpoints, status codes, and JSON response shapes from the source documentation

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
