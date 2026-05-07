# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/util/getSystemErrorMessage`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-getsystemerrormessage --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the compact context output matches the source document content

Review gate: The material kit must contain specific getSystemErrorMessage function signatures, not generic Bun documentation references

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
