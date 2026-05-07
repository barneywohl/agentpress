# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/test/default/MockFunctionCall/arguments`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-arguments --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the material-manifest.json exists at agentpress/material-kits/bun-arguments/material-manifest.json with the extracted facts.

Review gate: The material kit contains the exact MockFunctionCall argument schema, the exact argument type system, and the exact argument validation rules, with no unverified claims.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
