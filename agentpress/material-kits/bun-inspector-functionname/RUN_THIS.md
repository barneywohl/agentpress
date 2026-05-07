# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/inspector/Runtime/CallFrame/functionName`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-inspector-functionname --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit contains the extracted endpoint, auth, and response shape

Review gate: Kit must contain the exact Bun inspector API endpoint, authentication method, and response shape with no invented fields

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
