# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/bun/Worker/onmessageerror`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-worker-onmessageerror --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and confirm proof receipt fields are populated with extracted source facts

Review gate: Pass if: exact event signature is present, exact error object properties are present, exact error handling pattern is present, and all SOURCE FACT REQUIRED placeholders are replaced with real data

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
