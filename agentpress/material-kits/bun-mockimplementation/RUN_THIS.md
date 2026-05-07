# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/test/default/MockFunctionContext/mockImplementation`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-mockimplementation --json`.

Validation/proof: Run python3 scripts/agentpress.py proof-receipt --kit bun-mockimplementation --validation-strict and verify the receipt shows: (1) exact API signature extracted, (2) exact parameter types extracted, (3) exact error handling behavior extracted, (4) no invented content

Review gate: Pass if the material kit contains the exact Bun mockImplementation API signature, exact parameter types, and exact error handling behavior from the source document, with no invented content

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
