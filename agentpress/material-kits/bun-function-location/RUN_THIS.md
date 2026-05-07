# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/inspector/Debugger/CallFrame/functionLocation`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-function-location --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit contains the exact inspector API endpoint, authentication method, and response shape from the source document.

Review gate: Kit must contain the exact inspector API endpoint, authentication method, and response shape from the source document, with no invented endpoints or assumptions.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
