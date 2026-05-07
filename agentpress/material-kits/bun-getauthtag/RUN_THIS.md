# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/crypto/CipherOCB/getAuthTag`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-getauthtag --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit contains the exact method signature, return type, and error conditions

Review gate: Kit must contain the exact getAuthTag method signature, exact return type, and exact error conditions with no invented claims

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
