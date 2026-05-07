# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/test/default/MockFunctionCall/result`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-mock-result --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm the kit passes without errors

Review gate: Pass if the material-manifest.json contains the exact result field name, data type, and return shape extracted from the source document

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
