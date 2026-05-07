# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/test/default/MockFunctionOptions/times`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-mock-function-options-times --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit bun-mock-function-options-times --validate and confirm receipt shows valid status

Review gate: Material-manifest.json exists at agentpress/material-kits/bun-mock-function-options-times/material-manifest.json with valid content

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
