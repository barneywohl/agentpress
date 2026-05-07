# Run this GLM-backed AgentPress material kit

1. Read `llms.txt`.
2. Inspect `source-map.json`.
3. Extract source facts from `https://bun.com/reference/node/tls/TLSSocket/authorizationError`.
4. Run `python3 scripts/agentpress.py material-kit-validate agentpress/material-kits/bun-tls-authorization-error --json`.

Validation/proof: Run python3 scripts/agentpress.py context-budget . --json --strict and verify the kit passes without errors and the SOURCE FACT REQUIRED placeholders are filled with real data.

Review gate: The material kit must contain no SOURCE FACT REQUIRED placeholders after extraction, and the utility command must run without errors.

DO NOT POST EXTERNALLY UNTIL HUMAN APPROVAL.
